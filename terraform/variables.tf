variable "project_id" {
    description = "project_id"
    type = string
    sensitive = true
}

variable "location" {
    description = "location"
    type = string
    sensitive = true
}

variable "service_account_key" {
    description = "service_account_key"
    sensitive = true
}

variable "service_account_name" {
    description = "service_account_name"
    type = string
    sensitive = true
}

variable "roles_list" {
    description = "roles_list"
    type = list(string)
    sensitive = false
    default = [
        "roles/artifactregistry.writer",
        "roles/bigquery.admin",
        "roles/bigquery.readSessionUser",
        "roles/cloudbuild.builds.builder",
        "roles/cloudbuild.tokenAccessor",
        "roles/cloudbuild.workerPoolUser",
        "roles/cloudfunctions.developer",
        "roles/run.invoker",
        "roles/logging.logWriter",
        "roles/iam.serviceAccountUser",
        "roles/aiplatform.user",
        "roles/developerconnect.user",
        "roles/storage.objectCreator"
    ]
}
