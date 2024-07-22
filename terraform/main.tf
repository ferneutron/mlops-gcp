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
            //empty for now
        }
    }
}
