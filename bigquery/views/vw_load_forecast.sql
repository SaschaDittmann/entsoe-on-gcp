SELECT country_code,
       ts,
       forecasted_load,
       DATETIME(year, month, day, 0, 0, 0) AS import_date
FROM  `entsoe.load_forecast`
