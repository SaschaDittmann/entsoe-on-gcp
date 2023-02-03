variable "project_id" {
  description = "The ID of the project in which resources will be provisioned."
  type        = string
}

variable "storage_bucket_name" {
  description = "The name of the Cloud Storage bucket, which is used to store files extracted from the ENTSO-E platform."
  type        = string
}

variable "bq_dataset_id" { default = "entsoe" }
variable "data_location" { default = "EU" }
variable "project_region" { default = "europe-west1" }

variable "time_partitioning" {
  description = "Configures time-based partitioning for this table. cf https://www.terraform.io/docs/providers/google/r/bigquery_table.html#field"
  type        = map(string)
  default = {
    type  = "DAY"
    field = "ts"
  }
}
