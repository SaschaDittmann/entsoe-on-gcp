locals {
  path            = "../bigquery"
  tables          = jsondecode(file("${local.path}/tables.json"))["tables"]
  external_tables = jsondecode(file("${local.path}/external-tables.json"))["tables"]
}

resource "google_bigquery_dataset" "entsoe_dataset" {
  dataset_id  = "entsoe"
  description = "Extracted data from ENTSO-E Transparency Platform"
  location    = var.data_location
}

resource "google_bigquery_table" "internal_tables" {
  for_each   = local.tables
  dataset_id = google_bigquery_dataset.entsoe_dataset.dataset_id
  table_id   = each.value["table_id"]
  schema     = file("${local.path}/schema/${each.value["table_id"]}.json")

  dynamic "time_partitioning" {
    for_each = [
      var.time_partitioning
    ]
    content {
      type                     = try(each.value["partition_type"], time_partitioning.value["type"])
      field                    = try(each.value["partition_field"], time_partitioning.value["field"])
      expiration_ms            = try(time_partitioning.value["expiration_ms"], null)
      require_partition_filter = try(time_partitioning.value["require_partition_filter"], null)
    }
  }
  clustering = try(each.value["clustering"], [])
}

resource "google_storage_bucket_object" "dummy_data" {
  for_each = fileset("${local.path}/data", "**")

  name   = each.value
  source = "${local.path}/data/${each.value}"
  bucket = google_storage_bucket.entsoe_data_bucket.name
}

resource "google_bigquery_table" "external_tables" {
  for_each            = local.external_tables
  dataset_id          = google_bigquery_dataset.entsoe_dataset.dataset_id
  table_id            = each.value["table_id"]
  schema              = file("${local.path}/schema/${each.value["table_id"]}.json")
  deletion_protection = false
  depends_on = [
    google_storage_bucket_object.dummy_data
  ]

  external_data_configuration {
    autodetect    = each.value["external_data_autodetect"]
    source_format = each.value["source_format"]
    source_uris   = each.value["source_uris"]
    hive_partitioning_options {
      mode                     = each.value["hive_partitioning_mode"]
      require_partition_filter = false
      source_uri_prefix        = each.value["source_uri_prefix"]
    }
  }
}

resource "google_bigquery_table" "views" {
  for_each            = fileset("${local.path}/views", "*.sql")
  dataset_id          = google_bigquery_dataset.entsoe_dataset.dataset_id
  table_id            = replace(each.value, ".sql", "")
  deletion_protection = false
  depends_on = [
    google_bigquery_table.internal_tables,
    google_bigquery_table.external_tables
  ]

  view {
    query          = file("${local.path}/views/${each.value}")
    use_legacy_sql = false
  }
}

resource "google_bigquery_dataset" "entsoe_dw_dataset" {
  dataset_id  = "entsoe_dw"
  description = "ENTSO-E Transparency Data Warehouse"
  location    = var.data_location
}
