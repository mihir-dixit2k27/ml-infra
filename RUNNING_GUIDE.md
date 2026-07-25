# MLOps Churn Project — Step-by-Step Running Guide

A complete guide to bring up every component of the stack and verify it is healthy before moving to the next step.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     Docker Network (mlops-net)           │
│                                                          │
│  postgres:5432  ──►  mlflow-ui:5000  ──►  api:8000       │
│       │                                    │             │
│       └──────────────────────────────►  dashboard:8501   │
│                                                          │
│  airflow-webserver:8080                                  │
│  airflow-scheduler (background)                          │
└─────────────────────────────────────────────────────────┘
```

**Service → Host Port Mapping**

| Service            | Host URL                        | Purpose                        |
|--------------------|---------------------------------|--------------------------------|
| PostgreSQL         | `localhost:5433`                | Metadata DB + prediction logs  |
| MLflow UI          | `http://localhost:5001`         | Model registry & experiment UI |
| FastAPI            | `http://localhost:8000`         | Churn prediction endpoint      |
| Streamlit Dashboard| `http://localhost:8501`         | MLOps monitoring dashboard     |
| Airflow UI         | `http://localhost:8080`         | DAG management                 |

---

## Prerequisites

Before you begin, make sure the following are installed:

```
docker --version        # >= 24.x
docker compose version  # >= 2.x
python --version        # >= 3.10 (for running scripts locally)
```

Also verify Docker Desktop is **running** (the whale icon in the taskbar).

---

## Step 1 — Set Up Environment Variables

Copy the example env file and set your values:

```powershell
Copy-Item env.example .env
```

The defaults work out of the box for local development. Your `.env` should look like:

```env
POSTGRES_USER=mlflow_user
POSTGRES_PASSWORD=mlflow_password
POSTGRES_DB=mlflow_db
POSTGRES_PORT=5432

MLFLOW_TRACKING_URI=http://127.0.0.1:5001
MODEL_NAME=telco-churn-champion
MODEL_ALIAS=production
```

> ⚠️ **Never commit `.env` to Git.** It is already listed in `.gitignore`.

---

## Step 2 — Start Core Infrastructure (Postgres + MLflow)

Start only the database and MLflow first. This is the foundation everything else depends on.

```powershell
docker compose up -d postgres mlflow-ui
```

### ✅ Verification — PostgreSQL

```powershell
docker compose ps postgres
```

Expected output: `Status: healthy`

Also run a direct health check:

```powershell
docker exec postgres_db pg_isready -U mlflow_user -d mlflow_db
```

Expected: `localhost:5432 - accepting connections`

### ✅ Verification — MLflow

Open your browser and navigate to:

```
http://localhost:5001
```

You should see the **MLflow Experiments** UI with no errors.

**Wait ~30 seconds** after `docker compose up` before checking — MLflow waits for Postgres to be fully healthy first.

---

## Step 3 — Train and Register the Model

This is a one-time step (or repeat after wiping MLflow data). Run the training script on your host machine, pointing it at the containerised MLflow server.

```powershell
$env:MLFLOW_TRACKING_URI = "http://localhost:5001"
python scripts/train_and_register.py
```

### ✅ Verification — Model Registered

At the end of the script you should see:

```
✅ Model successfully registered!
Model: telco-churn-champion@production
Version: 1
```

Then confirm in the MLflow UI:

1. Go to `http://localhost:5001`
2. Click **Models** in the left sidebar
3. You should see `telco-churn-champion` listed
4. Click it → verify the `production` alias is set on version `1`

---

## Step 4 — Start the FastAPI Prediction Service

```powershell
docker compose up -d api
```

Wait ~20 seconds for the container to start and load the model from MLflow.

### ✅ Verification — API Health Check

```powershell
Invoke-RestMethod -Uri http://localhost:8000/health
```

Expected response:

```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_version": "1",
  "db_connected": true
}
```

**If `model_loaded` is `false`:** Check logs for model loading errors:

```powershell
docker compose logs api --tail 50
```

### ✅ Verification — Make a Test Prediction

