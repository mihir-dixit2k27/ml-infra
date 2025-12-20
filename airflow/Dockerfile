# airflow/Dockerfile
FROM apache/airflow:2.7.1-python3.10

# Switch to root to install system dependencies (if needed)
USER root
# (Optional) Install git or other system tools here if needed
# RUN apt-get update && apt-get install -y git

# Switch back to airflow user to install python packages
USER airflow

# Copy requirements file
COPY requirements.txt .
COPY requirements.txt /requirements.txt

# Install dependencies
# We use --no-cache-dir to keep image small
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt


# Set PYTHONPATH to include both airflow directory and user site-packages
# This ensures both /opt/airflow/src imports and user-installed packages (like joblib) work
ENV PYTHONPATH=/opt/airflow:/home/airflow/.local/lib/python3.10/site-packages:$PYTHONPATH
