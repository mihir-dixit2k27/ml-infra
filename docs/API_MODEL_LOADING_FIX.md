# API Model Loading Fix - Summary

## ✅ Retry Logic Implemented

**Status:** Successfully implemented retry logic in `api/simple_api.py`

### Changes Made:
1. Added retry loop in `load_model()` startup function
   - 5 retry attempts
   - 5-second delay between retries
   - Better error logging and diagnostics

2. Improved error messages
   - Clear indication of retry attempts
   - Detailed error information
   - Common causes listed for troubleshooting

### Code Location:
- File: `api/simple_api.py`
- Function: `load_model()` (lines 60-133)
- Retry logic: Lines 73-133

---

## ⚠️ Root Cause Identified

**Issue:** Model artifacts are missing from storage location

### Problem Details:
- Model is registered in MLflow registry ✅
- Production alias exists ✅
- Model metadata exists ✅
- **Model artifact files are missing** ❌

### Evidence:
1. Model registered: `telco-churn-champion` version 1 (production alias)
2. Expected artifact path: `/mlruns-artifacts/1/models/m-4b061c85eb474040bfd0ccd78b7f98be/artifacts/`
3. Actual status: Directory doesn't exist or is empty
4. Error: `No such file or directory: '/mlruns-artifacts/1/models/m-4b061c85eb474040bfd0ccd78b7f98be/artifacts/.'`

### Investigation Results:
- Checked version 15 (current production): Artifacts directory exists but is empty
- Checked run directory: Artifacts directory exists but is empty
- Model metadata exists but actual model files (`.pkl`, `MLmodel`) are missing

---

## 🔧 Solution Options

### Option 1: Re-register Model from Training Run (Recommended)
If you have a working training run with artifacts:

```python
import mlflow
from mlflow.tracking import MlflowClient

# Set tracking URI
mlflow.set_tracking_uri("http://localhost:5001")

# Register model from a run that has artifacts
run_id = "YOUR_RUN_ID_WITH_ARTIFACTS"
model_uri = f"runs:/{run_id}/model"

# Register the model
mlflow.register_model(
    model_uri=model_uri,
    name="telco-churn-champion"
)

# Set production alias
client = MlflowClient()
client.set_registered_model_alias(
    name="telco-churn-champion",
    alias="production",
    version="NEW_VERSION"
)
```

### Option 2: Re-train and Register Model
Re-run the training pipeline to generate new artifacts:

```bash
# Activate virtual environment
source venv/bin/activate

# Run training script
python src/train.py  # or your training script

# Model should be automatically registered if training script includes registration
```

### Option 3: Copy Artifacts from Backup
If you have a backup of the model artifacts:

1. Locate the backup artifacts
2. Copy them to the expected location:
   ```bash
   # Example: Copy artifacts to run directory
   cp -r /backup/artifacts/* /path/to/mlruns/200974736127882443/6e19442fa10740339121ad7640655129/artifacts/
   ```

### Option 4: Use Lazy Loading (Temporary Workaround)
The API already supports lazy loading on first `/predict` call. However, this won't work if artifacts are missing.

---

## 📊 Current Status

### Retry Logic: ✅ Working
- Retries 5 times with 5-second delays
- Proper error handling and logging
- Graceful degradation (API starts even if model fails to load)

### Model Loading: ❌ Failing
- Root cause: Missing artifacts
- Retry logic cannot fix missing files
- Needs manual intervention to restore artifacts

### API Status: ⚠️ Partially Functional
- API starts successfully
- Health endpoint works
- `/predict` endpoint will fail until artifacts are restored

---

## 🧪 Testing the Fix

### Test Retry Logic:
```bash
# 1. Restart services
docker-compose down
docker-compose up --build -d

# 2. Watch API logs
docker-compose logs -f api

# 3. Check retry attempts in logs
# You should see:
# - "Attempt 1/5" through "Attempt 5/5"
# - Retry messages with 5-second delays
# - Final error message if artifacts are missing
```

### Test Model Loading (after artifacts are restored):
```bash
# 1. Check health endpoint
curl http://localhost:8000/health

# 2. Should return:
# {
#   "status": "healthy",
#   "model_loaded": true,
#   "model_version": "1",
#   ...
# }

# 3. Test prediction
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d @test_request.json
```

---

## 📝 Next Steps

1. **Immediate:** Identify where model artifacts are stored (backup, different location, or need to re-train)
2. **Short-term:** Restore artifacts to expected location or re-register model
3. **Long-term:** Implement artifact backup/verification in CI/CD pipeline
4. **Monitoring:** Add health checks for artifact existence

---

## 🔍 Diagnostic Commands

### Check MLflow Registry:
```bash
curl http://localhost:5001/api/2.0/mlflow/registered-models/search | python3 -m json.tool
```

### Check Model Version:
```bash
curl "http://localhost:5001/api/2.0/mlflow/model-versions/get?name=telco-churn-champion&version=1" | python3 -m json.tool
```

### Check Artifacts in Container:
```bash
docker exec mlflow_server ls -la /mlruns-artifacts/200974736127882443/models/
docker exec mlflow_server find /mlruns-artifacts -name "*.pkl" -o -name "MLmodel"
```

### Check API Logs:
```bash
docker-compose logs api | grep -i "model\|error\|retry"
```

---

## ✅ Summary

**Retry Logic:** ✅ Successfully implemented and working
**Model Artifacts:** ❌ Missing - requires manual intervention
**API Functionality:** ⚠️ Partially functional (starts but model loading fails)

The retry logic will work correctly once the model artifacts are restored to the expected location.

---

**Date:** November 8, 2025
**Status:** Retry logic complete, awaiting artifact restoration

