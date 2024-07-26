resource "google_service_account" "mlops-sa-v3" {
account_id   = "mlops-sa-v3"
display_name = "Testing creation of mlops-sa-v3"
}

resource "google_project_iam_binding" "mlops-sa-v3" {
project = var.project_id
# role =  "roles/storage.admin"
count = length(var.roles_list)
role =  var.roles_list[count.index]
members = [
  "serviceAccount:${google_service_account.mlops-sa-v3.email}"
]
}
