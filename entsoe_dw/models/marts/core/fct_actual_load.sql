{{ config (
    materialized="table",
    partition_by={
      "field": "ts",
      "data_type": "timestamp",
      "granularity": "day"
    },
    cluster_by = ["ts"],
)}}

with load_forecast as (
    SELECT *
    FROM {{ ref('stg_actual_load') }}
)

SELECT  l.ts AS ts
        , l.actual_load AS actual_load
FROM    load_forecast l
