resource "google_service_account" "mlops-sa-v2" {
account_id   = "mlops-sa-v2"
display_name = "mlops-sa-v2"
}

resource "google_project_iam_binding" "mlops-sa-v2" {
project = var.project_id
role =  "roles/storage.admin"
members = [
  "serviceAccount:${google_service_account.mlops-sa-v2.email}"
]
}
