{{ config (
    materialized="table",
    partition_by={
      "field": "ts",
      "data_type": "timestamp",
      "granularity": "day"
    }
)}}

with load_forecast as (
    SELECT *
    FROM {{ ref('stg_load_forecast') }}
),

wind_and_solar_forecast as (
    SELECT *
    FROM {{ ref('stg_wind_and_solar_forecast') }}
)

SELECT  l.ts AS ts
        , l.forecasted_load AS `load`
        , ws.solar AS solar
        , ws.wind_offshore AS wind_offshore
        , ws.wind_onshore AS wind_onshore
FROM    load_forecast l
LEFT
JOIN    wind_and_solar_forecast ws
        ON l.ts = ws.ts
