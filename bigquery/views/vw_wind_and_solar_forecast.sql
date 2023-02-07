SELECT country_code,
       ts,
       solar,
       wind_offshore,
       wind_onshore,
       DATETIME(year, month, day, 0, 0, 0) AS import_date
FROM  `entsoe.wind_and_solar_forecast`
