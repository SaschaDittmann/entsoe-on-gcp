{{ config (
    materialized="table",
    partition_by={
      "field": "ts",
      "data_type": "timestamp",
      "granularity": "day"
    }
)}}

SELECT DISTINCT
       country_code,
       ts,
       actual_load
FROM   {{ source('entsoe', 'vw_actual_load') }}
