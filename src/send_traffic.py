import requests
import time
import random
import argparse
import sys

# CONFIGURATION
API_URL = "http://localhost:8000/predict"
DELAY_SECONDS = 0.5 

def get_normal_data():
    """
    Generates 'Normal' Telco Churn Data (matches training distribution)
    """
    return {
        "gender": random.choice(["Male", "Female"]),
        "SeniorCitizen": 0,
        "Partner": random.choice(["Yes", "No"]),
        "Dependents": random.choice(["Yes", "No"]),
        "tenure": random.randint(1, 72),
        "PhoneService": "Yes",
        "MultipleLines": random.choice(["Yes", "No", "No phone service"]),
        "InternetService": random.choice(["DSL", "Fiber optic", "No"]),
        "OnlineSecurity": random.choice(["Yes", "No"]),
        "OnlineBackup": random.choice(["Yes", "No"]),
        "DeviceProtection": random.choice(["Yes", "No"]),
        "TechSupport": random.choice(["Yes", "No"]),
        "StreamingTV": random.choice(["Yes", "No"]),
        "StreamingMovies": random.choice(["Yes", "No"]),
        "Contract": random.choice(["Month-to-month", "One year", "Two year"]),
        "PaperlessBilling": random.choice(["Yes", "No"]),
        "PaymentMethod": "Electronic check",
        "MonthlyCharges": random.uniform(20.0, 100.0),
        "TotalCharges": random.uniform(20.0, 5000.0)
    }

def get_drifted_data():
    """
    Generates 'Drifted' Data to trigger the alarm.
    - Tenure is unusually high
    - Monthly Charges are doubled
    - All customers are Senior Citizens (skewed demographic)
    """
    return {
        "gender": "Female", # Skewed to only one gender
        "SeniorCitizen": 1, # DRIFT: Everyone is a senior citizen now
        "Partner": "No",
        "Dependents": "No",
        "tenure": random.randint(80, 100), # DRIFT: Impossible tenure (normal max is usually 72)
        "PhoneService": "Yes",
        "MultipleLines": "Yes",
        "InternetService": "Fiber optic",
        "OnlineSecurity": "No",
        "OnlineBackup": "No",
        "DeviceProtection": "No",
        "TechSupport": "No",
        "StreamingTV": "Yes",
        "StreamingMovies": "Yes",
        "Contract": "Month-to-month",
        "PaperlessBilling": "Yes",
        "PaymentMethod": "Electronic check",
        "MonthlyCharges": random.uniform(150.0, 300.0), # DRIFT: Way too expensive
        "TotalCharges": random.uniform(8000.0, 10000.0)
    }

def send_request(data):
    try:
        response = requests.post(API_URL, json=data)
        if response.status_code == 200:
            # Success!
            print(f"[SUCCESS] Prediction: {response.json()}")
        else:
            # If it fails, print the short error message
            print(f"[ERROR] Status: {response.status_code} | {response.text[:100]}...")
    except requests.exceptions.ConnectionError:
        print(f"[CRITICAL] Could not connect to {API_URL}. Is Docker running?")
        sys.exit(1)

def main(mode):
    print(f"--- Starting Traffic Simulation: {mode.upper()} MODE ---")
    print(f"Targeting: {API_URL}")
    print("Press CTRL+C to stop.\n")

    try:
        while True:
            if mode == "normal":
                data = get_normal_data()
            elif mode == "drift":
                data = get_drifted_data()
            
            # Print a summary instead of the whole JSON to keep terminal clean
            print(f"Sending Customer: Tenure={data['tenure']}, Charges={data['MonthlyCharges']:.2f}")
            send_request(data)
            time.sleep(DELAY_SECONDS)
            
    except KeyboardInterrupt:
        print("\nStopping traffic simulation.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["normal", "drift"], default="normal")
    args = parser.parse_args()
    main(args.mode)
    