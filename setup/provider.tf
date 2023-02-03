terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "4.51.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "4.51.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.project_region
}

provider "google-beta" {
}

provider "null" {
}

provider "random" {
}

data "google_project" "project" {
  project_id = var.project_id
}
