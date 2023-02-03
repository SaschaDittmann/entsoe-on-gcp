resource "google_compute_network" "composer_network" {
  name                    = "composer-network"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "composer_subnet" {
  name          = "composer-subnet"
  ip_cidr_range = "10.1.0.0/16"
  region        = var.project_region
  network       = google_compute_network.composer_network.id
}
