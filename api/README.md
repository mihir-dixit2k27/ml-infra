# Telco Churn Prediction API

This API provides endpoints to predict customer churn using the trained MLflow model.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the API server:**
   ```bash
   python simple_api.py
   ```

3. **Access the API:**
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health
   - Prediction: http://localhost:8000/predict

## API Endpoints

### Health Check
- **GET** `/health` - Check if the model is loaded and API is healthy

### Prediction
- **POST** `/predict` - Predict customer churn
  - Input: JSON with customer features
  - Output: Prediction (0/1) and probabilities

### Model Information
- **GET** `/model/info` - Get information about the loaded model

## Example Usage

### Using curl:
```bash
curl -X POST "http://localhost:8000/predict" \
     -H "Content-Type: application/json" \
     -d '{
       "SeniorCitizen": 0,
       "tenure": 12,
       "MonthlyCharges": 70.0,
       "TotalCharges": 840.0,
       "gender": "Male",
       "Partner": "No",
       "Dependents": "No",
       "PhoneService": "Yes",
       "MultipleLines": "No",
       "InternetService": "DSL",
       "OnlineSecurity": "No",
       "OnlineBackup": "No",
       "DeviceProtection": "No",
       "TechSupport": "No",
       "StreamingTV": "No",
       "StreamingMovies": "No",
       "Contract": "Month-to-month",
       "PaperlessBilling": "Yes",
       "PaymentMethod": "Electronic check"
     }'
```

### Using Python:
```python
import requests

data = {
    "SeniorCitizen": 0,
    "tenure": 12,
    "MonthlyCharges": 70.0,
    "TotalCharges": 840.0,
    "gender": "Male",
    "Partner": "No",
    "Dependents": "No",
    "PhoneService": "Yes",
    "MultipleLines": "No",
    "InternetService": "DSL",
    "OnlineSecurity": "No",
    "OnlineBackup": "No",
    "DeviceProtection": "No",
    "TechSupport": "No",
    "StreamingTV": "No",
    "StreamingMovies": "No",
    "Contract": "Month-to-month",
    "PaperlessBilling": "Yes",
    "PaymentMethod": "Electronic check"
}

response = requests.post("http://localhost:8000/predict", json=data)
result = response.json()
print(f"Prediction: {result['prediction']}")
print(f"Churn Probability: {result['probability_churn']}")
```

## Model Loading

The API automatically loads the latest version of the registered MLflow model `telco-churn-champion`. The model is loaded from the MLflow model registry at startup.

## Troubleshooting

1. **Model not loading**: Ensure MLflow server is running on `http://127.0.0.1:5000`
2. **Prediction errors**: Check that all required features are provided in the correct format
3. **API not starting**: Verify all dependencies are installed correctly
