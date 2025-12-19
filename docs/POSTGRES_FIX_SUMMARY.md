# PostgreSQL Connection Error - Fix Summary

## Problem
User tried to connect to PostgreSQL with wrong credentials:
```bash
docker exec -it postgres_db psql -U myuser -d mlops_db
```
Error: `FATAL: role "myuser" does not exist`

## Root Cause
Using incorrect username and database name. The actual credentials are defined in `docker-compose.yml`.

## Solution
Changed connection command to use correct credentials from `docker-compose.yml`:

```bash
# CORRECT connection command
docker exec -it postgres_db psql -U mlflow_user -d mlflow_db
```

## Credentials (from docker-compose.yml)
- **Username**: `mlflow_user` (not `myuser`)
- **Password**: `mlflow_password` (default, can be overridden via env var)
- **Database**: `mlflow_db` (not `mlops_db`)
- **Host Port**: `5433` (maps to container port `5432`)

## Verification
✅ Connection successful
✅ Database accessible with 34 MLflow tables
✅ Model `telco-churn-champion` confirmed in `registered_models` table

## Files Created
- `POSTGRES_CONNECTION.md` - Full connection guide with examples



