resource "google_service_account" "composer_service_account" {
  account_id   = "composer-env-account"
  display_name = "Service Account for Composer Environment"
}

resource "google_service_account_iam_member" "composer_service_agent_v2" {
  provider           = google-beta
  service_account_id = google_service_account.composer_service_account.id
  role               = "roles/composer.ServiceAgentV2Ext"
  member             = "serviceAccount:service-${data.google_project.project.number}@cloudcomposer-accounts.iam.gserviceaccount.com"
}

resource "google_project_iam_member" "composer_sa_composer_worker" {
  project = var.project_id
  role    = "roles/composer.worker"
  member  = "serviceAccount:${google_service_account.composer_service_account.email}"
}

resource "google_project_iam_member" "composer_sa_storage_object_viewer" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.composer_service_account.email}"
}

resource "google_project_iam_member" "composer_sa_storage_object_creator" {
  project = var.project_id
  role    = "roles/storage.objectCreator"
  member  = "serviceAccount:${google_service_account.composer_service_account.email}"
}

resource "google_project_iam_member" "composer_sa_cloudbuild_builds_editor" {
  project = var.project_id
  role    = "roles/cloudbuild.builds.editor"
  member  = "serviceAccount:${google_service_account.composer_service_account.email}"
}

resource "google_service_account" "dbt_service_account" {
  account_id   = "dbt-service-account"
  display_name = "Service Account for the Data Build Tool (DBT)"
}

resource "google_service_account_key" "dbt_service_account_key" {
  service_account_id = google_service_account.dbt_service_account.name
  public_key_type    = "TYPE_X509_PEM_FILE"
}

resource "google_project_iam_member" "dbt_sa_storage_object_viewer" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.dbt_service_account.email}"
}

resource "google_project_iam_member" "dbt_sa_bigquery_data_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.dbt_service_account.email}"
}

resource "google_project_iam_member" "dbt_sa_bigquery_user" {
  project = var.project_id
  role    = "roles/bigquery.user"
  member  = "serviceAccount:${google_service_account.dbt_service_account.email}"
}

resource "google_project_iam_member" "dbt_sa_bigquery_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.dbt_service_account.email}"
}

resource "google_project_service_identity" "cloud_build_sa" {
  provider = google-beta

  project = data.google_project.project.project_id
  service = "cloudbuild.googleapis.com"
}

resource "google_project_iam_member" "cloud_build_sa_cloud_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_project_service_identity.cloud_build_sa.email}"
}

resource "google_project_iam_member" "cloud_build_sa_service_account_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_project_service_identity.cloud_build_sa.email}"
}
