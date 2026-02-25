# Workload Identity Federation for GitHub Actions (keyless CI/CD).
# Only created when var.enable_wif = true.

resource "google_iam_workload_identity_pool" "github" {
  count                     = var.enable_wif ? 1 : 0
  workload_identity_pool_id = "github-pool"
  display_name              = "GitHub Actions Pool"
  depends_on                = [google_project_service.apis["iam.googleapis.com"]]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  count                              = var.enable_wif ? 1 : 0
  workload_identity_pool_id          = google_iam_workload_identity_pool.github[0].workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub OIDC"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }

  attribute_condition = "assertion.repository == '${var.github_org}/${var.github_repo}'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account" "deployer" {
  count        = var.enable_wif ? 1 : 0
  account_id   = "${var.service_name}-deploy"
  display_name = "Panelin Sheets Orchestrator Deployer (CI)"
}

resource "google_service_account_iam_member" "wif_binding" {
  count              = var.enable_wif ? 1 : 0
  service_account_id = google_service_account.deployer[0].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github[0].name}/attribute.repository/${var.github_org}/${var.github_repo}"
}

resource "google_project_iam_member" "deployer_run_admin" {
  count   = var.enable_wif ? 1 : 0
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.deployer[0].email}"
}

resource "google_project_iam_member" "deployer_sa_user" {
  count   = var.enable_wif ? 1 : 0
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.deployer[0].email}"
}

resource "google_project_iam_member" "deployer_ar_writer" {
  count   = var.enable_wif ? 1 : 0
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.deployer[0].email}"
}
