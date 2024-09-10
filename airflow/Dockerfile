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

# Copy entrypoint script
COPY ./entrypoint.sh /entrypoint.sh

# Copy DAGs or other Airflow config
COPY ./dags ${AIRFLOW_HOME}/dags
COPY ./scripts ${AIRFLOW_HOME}/scripts
COPY ./plugins ${AIRFLOW_HOME}/plugins

# Copy conf
COPY ./webserver_config.py ${AIRFLOW_HOME}/webserver_config.py
COPY ./airflow.cfg ${AIRFLOW_HOME}/airflow.cfg

# Ensure /opt/airflow/logs/ has the right permissions
RUN mkdir -p ${AIRFLOW_HOME}/logs \
    && chmod -R 777 ${AIRFLOW_HOME}/logs

# Set ownership for airflow user
RUN chown -R airflow: ${AIRFLOW_HOME}

# Set permissions for the main directories
RUN chmod -R 755 ${AIRFLOW_HOME}/dags ${AIRFLOW_HOME}/plugins \
    && chmod 644 ${AIRFLOW_HOME}/airflow.cfg ${AIRFLOW_HOME}/webserver_config.py

# Switch back to airflow user
USER airflow
# Define the default entrypoint
ENTRYPOINT ["/entrypoint.sh"]
