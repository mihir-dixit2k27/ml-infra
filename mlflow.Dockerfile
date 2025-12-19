# MLflow Dockerfile
FROM python:3.12-slim

# Install MLflow and PostgreSQL dependencies
RUN pip install mlflow psycopg2-binary sqlalchemy

# Set working directory
WORKDIR /app

# Create directory for artifacts
RUN mkdir -p /mlruns-artifacts

# Expose MLflow port
EXPOSE 5000

# Default command (can be overridden in docker-compose.yml)
CMD ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000"]






