#!/bin/bash
# Airflow database initialized
echo "Initializing Airflow database..."
airflow db migrate
echo "Airflow database initialized."

# Admin 계정이 없을 때만 새로 생성
echo "Creating admin user if it does not exist..."
airflow users create \
    --username "$AIRFLOW_ADMIN_USERNAME" \
    --firstname "$AIRFLOW_ADMIN_FIRSTNAME" \
    --lastname "$AIRFLOW_ADMIN_LASTNAME" \
    --role Admin \
    --email "$AIRFLOW_ADMIN_EMAIL" \
    --password "$AIRFLOW_ADMIN_PASSWORD"
echo "Admin user created."

# Set up database connections via Airflow CLI (Postgres and MySQL as examples)
airflow connections add 'aws_rds_connection' \
    --conn-uri 'postgresql://admin:ciftag@ciftag-db.cr0068guyz3r.ap-northeast-2.rds.amazonaws.com:5432/ciftag'

airflow connections add 'main_postgresql_dev_connection' \
    --conn-uri 'postgresql://admin:ciftag@ciftag-postgres-svc.ciftag:5432/dev'

airflow connections add 'main_dev_server_connection' \
    --conn-uri 'http://ciftag-api-module-svc.ciftag:5000'

# Set Airflow Variable for base_script_path
airflow variables set base_script_path "/opt/airflow/scripts"

# Start Celery worker
echo "Starting Airflow Celery worker..."
airflow celery worker &
echo "Airflow Celery worker started."

# Check if the first argument is "scheduler"
if [ "$1" == "scheduler" ]; then
    echo "Starting Airflow Scheduler..."
    airflow scheduler
else
    echo "No valid argument provided. Exiting."
    airflow webserver
fi

# Continue with the default entrypoint
exec "$@"