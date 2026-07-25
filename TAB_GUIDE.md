# 🗺️ Browser Tab Navigation Guide

When you run `bash start.sh`, four browser tabs open automatically.
Here's what each one does and how to use it.

---

## Tab 1 — MLflow UI (`localhost:5001`)
**What it is:** Model registry and experiment tracker.

**What to do here:**
- Click **"Models"** in the left sidebar → see `telco-churn-champion`
- Click the model → see all registered versions
- See which version has the `production` alias (this is what the API loads)
- Click **"Experiments"** → see every training run with its accuracy, F1, AUC metrics

**You'll use this to:** Check model health, compare training runs, verify a new model was registered after retraining.

---

## Tab 2 — FastAPI Docs (`localhost:8000/docs`)
**What it is:** Auto-generated interactive API documentation (Swagger UI).

**What to do here — make a live prediction:**
1. Scroll to **`POST /predict`** → click it → click **"Try it out"**
2. Replace the request body with this sample customer:
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
3. Click **"Execute"** → see the churn probability in the response

**Other useful endpoints:**
- `GET /health` → Is the model loaded? Is DB connected?
- `GET /model/info` → Which model version is active?

---

## Tab 3 — Streamlit Dashboard (`localhost:8501`)
**What it is:** Real-time MLOps monitoring dashboard.

**What to do here:**
- **Top row:** Total predictions made, churn rate %, current model version
- **Prediction logs table:** Every prediction the API made (once you hit `/predict`)
- **Churn distribution chart:** Are more customers churning over time?
- Click **"Refresh Data"** button to pull the latest predictions from the DB

**To populate it with data:** After the dashboard loads, go to Tab 2 and make a few predictions — they'll appear here immediately after clicking Refresh.

Or run the traffic simulator in WSL:
```bash
docker compose run --rm \
  -e MLFLOW_TRACKING_URI=http://mlflow-ui:5000 \
  --entrypoint python api -c "
import requests, random
for _ in range(20):
    requests.post('http://fast_api:8000/predict', json={
        'SeniorCitizen': random.randint(0,1), 'tenure': random.randint(1,72),
        'MonthlyCharges': round(random.uniform(20,100),2),
        'TotalCharges': round(random.uniform(100,8000),2),
        'gender': random.choice(['Male','Female']),
        'Partner': random.choice(['Yes','No']),
        'Dependents': random.choice(['Yes','No']),
        'PhoneService': 'Yes', 'MultipleLines': 'No',
        'InternetService': random.choice(['Fiber optic','DSL','No']),
        'OnlineSecurity': 'No', 'OnlineBackup': 'No',
        'DeviceProtection': 'No', 'TechSupport': 'No',
        'StreamingTV': 'No', 'StreamingMovies': 'No',
        'Contract': random.choice(['Month-to-month','One year','Two year']),
        'PaperlessBilling': 'Yes', 'PaymentMethod': 'Electronic check'
    })
print('Done — 20 predictions sent')
"
```

---

## Tab 4 — Airflow UI (`localhost:8080`)
**What it is:** Workflow orchestration for automated model retraining.

**Login:** Username `admin` / Password `admin`

**What to do here:**
- Click **"DAGs"** in the top menu
- Find `retrain_model_manual` → toggle the switch to **unpause** it
- Click the DAG name → click the **▶ Play button** → "Trigger DAG" to manually trigger a retraining
- Watch the task graph turn green as each step completes
- After retraining, go back to MLflow (Tab 1) to see the new model version

---

## Summary

| Tab | URL | Purpose | You use it when... |
|-----|-----|---------|-------------------|
| MLflow | `localhost:5001` | Model registry | Verifying model exists / comparing runs |
| FastAPI | `localhost:8000/docs` | Make predictions | Testing the API directly |
| Dashboard | `localhost:8501` | Monitor health | Checking prediction volume & accuracy |
| Airflow | `localhost:8080` | Trigger retraining | Model drifts / needs fresh training |
