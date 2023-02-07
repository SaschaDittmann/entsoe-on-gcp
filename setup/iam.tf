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

resource "google_project_iam_member" "composer_worker" {
  project = var.project_id
  role    = "roles/composer.worker"
  member  = "serviceAccount:${google_service_account.composer_service_account.email}"
}
