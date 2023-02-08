locals {
  path                 = "../bigquery"
  entsoe_int_tables    = jsondecode(file("${local.path}/entsoe/tables.json"))["tables"]
  entsoe_ext_tables    = jsondecode(replace(file("${local.path}/entsoe/external-tables.json"), "<storage_data_bucket_name>", var.storage_data_bucket_name))["tables"]
  entsoe_dw_int_tables = jsondecode(file("${local.path}/entsoe_dw/tables.json"))["tables"]
  entsoe_dw_ext_tables = jsondecode(replace(file("${local.path}/entsoe_dw/external-tables.json"), "<storage_data_bucket_name>", var.storage_data_bucket_name))["tables"]
}

resource "google_storage_bucket_object" "dummy_data" {
  for_each = fileset("${local.path}/data", "**")

  name   = each.value
  source = "${local.path}/data/${each.value}"
  bucket = google_storage_bucket.entsoe_data_bucket.name
}

resource "google_bigquery_dataset" "entsoe_dataset" {
  dataset_id  = "entsoe"
  description = "Extracted data from ENTSO-E Transparency Platform"
  location    = var.data_location
}

resource "google_bigquery_table" "entsoe_int_tables" {
  for_each   = local.entsoe_int_tables
  dataset_id = google_bigquery_dataset.entsoe_dataset.dataset_id
  table_id   = each.value["table_id"]
  schema     = file("${local.path}/entsoe/schema/${each.value["table_id"]}.json")

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

resource "google_bigquery_table" "entsoe_ext_tables" {
  for_each            = local.entsoe_ext_tables
  dataset_id          = google_bigquery_dataset.entsoe_dataset.dataset_id
  table_id            = each.value["table_id"]
  schema              = file("${local.path}/entsoe/schema/${each.value["table_id"]}.json")
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

resource "google_bigquery_table" "entsoe_views" {
  for_each            = fileset("${local.path}/entsoe/views", "*.sql")
  dataset_id          = google_bigquery_dataset.entsoe_dataset.dataset_id
  table_id            = replace(each.value, ".sql", "")
  deletion_protection = false
  depends_on = [
    google_bigquery_table.entsoe_int_tables,
    google_bigquery_table.entsoe_ext_tables
  ]

  view {
    query          = file("${local.path}/entsoe/views/${each.value}")
    use_legacy_sql = false
  }
}

resource "google_bigquery_dataset" "entsoe_dw_dataset" {
  dataset_id  = "entsoe_dw"
  description = "ENTSO-E Transparency Data Warehouse"
  location    = var.data_location
}

resource "google_bigquery_table" "entsoe_dw_int_tables" {
  for_each   = local.entsoe_dw_int_tables
  dataset_id = google_bigquery_dataset.entsoe_dw_dataset.dataset_id
  table_id   = each.value["table_id"]
  schema     = file("${local.path}/entsoe_dw/schema/${each.value["table_id"]}.json")

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

resource "google_bigquery_table" "entsoe_dw_ext_tables" {
  for_each            = local.entsoe_dw_ext_tables
  dataset_id          = google_bigquery_dataset.entsoe_dw_dataset.dataset_id
  table_id            = each.value["table_id"]
  schema              = file("${local.path}/entsoe_dw/schema/${each.value["table_id"]}.json")
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

resource "google_bigquery_table" "entsoe_dw_views" {
  for_each            = fileset("${local.path}/entsoe_dw/views", "*.sql")
  dataset_id          = google_bigquery_dataset.entsoe_dw_dataset.dataset_id
  table_id            = replace(each.value, ".sql", "")
  deletion_protection = false
  depends_on = [
    google_bigquery_table.entsoe_dw_int_tables,
    google_bigquery_table.entsoe_dw_ext_tables
  ]

  view {
    query          = file("${local.path}/entsoe_dw/views/${each.value}")
    use_legacy_sql = false
  }
}
