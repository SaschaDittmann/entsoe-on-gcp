resource "google_storage_bucket" "static_website" {
  name          = var.storage_web_bucket_name
  location      = var.data_location
  force_destroy = true

  uniform_bucket_level_access = true
}
