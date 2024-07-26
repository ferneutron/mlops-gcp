# GCP provider

provider "google" {
  credentials  = file(var.service_account_key)
  project      = var.project_id
  region       = var.location
}
