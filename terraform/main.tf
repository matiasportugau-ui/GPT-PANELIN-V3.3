# Terraform Configuration for GCP Infrastructure
# This file defines all the infrastructure resources needed for the application

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Configure the Google Cloud Provider
provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required GCP APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",                    # Cloud Run API
    "sqladmin.googleapis.com",               # Cloud SQL Admin API
    "secretmanager.googleapis.com",          # Secret Manager API
    "compute.googleapis.com",                # Compute Engine API (for networking)
    "cloudbuild.googleapis.com",             # Cloud Build API
    "artifactregistry.googleapis.com",       # Artifact Registry API
    "servicenetworking.googleapis.com",      # Service Networking API (for VPC)
    "vpcaccess.googleapis.com",              # VPC Access API
    "iam.googleapis.com",                    # IAM API
  ])

  project = var.project_id
  service = each.value

  disable_on_destroy = false
}

# Create a service account for Cloud Run services
resource "google_service_account" "cloud_run_sa" {
  account_id   = "cloud-run-service-account"
  display_name = "Cloud Run Service Account"
  description  = "Service account used by Cloud Run services to access GCP resources"
  project      = var.project_id

  depends_on = [google_project_service.required_apis]
}

# Grant Secret Manager Secret Accessor role to the service account
resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"

  depends_on = [google_service_account.cloud_run_sa]
}

# Grant Cloud SQL Client role to the service account
resource "google_project_iam_member" "cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"

  depends_on = [google_service_account.cloud_run_sa]
}

# Grant Cloud Run Invoker role to the service account (for internal service-to-service calls)
resource "google_project_iam_member" "run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"

  depends_on = [google_service_account.cloud_run_sa]
}

# Grant Cloud Run Developer role to Cloud Build service account for deployments
resource "google_project_iam_member" "cloudbuild_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${var.project_id}@cloudbuild.gserviceaccount.com"

  depends_on = [google_project_service.required_apis]
}

# Create Cloud SQL PostgreSQL instance
resource "google_sql_database_instance" "postgres_instance" {
  name             = "web-app-db"
  database_version = "POSTGRES_16"
  region           = var.region
  project          = var.project_id

  settings {
    tier = "db-f1-micro"  # Smallest instance for development/testing
    
    # Configure IP connectivity
    ip_configuration {
      ipv4_enabled = false  # Disable public IP for security
      # Enable private IP if needed for VPC connectivity
      # private_network = google_compute_network.private_network.id
    }

    # Enable automatic backups
    backup_configuration {
      enabled            = true
      start_time         = "03:00"  # 3 AM UTC
      point_in_time_recovery_enabled = true
    }

    # Maintenance window
    maintenance_window {
      day          = 7  # Sunday
      hour         = 4  # 4 AM UTC
      update_track = "stable"
    }
  }

  deletion_protection = false  # Set to true in production

  depends_on = [google_project_service.required_apis]
}

# Create database within the Cloud SQL instance
resource "google_sql_database" "app_database" {
  name     = "app_database"
  instance = google_sql_database_instance.postgres_instance.name
  project  = var.project_id

  depends_on = [google_sql_database_instance.postgres_instance]
}

# Set root password for Cloud SQL instance
resource "google_sql_user" "postgres_user" {
  name     = "postgres"
  instance = google_sql_database_instance.postgres_instance.name
  password = var.db_root_password
  project  = var.project_id

  depends_on = [google_sql_database_instance.postgres_instance]
}

# Create Secret Manager secret for database credentials
resource "google_secret_manager_secret" "db_secret" {
  secret_id = "db-secret"
  project   = var.project_id

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

# Store database credentials in Secret Manager
resource "google_secret_manager_secret_version" "db_secret_version" {
  secret = google_secret_manager_secret.db_secret.id

  secret_data = jsonencode({
    username = "postgres"
    password = var.db_root_password
    database = "app_database"
    host     = google_sql_database_instance.postgres_instance.connection_name
  })

  depends_on = [
    google_secret_manager_secret.db_secret,
    google_sql_database_instance.postgres_instance
  ]
}

# Create Artifact Registry repository for Docker images
resource "google_artifact_registry_repository" "docker_repo" {
  location      = var.region
  repository_id = "cloud-run-repo"
  description   = "Docker repository for Cloud Run services"
  format        = "DOCKER"
  project       = var.project_id

  depends_on = [google_project_service.required_apis]
}

# Note: Cloud Run services and Load Balancer are deployed via Cloud Build
# This keeps the deployment pipeline automated and integrated with CI/CD
