# MLOps Setup Summary

## Issues Resolved

### 1. Docker Compose Error (`ContainerConfig`)
- **Problem**: Docker Compose v1.29.2 failed with `KeyError: 'ContainerConfig'`
- **Solution**: Cleared corrupted container state with `docker-compose down` and recreated services

### 2. MLflow Host Header Rejection
- **Problem**: API couldn't connect to MLflow - "Invalid Host header - possible DNS rebinding attack"
- **Solution**: Updated `docker-compose.yml` allowed-hosts to include `mlflow-ui:5000` and wildcard `*`

### 3. Model Not Found
- **Problem**: No models registered in MLflow Model Registry
- **Solution**: Created `train_and_register.py` script, trained model, registered as `telco-churn-champion@production`

### 4. Model Loading with Aliases
- **Problem**: API failed when production alias didn't exist
- **Solution**: Enhanced `model_loader.py` to fallback from alias → latest version → graceful error

### 5. PyFuncModel predict_proba
- **Problem**: `predict_proba()` not available on MLflow's PyFuncModel wrapper
- **Solution**: Use `model.get_raw_model()` to access underlying sklearn pipeline

## Current System State

### Services Running
- **PostgreSQL**: Port 5433 (healthy)
- **MLflow Server**: Port 5001 (http://localhost:5001)
- **FastAPI**: Port 8000 (http://localhost:8000)

### MLflow Setup
- **Tracking URI**: `http://mlflow-ui:5000` (internal Docker network)
- **Backend Store**: PostgreSQL
- **Artifact Root**: `file:///mlruns-artifacts` (mounted from `./mlruns`)
- **Experiment**: `Telco_Churn_Champion`

### Model Registry
- **Model Name**: `telco-churn-champion`
- **Registered Version**: 1
- **Production Alias**: Set to version 1
- **Status**: READY

### API Status
- **Model Loaded**: ✅ Yes
- **Health Endpoint**: `/health` - returns model status
- **Predict Endpoint**: `/predict` - working with probabilities
- **Model Info**: `/model/info` - available

## Key Files Modified

### `docker-compose.yml`
- Added `mlflow-ui:5000,0.0.0.0,*` to `--allowed-hosts` for MLflow server

### `api/model_loader.py`
- Enhanced `load_latest_model()` with alias → version fallback logic
- Fixed `predict_proba()` to use `get_raw_model()` for PyFuncModel compatibility

### Created: `train_and_register.py`
- Minimal training script to train and register models
- Handles model registration with production alias
- Can be run in Docker container or locally

## Key Configuration

```env
# Environment Variables (docker-compose.yml)
MLFLOW_TRACKING_URI=http://mlflow-ui:5000
MODEL_NAME=telco-churn-champion
MODEL_ALIAS=production
```

## Verified Working Endpoints

```bash
# Health Check
GET http://localhost:8000/health
# Returns: {"status": "healthy", "model_loaded": true, "model_version": "unknown"}

# Prediction
POST http://localhost:8000/predict
Content-Type: application/json
# Returns predictions with probabilities
```

## Model Details
- **Type**: RandomForestClassifier (scikit-learn Pipeline)
- **Metrics**: Accuracy: 0.793, F1: 0.571, AUC: 0.830
- **Features**: 19 features (4 numeric, 15 categorical)
- **Target**: Binary churn prediction (0=No, 1=Yes)

## Next Steps Planning

### Potential Improvements
1. **Model Version Tracking**: Fix `model_version` showing "unknown" in health check
2. **Monitoring**: Add prediction logging to MLflow
3. **Model Updates**: Set up automated retraining pipeline
4. **API Improvements**: Add batch prediction endpoint
5. **Testing**: Add unit/integration tests for model loading
6. **CI/CD**: Automate model training and deployment
7. **Model Staging**: Implement staging → production promotion workflow
8. **A/B Testing**: Support multiple model versions for comparison

### Operational Considerations
- Model artifacts stored in Docker volume (`./mlruns`)
- Consider artifact storage backup strategy
- Monitor PostgreSQL database growth
- Set up MLflow experiment tracking cleanup policies

## Training a New Model

To train and register a new model version:
```bash
# Option 1: Run in Docker container
docker exec -e MLFLOW_TRACKING_URI=http://mlflow-ui:5000 fast_api python3 /app/train_and_register.py

# Option 2: Run locally (if MLflow installed)
MLFLOW_TRACKING_URI=http://localhost:5001 python train_and_register.py
```

The script will:
1. Train a new RandomForest model
2. Log metrics to MLflow
3. Register model in Model Registry
4. Set production alias to new version




