SELECT * 
FROM
(
  SELECT 
    ts
    , 'consumption' AS type
    , `load`
  FROM `entsoe_dw.fct_forecast`
  UNION ALL
  SELECT 
    ts
    , 'solar' AS type
    , solar
  FROM `entsoe_dw.fct_forecast`
  UNION ALL
  SELECT 
    ts
    , 'wind_offshore' AS type
    , wind_offshore
  FROM `entsoe_dw.fct_forecast`
  UNION ALL
  SELECT 
    ts
    , 'wind_onshore' AS type
    , wind_onshore
  FROM `entsoe_dw.fct_forecast`
)
ORDER BY ts, type
