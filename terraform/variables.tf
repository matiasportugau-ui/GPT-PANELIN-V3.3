# Terraform Variables
# Define input variables for the infrastructure deployment

variable "project_id" {
  description = "The GCP project ID where resources will be created"
  type        = string
}

variable "region" {
  description = "The GCP region for resource deployment"
  type        = string
  default     = "us-central1"
}

variable "db_root_password" {
  description = "Root password for the Cloud SQL PostgreSQL instance"
  type        = string
  sensitive   = true
}
