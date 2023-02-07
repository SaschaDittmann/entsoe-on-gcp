from __future__ import print_function
from datetime import timedelta
import json
import logging
import os
import tempfile

from airflow import DAG, settings
from airflow.models import Variable
from airflow.models.connection import Connection
from airflow.utils.task_group import TaskGroup
from airflow.utils.dates import days_ago

from airflow.operators.bash_operator import BashOperator
from airflow_dbt_python.operators.dbt import (
    DbtDepsOperator,
    DbtSourceFreshnessOperator,
    DbtSeedOperator,
    DbtRunOperator,
    DbtTestOperator,
    DbtDocsGenerateOperator,
)
from airflow.operators.python_operator import PythonOperator
from airflow.providers.google.cloud.transfers.local_to_gcs import LocalFilesystemToGCSOperator

website_bucket_name = Variable.get("static_website_bucket_name")

session = settings.Session()
existing = session.query(Connection).filter_by(
    conn_id="entsoe_bigquery_connection").first()

if existing is None:
    connection_extras = {
        "method": "service-account-json",
        "project": Variable.get("dev_project_id"),
        "dataset": "entsoe_dw",
        "location": "EU",
        "job_execution_timeout_seconds": 300,
        "job_retries": 1,
        "priority": "interactive",
        "threads": 4,
        "keyfile_json": {
            "type": "service_account",
            "project_id": Variable.get("dev_project_id"),
            "private_key_id": Variable.get("dev_keyfile_private_key_id"),
            "private_key": Variable.get("dev_keyfile_private_key"),
            "client_email": Variable.get("dev_keyfile_client_email"),
            "client_id": Variable.get("dev_keyfile_client_id"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": Variable.get("dev_keyfile_client_x509_cert_url")
        }
    }

    my_conn = Connection(
        conn_id="entsoe_bigquery_connection",
        conn_type="bigquery",  # Other dbt parameters can be added as extras
        extra=json.dumps(connection_extras),
    )

    session.add(my_conn)
    session.commit()

default_dag_args = {
    'owner': 'airflow',
    'start_date': days_ago(1),
}

with DAG(
        'process_dwh',
        schedule_interval="0 8 * * *",
        max_active_runs=1,
        catchup=False,
        dagrun_timeout=timedelta(minutes=60),
        default_args=default_dag_args) as dag:

    def create_temp_directory(ti):
        tmpdir = tempfile.TemporaryDirectory()
        logging.info(f"directory {tmpdir.name} created")
        assert os.path.exists(tmpdir.name)
        ti.xcom_push(key='dbt_temp_directory', value=tmpdir.name)
    create_temp_directory_task = PythonOperator(
        task_id='create_temp_directory',
        python_callable=create_temp_directory)

    checkout = BashOperator(
        task_id='checkout',
        bash_command="""git clone {{ var.value.git_remote_url }} 
            cp -r ./entsoe-on-gcp {{ ti.xcom_pull(task_ids='create_temp_directory', key='dbt_temp_directory') }}
            """,
        dag=dag,
    )

    resolve_dependencies = DbtDepsOperator(
        task_id='resolve-dependencies',
        project_dir="{{ ti.xcom_pull(task_ids='create_temp_directory', key='dbt_temp_directory') }}/entsoe_dw",
        profiles_dir=None,
        target="entsoe_bigquery_connection",
        dag=dag,
    )

    check_source_freshness = DbtSourceFreshnessOperator(
        task_id='check-source-freshness',
        project_dir="{{ ti.xcom_pull(task_ids='create_temp_directory', key='dbt_temp_directory') }}/entsoe_dw",
        profiles_dir=None,
        target="entsoe_bigquery_connection",
        do_xcom_push_artifacts=["sources.json"],
        dag=dag,
    )

    run_source_tests = DbtTestOperator(
        task_id='run-source-tests',
        select="source:*",
        project_dir="{{ ti.xcom_pull(task_ids='create_temp_directory', key='dbt_temp_directory') }}/entsoe_dw",
        profiles_dir=None,
        target="entsoe_bigquery_connection",
        dag=dag,
    )

    add_seeds = DbtSeedOperator(
        task_id='add-seeds',
        project_dir="{{ ti.xcom_pull(task_ids='create_temp_directory', key='dbt_temp_directory') }}/entsoe_dw",
        profiles_dir=None,
        target="entsoe_bigquery_connection",
        dag=dag,
    )

    run_transformations = DbtRunOperator(
        task_id='run-transformations',
        project_dir="{{ ti.xcom_pull(task_ids='create_temp_directory', key='dbt_temp_directory') }}/entsoe_dw",
        profiles_dir=None,
        target="entsoe_bigquery_connection",
        do_xcom_push_artifacts=["manifest.json", "run_results.json"],
        dag=dag,
    )

    generate_docs = DbtDocsGenerateOperator(
        task_id='generate-docs',
        project_dir="{{ ti.xcom_pull(task_ids='create_temp_directory', key='dbt_temp_directory') }}/entsoe_dw",
        profiles_dir=None,
        target="entsoe_bigquery_connection",
        dag=dag,
    )

    run_tests = DbtTestOperator(
        task_id='run-tests',
        exclude='source:*',
        project_dir="{{ ti.xcom_pull(task_ids='create_temp_directory', key='dbt_temp_directory') }}/entsoe_dw",
        profiles_dir=None,
        target="entsoe_bigquery_connection",
        dag=dag,
    )

    upload_index_file = LocalFilesystemToGCSOperator(
        task_id="upload_index_file",
        src="{{ ti.xcom_pull(task_ids='create_temp_directory', key='dbt_temp_directory') }}/entsoe_dw/target/index.html",
        dst="{{ run_id }}/index.html",
        bucket=website_bucket_name,
    )

    upload_manifest_file = LocalFilesystemToGCSOperator(
        task_id="upload_manifest_file",
        src="{{ ti.xcom_pull(task_ids='create_temp_directory', key='dbt_temp_directory') }}/entsoe_dw/target/manifest.json",
        dst="{{ run_id }}/manifest.json",
        bucket=website_bucket_name,
    )

    upload_catalog_file = LocalFilesystemToGCSOperator(
        task_id="upload_catalog_file",
        src="{{ ti.xcom_pull(task_ids='create_temp_directory', key='dbt_temp_directory') }}/entsoe_dw/target/catalog.json",
        dst="{{ run_id }}/catalog.json",
        bucket=website_bucket_name,
    )

    create_temp_directory_task >> checkout
    checkout >> resolve_dependencies
    resolve_dependencies >> check_source_freshness
    check_source_freshness >> run_source_tests
    run_source_tests >> add_seeds
    add_seeds >> run_transformations
    run_transformations >> run_tests
    run_tests >> generate_docs
    generate_docs >> upload_index_file
    generate_docs >> upload_manifest_file
    generate_docs >> upload_catalog_file
