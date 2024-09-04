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

# Set permissions for the airflow user
RUN chown -R airflow: ${AIRFLOW_HOME} \
    && chmod -R 777 ${AIRFLOW_HOME}

# Switch back to airflow user
USER airflow

# Copy DAGs or other Airflow config (optional)
COPY ./dags ${AIRFLOW_HOME}/dags
COPY ./plugins ${AIRFLOW_HOME}/plugins

# Define the default entrypoint
ENTRYPOINT ["/entrypoint.sh"]
