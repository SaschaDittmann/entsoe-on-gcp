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
country_codes = Variable.get("entsoe_country_codes").split(",")
client = EntsoePandasClient(api_key=entsoe_api_key)

cloud_storage = GoogleCloudStorageHook()
entsoe_bucket_name = Variable.get("entsoe_bucket_name")

default_dag_args = {
    'owner': 'airflow',
    'start_date': days_ago(1),
}

with DAG(
        'query_actual_load',
        schedule_interval="0 */6 * * *",
        catchup=False,
        dagrun_timeout=timedelta(minutes=15),
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

    def store_actual_load(ti, ds, **kwargs):
        tmpdir = ti.xcom_pull(task_ids='setup_pipeline',
                              key='temp_directory')
        os.makedirs(tmpdir, exist_ok=True)
        logging.info(f"Data Directory (local): {tmpdir}")

        country_code = kwargs['country_code']
        logging.info(f"Country Code: {country_code}")
        execution_date = datetime.strptime(ds, '%Y-%m-%d')
        logging.info(f"Execution Date: {execution_date}")
        entsoe_start = execution_date
        logging.info(f"Start Day: {entsoe_start}")
        entsoe_end = entsoe_start + timedelta(days=1)
        logging.info(f"End Day: {entsoe_end}")

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

        tmp_file_path = f"{tmpdir}/actual_load.parquet"
        load_forecast.to_parquet(tmp_file_path)

        object_name = f"actual_load/{execution_date.strftime('year=%Y/month=%m/day=%d')}/actual_load_{country_code.lower()}.parquet"
        cloud_storage.upload(entsoe_bucket_name, object_name, tmp_file_path)
    store_actual_load_tasks = []
    for country_code in country_codes:
        store_actual_load_task = PythonOperator(
            task_id=f"store_actual_load_{country_code.lower()}",
            provide_context=True,
            python_callable=store_actual_load,
            op_kwargs={'country_code': country_code},
            dag=dag)
        setup_pipeline >> store_actual_load_task >> cleanup_pipeline
        store_actual_load_tasks.append(store_actual_load_task)
