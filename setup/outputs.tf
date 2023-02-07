output "dag_gcs_prefix" {
  value = google_composer_environment.entsoe_composer_env.config.0.dag_gcs_prefix
}
