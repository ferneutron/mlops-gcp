provider "google" {
    project = "gsd-ai-mx-ferneutron"
    credentials = "${file("credentials.json")}"
    region = "us-central1"
    zone = "us-central1-c"
}

resource "google_compute_instance" "terraform-instance" {
    name = "terraform-instance"
    machine_type = "f1-micro"
    zone = "us-central1-a"
    allow_stopping_for_update = true

    boot_disk {
        initialize_params {
            image = "debian-cloud/debian-11"
        }
    }

    network_interface {
        network = "default"
        access_config {
            //empty
        }
    }
}

resource "google_service_account" "sa" {
  account_id   = "mlops-test"
  display_name = "MLOpsTestSA"
  disabled     = false
  project      = "gsd-ai-mx-ferneutron"

  # Add the roles that the service account needs
  roles = [
    "roles/artifactregistry.writer",
    "roles/bigquery.admin",
    "roles/bigquery.readsessions.user",
    "roles/cloudbuild.loggingServiceAgent",
    "roles/cloudbuild.serviceAccount",
    "roles/cloudbuild.tokenAccessor",
    "roles/cloudbuild.workerpoolUser",
    "roles/cloudfunctions.admin",
    "roles/cloudfunctions.developer",
    "roles/cloudrun.admin",
    "roles/cloudrun.invoker",
    "roles/developer.connect.user",
    "roles/logging.writer",
    "roles/iam.serviceAccountUser",
    "roles/storage.admin",
    "roles/vertexai.user",
  ]
}
