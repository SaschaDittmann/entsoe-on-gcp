SELECT country_code,
       ts,
       actual_load,
       DATETIME(year, month, day, 0, 0, 0) AS import_date
FROM  `entsoe.actual_load`
