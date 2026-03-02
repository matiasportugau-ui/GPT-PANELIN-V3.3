locals {
  image_uri = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_repo}/${var.service_name}:latest"
}

# ---------------------------------------------------------------
# APIs
# ---------------------------------------------------------------

resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "firestore.googleapis.com",
    "sheets.googleapis.com",
    "cloudscheduler.googleapis.com",
    "iam.googleapis.com",
  ])
  service            = each.key
  disable_on_destroy = false
}

# ---------------------------------------------------------------
# Service Account (runtime)
# ---------------------------------------------------------------

resource "google_service_account" "runtime" {
  account_id   = "${var.service_name}-rt"
  display_name = "Panelin Sheets Orchestrator Runtime"
}

# ---------------------------------------------------------------
# Secrets
# ---------------------------------------------------------------

resource "google_secret_manager_secret" "openai_api_key" {
  secret_id = "panelin-orch-openai-api-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis["secretmanager.googleapis.com"]]
}

resource "google_secret_manager_secret" "orch_api_key" {
  secret_id = "panelin-orch-api-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis["secretmanager.googleapis.com"]]
}

resource "google_secret_manager_secret_iam_member" "runtime_openai" {
  secret_id = google_secret_manager_secret.openai_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_secret_manager_secret_iam_member" "runtime_orch" {
  secret_id = google_secret_manager_secret.orch_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

# ---------------------------------------------------------------
# Firestore (for idempotency)
# ---------------------------------------------------------------

resource "google_project_iam_member" "runtime_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

# ---------------------------------------------------------------
# Artifact Registry
# ---------------------------------------------------------------

resource "google_artifact_registry_repository" "docker" {
  location      = var.region
  repository_id = var.artifact_repo
  format        = "DOCKER"
  depends_on    = [google_project_service.apis["artifactregistry.googleapis.com"]]
}

# ---------------------------------------------------------------
# Cloud Run service
# ---------------------------------------------------------------

resource "google_cloud_run_v2_service" "svc" {
  name     = var.service_name
  location = var.region

  depends_on = [
    google_project_service.apis["run.googleapis.com"],
    google_artifact_registry_repository.docker,
  ]

  template {
    service_account                  = google_service_account.runtime.email
    max_instance_request_concurrency = var.run_concurrency

    scaling {
      max_instance_count = var.run_max_instances
    }

    containers {
      image = local.image_uri

      resources {
        limits = {
          memory = var.run_memory
          cpu    = var.run_cpu
        }
      }

      env { name = "ENV";            value = "prod" }
      env { name = "GCP_PROJECT_ID"; value = var.project_id }
      env { name = "OPENAI_MODEL";   value = "gpt-4o-mini" }
      env { name = "IDEMPOTENCY_BACKEND"; value = "firestore" }

      env {
        name = "OPENAI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.openai_api_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "PANELIN_ORCH_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.orch_api_key.secret_id
            version = "latest"
          }
        }
      }
    }
  }
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.svc.name
  location = google_cloud_run_v2_service.svc.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ---------------------------------------------------------------
# Cloud Scheduler (optional queue processor)
# ---------------------------------------------------------------

resource "google_cloud_scheduler_job" "queue_job" {
  count     = var.enable_scheduler ? 1 : 0
  name      = "${var.service_name}-queue"
  schedule  = var.scheduler_cron
  time_zone = var.scheduler_time_zone

  depends_on = [google_project_service.apis["cloudscheduler.googleapis.com"]]

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.svc.uri}/v1/queue/process"
    headers = {
      "Content-Type" = "application/json"
      "X-API-Key"    = var.scheduler_api_key
    }
    body = base64encode(jsonencode({ "limit" = 20 }))
  }
}
