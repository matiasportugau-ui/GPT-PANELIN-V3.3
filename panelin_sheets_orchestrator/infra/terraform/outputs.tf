output "cloud_run_uri" {
  value       = google_cloud_run_v2_service.svc.uri
  description = "Cloud Run service URL"
}

output "runtime_service_account" {
  value       = google_service_account.runtime.email
  description = "Runtime SA email – share the Google Sheet with this address"
}

output "wif_provider" {
  value       = var.enable_wif ? google_iam_workload_identity_pool_provider.github[0].name : "WIF disabled"
  description = "WIF provider resource name (for GitHub Actions auth)"
}

output "deployer_service_account" {
  value       = var.enable_wif ? google_service_account.deployer[0].email : "WIF disabled"
  description = "Deployer SA email (for CI/CD)"
}
