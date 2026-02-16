# Terraform Outputs
# Define outputs to display after infrastructure deployment

output "cloud_sql_connection_name" {
  description = "The connection name for the Cloud SQL instance"
  value       = google_sql_database_instance.postgres_instance.connection_name
}

output "db_secret_name" {
  description = "The name of the Secret Manager secret containing database credentials"
  value       = google_secret_manager_secret.db_secret.secret_id
}

output "artifact_registry_repo_name" {
  description = "The name of the Artifact Registry repository"
  value       = google_artifact_registry_repository.docker_repo.name
}

output "cloud_run_service_account_email" {
  description = "Email of the Cloud Run service account"
  value       = google_service_account.cloud_run_sa.email
}
