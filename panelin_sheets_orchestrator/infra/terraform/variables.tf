variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type        = string
  default     = "us-central1"
  description = "GCP region for Cloud Run / Artifact Registry"
}

variable "service_name" {
  type        = string
  default     = "panelin-sheets-orchestrator"
  description = "Cloud Run service name"
}

variable "artifact_repo" {
  type        = string
  default     = "panelin"
  description = "Artifact Registry Docker repository name"
}

variable "run_concurrency" {
  type        = number
  default     = 80
  description = "Max concurrent requests per Cloud Run instance"
}

variable "run_memory" {
  type        = string
  default     = "512Mi"
  description = "Cloud Run memory limit"
}

variable "run_cpu" {
  type        = string
  default     = "1"
  description = "Cloud Run vCPU count"
}

variable "run_max_instances" {
  type        = number
  default     = 5
  description = "Max Cloud Run instances"
}

variable "enable_scheduler" {
  type        = bool
  default     = false
  description = "Whether to create a Cloud Scheduler job for queue processing"
}

variable "scheduler_cron" {
  type        = string
  default     = "*/15 * * * *"
  description = "Cron schedule for queue processing"
}

variable "scheduler_time_zone" {
  type        = string
  default     = "America/Montevideo"
  description = "Time zone for Cloud Scheduler"
}

variable "scheduler_api_key" {
  type        = string
  default     = ""
  sensitive   = true
  description = "API key to use in the Cloud Scheduler X-API-Key header"
}

variable "enable_wif" {
  type        = bool
  default     = false
  description = "Enable Workload Identity Federation for GitHub Actions CI/CD"
}

variable "github_org" {
  type        = string
  default     = "matiasportugau-ui"
  description = "GitHub org/user for WIF attribute condition"
}

variable "github_repo" {
  type        = string
  default     = "GPT-PANELIN-V3.3"
  description = "GitHub repo name for WIF attribute condition"
}
