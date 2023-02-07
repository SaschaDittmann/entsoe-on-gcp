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
       solar,
       wind_offshore,
       wind_onshore
FROM   {{ source('entsoe', 'vw_wind_and_solar_forecast') }}
