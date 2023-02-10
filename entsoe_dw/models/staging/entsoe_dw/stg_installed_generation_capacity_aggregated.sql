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
       biomass_actual_aggregated,
       fossil_brown_coal_lignite_actual_aggregated,
       fossil_gas_actual_aggregated,
       fossil_hard_coal_actual_aggregated,
       fossil_oil_actual_aggregated,
       geothermal_actual_aggregated,
       hydro_pumped_storage_actual_aggregated,
       hydro_pumped_storage_actual_consumption,
       hydro_run_of_river_and_poundage_actual_aggregated,
       hydro_water_reservoir_actual_aggregated,
       nuclear_actual_aggregated,
       other_actual_aggregated,
       other_renewable_actual_aggregated,
       solar_actual_aggregated,
       solar_actual_consumption,
       waste_actual_aggregated,
       wind_offshore_actual_aggregated,
       wind_onshore_actual_aggregated,
       wind_onshore_actual_consumption
FROM   {{ source('entsoe', 'vw_installed_generation_capacity_aggregated') }}
