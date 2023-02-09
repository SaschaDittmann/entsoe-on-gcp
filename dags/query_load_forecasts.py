from __future__ import print_function
from datetime import datetime, timedelta
import logging
import tempfile
import os
import shutil

from entsoe import EntsoePandasClient
import pandas as pd

from airflow import DAG, settings
from airflow.models import Variable
from airflow.models.connection import Connection
from airflow.utils.task_group import TaskGroup
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule

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
    'start_date': days_ago(7),
}

with DAG(
        'query_load_forecasts',
        schedule_interval="0 6 * * *",
        catchup=True,
        dagrun_timeout=timedelta(minutes=60),
        default_args=default_dag_args) as dag:

    def create_temp_directory(ti):
        tmpdir = tempfile.TemporaryDirectory()
        logging.info(f"directory {tmpdir.name} created")
        assert os.path.exists(tmpdir.name)
        ti.xcom_push(key='temp_directory', value=tmpdir.name)
    setup_pipeline = PythonOperator(
        task_id='setup_pipeline',
        python_callable=create_temp_directory)

    def remove_temp_directory(ti):
        tmpdir = ti.xcom_pull(task_ids='setup_pipeline',
                              key='temp_directory')
        if os.path.exists(tmpdir):
            shutil.rmtree(tmpdir)
            logging.info(f"directory {tmpdir} removed")
    cleanup_pipeline = PythonOperator(
        task_id='cleanup_pipeline',
        trigger_rule=TriggerRule.ALL_DONE,
        python_callable=remove_temp_directory)

    def store_load_forecast(ti, ds, **kwargs):
        tmpdir = ti.xcom_pull(task_ids='setup_pipeline',
                              key='temp_directory')
        os.makedirs(tmpdir, exist_ok=True)
        logging.info(f"Data Directory (local): {tmpdir}")

        logging.info(f"Country Code: {country_code}")
        execution_date = datetime.strptime(ds, '%Y-%m-%d')
        logging.info(f"Execution Date: {execution_date}")
        entsoe_start = execution_date + timedelta(days=1)
        logging.info(f"Start Day: {entsoe_start}")
        entsoe_end = entsoe_start + timedelta(days=1)
        logging.info(f"End Day: {entsoe_end}")

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

        tmp_file_path = f"{tmpdir}/load_forecast.parquet"
        load_forecast.to_parquet(tmp_file_path)

        object_name = f"load_forecast/{execution_date.strftime('year=%Y/month=%m/day=%d')}/load_forecast.parquet"
        cloud_storage.upload(entsoe_bucket_name, object_name, tmp_file_path)
    store_load_forecast_task = PythonOperator(
        task_id='store_load_forecast',
        provide_context=True,
        python_callable=store_load_forecast)

    def store_wind_and_solar_forecast(ti, ds, **kwargs):
        tmpdir = ti.xcom_pull(task_ids='setup_pipeline',
                              key='temp_directory')
        os.makedirs(tmpdir, exist_ok=True)
        logging.info(f"Data Directory (local): {tmpdir}")

        logging.info(f"Country Code: {country_code}")
        execution_date = datetime.strptime(ds, '%Y-%m-%d')
        logging.info(f"Execution Date: {execution_date}")
        entsoe_start = execution_date + timedelta(days=1)
        logging.info(f"Start Day: {entsoe_start}")
        entsoe_end = entsoe_start + timedelta(days=1)
        logging.info(f"End Day: {entsoe_end}")

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

        tmp_file_path = f"{tmpdir}/wind_and_solar_forecast.parquet"
        wind_and_solar_forecast.to_parquet(tmp_file_path)

        object_name = f"wind_and_solar_forecast/{execution_date.strftime('year=%Y/month=%m/day=%d')}/wind_and_solar_forecast.parquet"
        cloud_storage.upload(entsoe_bucket_name, object_name, tmp_file_path)
    store_wind_and_solar_forecast_task = PythonOperator(
        task_id='wind_and_solar_forecast',
        provide_context=True,
        python_callable=store_wind_and_solar_forecast)

    setup_pipeline >> store_load_forecast_task >> cleanup_pipeline
    setup_pipeline >> store_wind_and_solar_forecast_task >> cleanup_pipeline
