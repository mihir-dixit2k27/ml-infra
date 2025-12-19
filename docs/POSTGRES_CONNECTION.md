# PostgreSQL Connection Guide

## Correct Connection Credentials

Based on `docker-compose.yml` configuration:

- **Username**: `mlflow_user`
- **Password**: `mlflow_password` (default)
- **Database**: `mlflow_db`
- **Host**: `localhost` (from host) or `postgres` (from Docker network)
- **Port**: `5433` (host) or `5432` (container)

## Connection Methods

### 1. Connect from Host Machine

```bash
# Using psql
docker exec -it postgres_db psql -U mlflow_user -d mlflow_db

# Or connect directly via host port
psql -h localhost -p 5433 -U mlflow_user -d mlflow_db

# With password prompt
PGPASSWORD=mlflow_password psql -h localhost -p 5433 -U mlflow_user -d mlflow_db
```

### 2. Connect from Docker Container

```bash
# From API container (internal network)
docker exec -it fast_api psql -h postgres -p 5432 -U mlflow_user -d mlflow_db
```

### 3. Connection String Format

```bash
# For psql
postgresql://mlflow_user:mlflow_password@localhost:5433/mlflow_db

# For applications (internal Docker network)
postgresql://mlflow_user:mlflow_password@postgres:5432/mlflow_db
```

## Useful Commands

```sql
-- List all tables
\dt

-- List all schemas
\dn

-- Describe a table
\d table_name

-- List MLflow experiments
SELECT * FROM experiments;

-- List registered models
SELECT * FROM registered_models;

-- Exit psql
\q
```

## Verify Connection

```bash
# Test connection
docker exec postgres_db psql -U mlflow_user -d mlflow_db -c "SELECT version();"
```



