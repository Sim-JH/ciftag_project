#!/bin/bash

# Check if AIRFLOW__CORE__FERNET_KEY is set, if not, generate one
if [ -z "$AIRFLOW__CORE__FERNET_KEY" ]; then
    echo "Generating Fernet key..."
    export AIRFLOW__CORE__FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    echo "Fernet key generated: $AIRFLOW__CORE__FERNET_KEY"
fi

# Airflow database initialized
echo "Initializing Airflow database..."
airflow db init
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
    --conn-uri 'ciftag-db.cr0068guyz3r.ap-northeast-2.rds.amazonaws.com'

airflow connections add 'local_postgresl_connection' \
    --conn-uri 'postgresql://admin:ciftag@ciftag-postgres/ciftag'

# Continue with the default entrypoint
exec "$@"