```powershell
$body = @{
    SeniorCitizen    = 0
    tenure           = 12
    MonthlyCharges   = 65.5
    TotalCharges     = 786.0
    gender           = "Male"
    Partner          = "Yes"
    Dependents       = "No"
    PhoneService     = "Yes"
    MultipleLines    = "No"
    InternetService  = "Fiber optic"
    OnlineSecurity   = "No"
    OnlineBackup     = "No"
    DeviceProtection = "No"
    TechSupport      = "No"
    StreamingTV      = "Yes"
    StreamingMovies  = "Yes"
    Contract         = "Month-to-month"
    PaperlessBilling = "Yes"
    PaymentMethod    = "Electronic check"
} | ConvertTo-Json

Invoke-RestMethod -Method POST -Uri http://localhost:8000/predict `
    -ContentType "application/json" -Body $body
```

Expected response:

```json
{
  "prediction": 1,
  "probability_no_churn": 0.32,
  "probability_churn": 0.68,
  "model_version": "1"
}
```

You can also use the **interactive Swagger UI** at `http://localhost:8000/docs`.

---

## Step 5 — Start the Streamlit Dashboard

```powershell
docker compose up -d dashboard
```

### ✅ Verification — Dashboard Loads

Open: `http://localhost:8501`

You should see the MLOps monitoring dashboard. After Step 4's test prediction, you should see at least 1 row in the prediction logs section.

---

## Step 6 — Start Airflow (Retraining Pipeline)

Airflow requires its database to be initialised before the webserver and scheduler start. Docker Compose handles this via `airflow-init`.

```powershell
docker compose up -d airflow-init
```

Wait for it to complete (it exits on success):

```powershell
docker compose ps airflow-init
# Should show: Status: exited (0)
```

Then start the webserver and scheduler:

```powershell
docker compose up -d airflow-webserver airflow-scheduler
```

### ✅ Verification — Airflow UI

Open: `http://localhost:8080`

Login credentials:
- **Username:** `admin`
- **Password:** `admin`

You should see the DAG list. Look for `retrain_model_manual` and `data_drift_monitor` DAGs.

### ✅ Verification — DAGs are loaded

In the Airflow UI:
1. Click **DAGs** in the top menu
2. Confirm `retrain_model_manual` appears in the list
3. Toggle it **ON** (unpause it) if you want it active

---

## Step 7 — Simulate Traffic (Optional but Recommended)

Generate realistic prediction traffic to populate the dashboard metrics:

```powershell
$env:MLFLOW_TRACKING_URI = "http://localhost:5001"
python scripts/simulate_traffic.py
```

This sends a batch of predictions to the API and logs them to the database. After running it, refresh `http://localhost:8501` to see updated metrics.

---

## Step 8 — Full Stack Verification

Once all services are up, run this full status check:

```powershell
docker compose ps
```

All services should show `running` or `healthy`. Expected output:

```
NAME                   STATUS
postgres_db            running (healthy)
mlflow_server          running
fast_api               running
mlops_dashboard        running
airflow-webserver      running
airflow-scheduler      running
```

### Quick health check all at once:

```powershell
# FastAPI
Invoke-RestMethod http://localhost:8000/health

# FastAPI DB check
Invoke-RestMethod http://localhost:8000/health/db

# MLflow (should return HTML page)
Invoke-WebRequest http://localhost:5001 -UseBasicParsing | Select-Object StatusCode
```

---

## Stopping the Stack

To stop all services (preserves data):

```powershell
docker compose down
```

To stop and **wipe all data** (including the Postgres volume — you'll need to retrain):

```powershell
docker compose down -v
```

---

## Troubleshooting

### API says `model_loaded: false`
1. Check MLflow has the model: `http://localhost:5001` → Models tab
2. Check API logs: `docker compose logs api --tail 50`
3. If model is missing, re-run Step 3

### Airflow DAGs not showing
1. Check the DAG files are in `./dags/` folder
2. Check scheduler logs: `docker compose logs airflow-scheduler --tail 30`
3. DAGs can take up to 60 seconds to appear after a scheduler restart

### Port already in use
Find and kill the conflicting process:
```powershell
# Example: port 5001 is busy
netstat -ano | findstr :5001
# Then kill the PID shown
taskkill /PID <pid> /F
```

### Database connection errors
1. Ensure postgres is `healthy`: `docker compose ps postgres`
2. Check credentials match between `.env` and `docker-compose.yml`

---

## Service Startup Order (Dependency Chain)

```
postgres (healthy)
    │
    ├──► mlflow-ui (started)
    │        │
    │        └──► api ──► dashboard
    │
    └──► airflow-init (completed)
             │
             ├──► airflow-webserver
             └──► airflow-scheduler
```

Always bring up services in this order if starting manually:
1. `postgres` → 2. `mlflow-ui` → 3. `api` + `dashboard` → 4. `airflow-*`
