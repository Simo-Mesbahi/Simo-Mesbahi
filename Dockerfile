FROM apache/airflow:2.5.0

USER root
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && apt-get clean

USER airflow
COPY ./dags /opt/airflow/dags
COPY ./plugins /opt/airflow/plugins

RUN pip install --no-cache-dir -r /opt/airflow/requirements.txt
