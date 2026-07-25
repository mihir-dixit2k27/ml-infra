# Telco Churn MLOps Pipeline

A production-style MLOps system that trains, serves, monitors, and automatically retrains a churn prediction model. Built to demonstrate how ML models are maintained in real infrastructure — not just trained once and forgotten.

---

## What this does

Predicts whether a telecom customer will churn. But more importantly, it keeps the model _accurate_ by catching data drift and triggering retraining automatically.

1. **Train** — Random Forest model tracked in MLflow, registered with a `production` alias
2. **Serve** — FastAPI loads the champion model and serves real-time predictions
3. **Log** — Every prediction is written to Postgres for downstream monitoring
4. **Monitor** — Airflow checks for data drift daily; Prometheus/Grafana expose latency at 15s resolution
5. **Retrain** — When drift is detected, a DAG retrains and promotes a new model version

---

## Architecture

```
                          ┌─────────────────────────────────────┐
                          │           User / Client              │
                          └──────────────┬──────────────────────┘
                                         │ POST /predict
                                         ▼
                          ┌─────────────────────────────────────┐
                          │        FastAPI  (port 8000)          │
                          │   loads model from MLflow registry   │
                          └──────────┬──────────────┬───────────┘
                                     │              │
                    loads model      │              │  logs prediction
                                     ▼              ▼
                   ┌─────────────────────┐   ┌──────────────────┐
                   │  MLflow Server       │   │  PostgreSQL       │
                   │  (port 5001)         │   │  prediction_logs  │
                   │  model registry +    │   │  airflow_db       │
                   │  experiment tracker  │   │  mlflow_db        │
                   └─────────────────────┘   └────────┬─────────┘
                                                       │
                              reads logs               │
                          ┌────────────────────────────┤
                          │                            │
                          ▼                            ▼
              ┌─────────────────────┐     ┌────────────────────────┐
              │  Streamlit Dashboard │     │  Airflow  (port 8080)  │
              │  (port 8501)         │     │  drift_check DAG       │
              │  live predictions,   │     │  retrain_model DAG     │
              │  drift charts        │     └────────────┬───────────┘
              └─────────────────────┘                  │
                                                        │ triggers retraining
                                                        ▼
                                           ┌─────────────────────┐
                                           │  train_and_register  │
                                           │  .py (inside Docker) │
                                           └─────────────────────┘

  Observability layer (optional, run via monitoring/docker-compose.monitoring.yml):

              ┌────────────────────┐      ┌────────────────────┐
              │  Prometheus         │─────▶│  Grafana (3000)    │
              │  scrapes every 15s  │      │  latency, errors,  │
              │  (vs CW 1-min)      │      │  predictions/min   │
              └────────────────────┘      └────────────────────┘
```

---

## Stack

| Layer | Technology |
|---|---|
| Model serving | FastAPI + Uvicorn |
| Model registry | MLflow |
| Database | PostgreSQL |
| Orchestration | Apache Airflow |
| Dashboard | Streamlit |
| Observability | Prometheus + Grafana |
| Infrastructure | Terraform (ECS Fargate, RDS, ALB, ECR, CloudTrail) |
| CI/CD | GitHub Actions |
| Container runtime | Docker Compose (local) |

---

## Running locally

Make sure Docker Desktop is running, then:

```bash
# Clone and start everything
bash start.sh
```

That's it. The script handles startup order, health checks, and DB initialization automatically.

Once up:

| Service | URL |
|---|---|
| FastAPI (prediction API) | http://localhost:8000/docs |
| MLflow (model registry) | http://localhost:5001 |
| Streamlit (dashboard) | http://localhost:8501 |
| Airflow (retraining) | http://localhost:8080 — `admin / admin` |

To also run Prometheus + Grafana:

```bash
docker compose -f docker-compose.yml -f monitoring/docker-compose.monitoring.yml up -d
# Grafana → http://localhost:3000  (admin / admin)
```

To stop everything:

```bash
docker compose down
```

---

## Testing the pipeline end-to-end

**1. Make a prediction**

Go to `http://localhost:8000/docs` → `POST /predict` → Try it out → paste:

```json
{
  "SeniorCitizen": 0, "tenure": 12, "MonthlyCharges": 65.5,
  "TotalCharges": 786.0, "gender": "Male", "Partner": "Yes",
  "Dependents": "No", "PhoneService": "Yes", "MultipleLines": "No",
  "InternetService": "Fiber optic", "OnlineSecurity": "No",
  "OnlineBackup": "No", "DeviceProtection": "No", "TechSupport": "No",
  "StreamingTV": "Yes", "StreamingMovies": "Yes",
  "Contract": "Month-to-month", "PaperlessBilling": "Yes",
  "PaymentMethod": "Electronic check"
}
```

**2. Watch it in the dashboard**

Open `http://localhost:8501` → click **Refresh Data** → the prediction appears.

**3. Simulate drift and trigger retraining**

In Airflow (`http://localhost:8080`), find `retrain_model_manual` and click ▶ to trigger it. After it completes, a new model version appears in MLflow.

---

## Deploying to AWS

Infrastructure is managed with Terraform under `infra/terraform/`:

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
# Fill in db_password and any overrides

terraform init
terraform plan
terraform apply
```

This provisions: VPC, ECS Fargate cluster, RDS Postgres, ALB, ECR repos, IAM roles, CloudTrail (IAM audit), CloudWatch alarms + dashboard.

CI/CD (`.github/workflows/ci.yml`) runs tests, validates Terraform, builds Docker images, and deploys to ECS on every push to `main`.

---

## Project structure

```
├── api/                  FastAPI prediction service
├── dags/                 Airflow DAGs (drift check + retraining)
├── dashboard/            Streamlit monitoring dashboard
├── scripts/              Training, registration, traffic simulation
├── infra/terraform/      Terraform modules (networking, ECS, RDS, IAM, monitoring)
├── monitoring/           Prometheus config, Grafana dashboard, docker-compose overlay
├── .github/workflows/    CI/CD pipeline
├── start.sh              One-command local startup
└── docker-compose.yml    Full local stack definition
```
