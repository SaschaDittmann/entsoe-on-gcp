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
        'query_actual_load',
        schedule_interval="0 * * * *",
        catchup=False,
        dagrun_timeout=timedelta(minutes=15),
        default_args=default_dag_args) as dag:

    def store_actual_load(ds, **kwargs):
        logging.info(f"Country Code: {country_code}")
        execution_date = datetime.strptime(ds, '%Y-%m-%d')
        logging.info(f"Execution Date: {execution_date}")
        entsoe_start = execution_date
        logging.info(f"Start Day: {entsoe_start}")
        entsoe_end = entsoe_start + timedelta(days=1)
        logging.info(f"End Day: {entsoe_start}")

        start = pd.Timestamp(entsoe_start.strftime("%Y%m%d"), tz='UTC')
        end = pd.Timestamp(entsoe_end.strftime("%Y%m%d"), tz='UTC')

        load_forecast = client.query_load(
            country_code, start=start, end=end)
        load_forecast = load_forecast \
            .reset_index(level=0) \
            .assign(country_code=country_code) \
            .rename(columns={
                "index": "ts",
                "Actual Load": "actual_load"
            })

        tmp_file_path = '/home/airflow/gcs/data/actual_load.parquet'
        load_forecast.to_parquet(tmp_file_path)

        object_name = f"actual_load/{execution_date.strftime('year=%Y/month=%m/day=%d')}/actual_load.parquet"
        cloud_storage.upload(entsoe_bucket_name, object_name, tmp_file_path)
    store_load_forecast_task = PythonOperator(
        task_id='store_actual_load',
        provide_context=True,
        python_callable=store_actual_load)
