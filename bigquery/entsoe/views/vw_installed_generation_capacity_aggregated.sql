SELECT country_code,
       ts,
       DATETIME(year, month, day, 0, 0, 0) AS import_date
FROM  `entsoe.installed_generation_capacity_aggregated`
