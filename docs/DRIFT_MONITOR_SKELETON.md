# Drift Monitor Skeleton - Implementation Summary

## ✅ Implementation Complete

### What Was Built

**File**: `src/drift_monitor.py`

A complete skeleton for drift detection that:
1. ✅ Connects to PostgreSQL database (with retry logic)
2. ✅ Fetches prediction logs from `prediction_logs` table
3. ✅ Loads baseline training statistics
4. ✅ Compares production data with baseline
5. ✅ Provides detailed output with statistics

## Key Features

### 1. Resilient DB Connection
- **Two methods**: SQLAlchemy (primary) and psycopg2 (alternative)
- **Retry logic**: 5 attempts with 3-second delays
- **Connection to**: `localhost:5433` (host port mapped from Docker)
- **Database**: `mlflow_db`

### 2. Data Fetching
- **Function**: `fetch_recent_predictions_sqlalchemy()` / `fetch_recent_predictions_psycopg2()`
- **Returns**: Pandas DataFrame with 19 features
- **Limit**: 1000 predictions (configurable)
- **Ordering**: Most recent first

### 3. Baseline Stats Loading
- **Source**: `data/processed/train_stats_v1.0.json`
- **Function**: `load_baseline_stats()`
- **Validation**: Checks for expected keys and structure
- **Features**: SeniorCitizen, tenure, MonthlyCharges, TotalCharges

### 4. Enhanced Output
- Baseline vs Production comparison
- Percentage differences calculated
- Timestamp information
- Data summary statistics

## Test Results

```bash
$ python src/drift_monitor.py

============================================================
--- Running Drift Monitor Script ---
============================================================
--- Baseline stats loaded successfully ---
--- SQLAlchemy engine created successfully ---
--- Fetched 2 recent predictions ---

Recent Predictions DataFrame (sample):
   gender  seniorcitizen  ... monthlycharges totalcharges
0  Female              1  ...           90.0       2160.0
1    Male              0  ...           70.0        840.0

--- Quick Comparison (Production vs Baseline) ---
Seniorcitizen mean - Baseline: 0.1618, Production: 0.5000 (Δ: 209.1%)
Tenure mean - Baseline: 32.5623, Production: 18.0000 (Δ: 44.7%)
Monthlycharges mean - Baseline: 64.9993, Production: 80.0000 (Δ: 23.1%)
Totalcharges mean - Baseline: 2301.8395, Production: 1500.0000 (Δ: 34.8%)
```

## Usage

### Run the Script
```bash
# Activate virtual environment
source venv/bin/activate

# Run drift monitor
python src/drift_monitor.py
```

### Prerequisites
- Docker stack running (`docker-compose up -d`)
- PostgreSQL accessible on port 5433
- At least one prediction logged in `prediction_logs` table
- Baseline stats file exists: `data/processed/train_stats_v1.0.json`

## Functions Available

1. **`get_db_connection(retries=5, delay=3)`** - Direct PostgreSQL connection
2. **`get_sqlalchemy_engine()`** - SQLAlchemy engine for pandas
3. **`fetch_recent_predictions_sqlalchemy(engine, limit=1000)`** - Fetch via SQLAlchemy
4. **`fetch_recent_predictions_psycopg2(conn, limit=1000)`** - Fetch via psycopg2
5. **`load_baseline_stats(path=STATS_FILE_PATH)`** - Load baseline statistics

## Next Steps (Future Enhancements)

1. **Statistical Tests**: Add Kolmogorov-Smirnov, chi-square tests
2. **Drift Thresholds**: Define acceptable drift percentages
3. **Alerting**: Email/Slack notifications on drift detection
4. **Visualizations**: Generate plots comparing distributions
5. **Scheduled Runs**: Cron job for periodic monitoring
6. **Categorical Drift**: Monitor categorical feature distributions
7. **Model Performance Drift**: Track prediction accuracy over time

## Configuration

All configuration uses environment variables with sensible defaults:
- `POSTGRES_DB` (default: `mlflow_db`)
- `POSTGRES_USER` (default: `mlflow_user`)
- `POSTGRES_PASSWORD` (default: `mlflow_password`)
- `POSTGRES_HOST` (default: `localhost`)
- `POSTGRES_PORT` (default: `5433`)

## Error Handling

- ✅ File not found errors (baseline stats)
- ✅ Database connection failures (with retries)
- ✅ Empty result sets
- ✅ JSON decode errors
- ✅ Connection cleanup (finally blocks)




