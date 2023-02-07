locals {
  dag_path = "../dags"
}

resource "google_storage_bucket" "entsoe_data_bucket" {
  name          = var.storage_data_bucket_name
  location      = var.data_location
  force_destroy = false

  uniform_bucket_level_access = true
}

resource "google_composer_environment" "entsoe_composer_env" {
  name    = "entsoe-composer"
  project = var.project_id
  region  = var.project_region
  depends_on = [
    google_service_account_iam_member.composer_service_agent_v2,
    google_project_iam_member.composer_sa_composer_worker
  ]

  config {
    software_config {
      image_version = "composer-2-airflow-2"

      pypi_packages = {
        "entsoe-py"          = "",
        "dbt-core"           = "~=1.3.0",
        "dbt-bigquery"       = "~=1.3.0",
        "airflow-dbt-python" = "[bigquery]"
      }
    }

    workloads_config {
      scheduler {
        cpu        = 0.5
        memory_gb  = 1.875
        storage_gb = 1
        count      = 1
      }
      web_server {
        cpu        = 0.5
        memory_gb  = 1.875
        storage_gb = 1
      }
      worker {
        cpu        = 0.5
        memory_gb  = 1.875
        storage_gb = 1
        min_count  = 1
        max_count  = 3
      }
    }

    environment_size = "ENVIRONMENT_SIZE_SMALL"

    node_config {
      network         = google_compute_network.composer_network.id
      subnetwork      = google_compute_subnetwork.composer_subnet.id
      service_account = google_service_account.composer_service_account.name
    }
  }
}

resource "google_storage_bucket_object" "dags" {
  for_each = fileset("${local.dag_path}", "**")

  name   = "dags/${each.value}"
  source = "${local.dag_path}/${each.value}"
  bucket = split("/", google_composer_environment.entsoe_composer_env.config.0.dag_gcs_prefix).2
}
