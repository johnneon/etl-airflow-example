import os
import pandas as pd
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from transform_script import transfrom

# def debug_working_directory(**kwargs):
#     """Проверка текущей рабочей директории"""
#     current_dir = os.getcwd()
#     print(f"Current working directory: {current_dir}")
#     print(f"Files in working directory: {os.listdir(os.path.join(current_dir, 'dags'))}")


# Функции для задач
def extract_data(**kwargs):
    """Извлечение данных из файла profit_table.csv"""
    profit_table = pd.read_csv('dags/profit_table.csv')  # Читаем таблицу
    # Сохраняем в Parquet
    profit_table.to_parquet('dags/profit_table_extracted.parquet', index=False)
    # Передаем путь через XCom
    kwargs['ti'].xcom_push(key='profit_table_path', value='dags/profit_table_extracted.parquet')


def transform_data(**kwargs):
    """Обработка данных с использованием transform"""
    ti = kwargs['ti']
    profit_table = pd.read_parquet(ti.xcom_pull(key='profit_table_path'))  # Загружаем данные
    transformed_data = transfrom(profit_table, kwargs['ds'])  # Обрабатываем данные
    ti.xcom_push(key='transformed_data', value=transformed_data.to_dict())  # Сохраняем данные


def load_data(**kwargs):
    """Сохранение обработанных данных в файл flags_activity.csv"""
    ti = kwargs['ti']
    transformed_data = pd.DataFrame(ti.xcom_pull(key='transformed_data'))  # Загружаем обработанные данные
    # Проверяем, существует ли файл flags_activity.csv
    if os.path.exists('dags/flags_activity.csv'):
        existing_data = pd.read_csv('dags/flags_activity.csv')
        combined_data = pd.concat([existing_data, transformed_data], ignore_index=True)
    else:
        combined_data = transformed_data
    combined_data.to_csv('dags/flags_activity.csv', index=False)  # Сохраняем данные


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
    # debug_task = PythonOperator(
    #     task_id='debug_working_directory',
    #     python_callable=debug_working_directory,
    # )

    extract_task = PythonOperator(
        task_id='extract',
        python_callable=extract_data,
    )

    transform_task = PythonOperator(
        task_id='transform',
        python_callable=transform_data,
    )

    load_task = PythonOperator(
        task_id='load',
        python_callable=load_data,
    )

    extract_task >> transform_task >> load_task
