from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime
import requests
import psycopg2

# Configuration de la base de données PostgreSQL
DB_CONFIG = {
    "host": "postgres",
    "database": "airflow_db",
    "user": "airflow",
    "password": "airflow",
}

# URL de l'API publique (exemple : taux Bitcoin)
API_URL = "https://api.coindesk.com/v1/bpi/currentprice.json"

# Fonction d'extraction
def extract_data():
    response = requests.get(API_URL)
    response.raise_for_status()  # Vérifie les erreurs HTTP
    data = response.json()
    return data

# Fonction de transformation
def transform_data(**context):
    raw_data = context['ti'].xcom_pull(task_ids='extract_task')
    transformed_data = {
        "time": raw_data["time"]["updated"],
        "currency": "USD",
        "rate": float(raw_data["bpi"]["USD"]["rate"].replace(",", "")),
    }
    return transformed_data

# Fonction de chargement
def load_data(**context):
    transformed_data = context['ti'].xcom_pull(task_ids='transform_task')
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Création de la table si elle n'existe pas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bitcoin_rates (
            time TEXT,
            currency TEXT,
            rate FLOAT
        )
    """)
    conn.commit()

    # Insertion des données
    cursor.execute("""
        INSERT INTO bitcoin_rates (time, currency, rate)
        VALUES (%s, %s, %s)
    """, (transformed_data["time"], transformed_data["currency"], transformed_data["rate"]))
    conn.commit()
    cursor.close()
    conn.close()

# Définition du DAG
default_args = {
    "start_date": datetime(2023, 1, 1),
    "retries": 1,
}

with DAG(
    "etl_pipeline",
    default_args=default_args,
    schedule_interval="@hourly",  # Exécution toutes les heures
    catchup=False,
) as dag:

    # Tâches ETL
    extract_task = PythonOperator(
        task_id="extract_task",
        python_callable=extract_data,
    )

    transform_task = PythonOperator(
        task_id="transform_task",
        python_callable=transform_data,
        provide_context=True,
    )

    load_task = PythonOperator(
        task_id="load_task",
        python_callable=load_data,
        provide_context=True,
    )

    # Définition de la séquence des tâches
    extract_task >> transform_task >> load_task
