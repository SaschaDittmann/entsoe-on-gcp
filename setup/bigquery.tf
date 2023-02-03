locals {
  path   = "../bigquery"
  tables = jsondecode(file("${local.path}/tables.json"))["tables"]
}

resource "google_bigquery_dataset" "entsoe_dataset" {
  dataset_id  = "entsoe"
  description = "Extracted data from ENTSO-E Transparency Platform"
  location    = var.data_location
}

resource "google_bigquery_table" "default" {
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
