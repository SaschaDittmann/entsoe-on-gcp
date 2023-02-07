resource "google_storage_bucket" "static_website" {
  name          = var.storage_web_bucket_name
  location      = var.data_location
  force_destroy = true

  uniform_bucket_level_access = true

  website {
    main_page_suffix = "index.html"
    not_found_page   = "404.html"
  }
}

# Upload a simple index.html page to the bucket
resource "google_storage_bucket_object" "indexpage" {
  name         = "index.html"
  content      = "<html><body>Hello World!</body></html>"
  content_type = "text/html"
  bucket       = google_storage_bucket.static_website.id
}

# Upload a simple 404 / error page to the bucket
resource "google_storage_bucket_object" "errorpage" {
  name         = "404.html"
  content      = "<html><body>404!</body></html>"
  content_type = "text/html"
  bucket       = google_storage_bucket.static_website.id
}

# Make bucket public by granting allUsers READER access
# resource "google_storage_bucket_access_control" "public_rule" {
#   bucket = google_storage_bucket.static_website.id
#   role   = "READER"
#   entity = "allUsers"
# }
