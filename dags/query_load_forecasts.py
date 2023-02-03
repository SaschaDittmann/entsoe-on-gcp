from __future__ import print_function
from datetime import datetime, timedelta
import logging

from entsoe import EntsoePandasClient
import pandas as pd

from airflow import DAG, settings
from airflow.models import Variable
from airflow.models.connection import Connection
from airflow.utils.task_group import TaskGroup
from airflow.utils.dates import days_ago

from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator

from airflow.contrib.hooks.gcs_hook import GoogleCloudStorageHook

entsoe_api_key = Variable.get("entsoe_api_key")
country_code = Variable.get("entsoe_country_code")
client = EntsoePandasClient(api_key=entsoe_api_key)

cloud_storage = GoogleCloudStorageHook()
entsoe_bucket_name = Variable.get("entsoe_bucket_name")

default_dag_args = {
    'owner': 'airflow',
    'start_date': days_ago(1),
}

with DAG(
        'query_load_forecasts',
        schedule_interval="0 6 * * *",
        catchup=False,
        dagrun_timeout=timedelta(minutes=60),
        default_args=default_dag_args) as dag:

    def store_load_forecast(ds, **kwargs):
        logging.info(f"Country Code: {country_code}")
        execution_date = datetime.strptime(ds, '%Y-%m-%d')
        logging.info(f"Execution Date: {execution_date}")
        entsoe_start = execution_date + timedelta(days=1)
        logging.info(f"Start Day: {entsoe_start}")
        entsoe_end = entsoe_start + timedelta(days=1)
        logging.info(f"End Day: {entsoe_start}")

        start = pd.Timestamp(entsoe_start.strftime("%Y%m%d"), tz='UTC')
        end = pd.Timestamp(entsoe_end.strftime("%Y%m%d"), tz='UTC')

        load_forecast = client.query_load_forecast(
            country_code, start=start, end=end)
        load_forecast = load_forecast \
            .reset_index(level=0) \
            .assign(country_code=country_code) \
            .rename(columns={
                "index": "ts",
                "Forecasted Load": "forecasted_load"
            })

        tmp_file_path = '/home/airflow/gcs/data/load_forecast.parquet'
        load_forecast.to_parquet(tmp_file_path)

        object_name = f"load_forecast/{execution_date.strftime('%Y/%m/%d')}/load_forecast.parquet"
        cloud_storage.upload(entsoe_bucket_name, object_name, tmp_file_path)
    store_load_forecast_task = PythonOperator(
        task_id='store_load_forecast',
        provide_context=True,
        python_callable=store_load_forecast)

    def store_wind_and_solar_forecast(ds, **kwargs):
        logging.info(f"Country Code: {country_code}")
        execution_date = datetime.strptime(ds, '%Y-%m-%d')
        logging.info(f"Execution Date: {execution_date}")
        entsoe_start = execution_date + timedelta(days=1)
        logging.info(f"Start Day: {entsoe_start}")
        entsoe_end = entsoe_start + timedelta(days=1)
        logging.info(f"End Day: {entsoe_start}")

        start = pd.Timestamp(entsoe_start.strftime("%Y%m%d"), tz='UTC')
        end = pd.Timestamp(entsoe_end.strftime("%Y%m%d"), tz='UTC')

        wind_and_solar_forecast = client.query_wind_and_solar_forecast(
            country_code, start=start, end=end)
        wind_and_solar_forecast = wind_and_solar_forecast \
            .reset_index(level=0) \
            .assign(country_code=country_code) \
            .rename(columns={
                "index": "ts",
                "Solar": "solar",
                "Wind Offshore": "wind_onshore",
                "Wind Onshore": "wind_offshore"
            })

        tmp_file_path = '/home/airflow/gcs/data/wind_and_solar_forecast.parquet'
        wind_and_solar_forecast.to_parquet(tmp_file_path)

        object_name = f"wind_and_solar_forecast/{execution_date.strftime('%Y/%m/%d')}/wind_and_solar_forecast.parquet"
        cloud_storage.upload(entsoe_bucket_name, object_name, tmp_file_path)
    store_wind_and_solar_forecast_task = PythonOperator(
        task_id='wind_and_solar_forecast',
        provide_context=True,
        python_callable=store_wind_and_solar_forecast)
