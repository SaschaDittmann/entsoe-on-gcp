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
        'query_installed_generation_capacity_aggregated',
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

    def store_installed_generation_capacity_aggregated(ti, ds, **kwargs):
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

        generation = client.query_generation(
            country_code, start=start, end=end)

        generation = generation.reset_index(level=0)
        column_names = list(generation.columns.values)
        column_names[0] = 'ts'
        column_names[1] = 'biomass_actual_aggregated'
        column_names[2] = 'fossil_brown_coal_lignite_actual_aggregated'
        column_names[3] = 'fossil_gas_actual_aggregated'
        column_names[4] = 'fossil_hard_coal_actual_aggregated'
        column_names[5] = 'fossil_oil_actual_aggregated'
        column_names[6] = 'geothermal_actual_aggregated'
        column_names[7] = 'hydro_pumped_storage_actual_aggregated'
        column_names[8] = 'hydro_pumped_storage_actual_consumption'
        column_names[9] = 'hydro_run_of_river_and_poundage_actual_aggregated'
        column_names[10] = 'hydro_water_reservoir_actual_aggregated'
        column_names[11] = 'nuclear_actual_aggregated'
        column_names[12] = 'other_actual_aggregated'
        column_names[13] = 'other_renewable_actual_aggregated'
        column_names[14] = 'solar_actual_aggregated'
        column_names[15] = 'solar_actual_consumption'
        column_names[16] = 'waste_actual_aggregated'
        column_names[17] = 'wind_offshore_actual_aggregated'
        column_names[18] = 'wind_onshore_actual_aggregated'
        column_names[19] = 'wind_onshore_actual_consumption'
        generation.columns = column_names
        generation = generation.assign(country_code=country_code)

        tmp_file_path = f"{tmpdir}/installed_generation_capacity_aggregated_{country_code.lower()}.parquet"
        generation.to_parquet(tmp_file_path)

        object_name = f"installed_generation_capacity_aggregated/{execution_date.strftime('year=%Y/month=%m/day=%d')}/installed_generation_capacity_aggregated_{country_code.lower()}.parquet"
        cloud_storage.upload(entsoe_bucket_name, object_name, tmp_file_path)
    store_installed_generation_capacity_aggregated_tasks = []
    for country_code in country_codes:
        store_installed_generation_capacity_aggregated_task = PythonOperator(
            task_id=f"store_installed_generation_capacity_aggregated_{country_code.lower()}",
            provide_context=True,
            python_callable=store_installed_generation_capacity_aggregated,
            op_kwargs={'country_code': country_code},
            dag=dag)
        setup_pipeline >> store_installed_generation_capacity_aggregated_task >> cleanup_pipeline
        store_installed_generation_capacity_aggregated_tasks.append(
            store_installed_generation_capacity_aggregated_task)
