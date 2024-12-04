import os
import pandas as pd
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from transform_script import transfrom


def extract_data(**kwargs):
    """Извлечение данных из файла profit_table.csv"""
    profit_table = pd.read_csv('dags/profit_table.csv')
    profit_table.to_parquet('dags/profit_table_extracted.parquet', index=False)
    kwargs['ti'].xcom_push(key='profit_table_path', value='dags/profit_table_extracted.parquet')


def transform_data(**kwargs):
    """Обработка данных с использованием transform"""
    ti = kwargs['ti']
    profit_table = pd.read_parquet(ti.xcom_pull(key='profit_table_path'))
    transformed_data = transfrom(profit_table, kwargs['ds'])
    ti.xcom_push(key='transformed_data', value=transformed_data.to_dict())

# def transform_product_data(product, **kwargs):
#     """Обработка данных для отдельного продукта"""
#     ti = kwargs['ti']
#     profit_table = pd.read_parquet(ti.xcom_pull(key='profit_table_path'))
#     filtered_table = profit_table[['id', f'sum_{product}', f'count_{product}', 'date']]
#     transformed_data = transfrom(filtered_table, kwargs['ds'])
#     ti.xcom_push(key=f'transformed_data_{product}', value=transformed_data.to_dict())

def load_data(**kwargs):
    """Сохранение обработанных данных в файл flags_activity.csv"""
    ti = kwargs['ti']
    transformed_data = pd.DataFrame(ti.xcom_pull(key='transformed_data'))
    if os.path.exists('dags/flags_activity.csv'):
        existing_data = pd.read_csv('dags/flags_activity.csv')
        combined_data = pd.concat([existing_data, transformed_data], ignore_index=True)
    else:
        combined_data = transformed_data
    combined_data.to_csv('dags/flags_activity.csv', index=False)


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
        'etl_client_activity_EFIMOVICH_EVGENII',
        default_args=default_args,
        description='ETL для витрины активности клиентов',
        schedule_interval='0 0 5 * *',  # Запуск каждый месяц 5-го числа
        start_date=datetime(2023, 10, 1),
        catchup=False,
) as dag:
    extract_task = PythonOperator(
        task_id='extract',
        python_callable=extract_data,
    )

    # transform_tasks = []
    # for product in 'abcdefghij':
    #     task = PythonOperator(
    #         task_id=f'transform_{product}',
    #         python_callable=transform_product_data,
    #         op_kwargs={'product': product},
    #     )
    #     transform_tasks.append(task)

    transform_task = PythonOperator(
        task_id='transform',
        python_callable=transform_data,
    )


    load_task = PythonOperator(
        task_id='load',
        python_callable=load_data,
    )

    extract_task >> transform_task >> load_task
