FROM apache/airflow:2.7.0

# Set environment variables
ENV AIRFLOW_HOME=/opt/airflow

# Switch to root user to install dependencies
USER root

# Install any additional dependencies you need
# Example: installing vim and postgresql client
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    vim \
    postgresql-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Ensure /fernet_key has the right permissions
RUN touch /fernet_key \
    && chmod 666 /fernet_key

# Copy entrypoint script
COPY ./entrypoint.sh /entrypoint.sh

# Set permissions for the airflow user
RUN chown -R airflow: ${AIRFLOW_HOME} \
    && chmod -R 777 ${AIRFLOW_HOME}

# Copy conf
COPY ./webserver_config.py ${AIRFLOW_HOME}/webserver_config.py
COPY ./airflow.cfg ${AIRFLOW_HOME}/airflow.cfg

# Switch back to airflow user
USER airflow

# Copy DAGs or other Airflow config
COPY ./dags ${AIRFLOW_HOME}/dags
COPY ./plugins ${AIRFLOW_HOME}/plugins

# Define the default entrypoint
ENTRYPOINT ["/entrypoint.sh"]
