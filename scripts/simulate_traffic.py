#!/usr/bin/env python3
"""
Simulate users sending data to the Telco Churn Prediction API

This script loads validation data and sends it to the API endpoint
to simulate real user traffic and test the API performance.
"""

import requests
import pandas as pd
import time
import json
import random
from pathlib import Path

# Configuration
API_ENDPOINT = "http://localhost:8000/predict"
DATA_FILE = "data/processed/validation_v1.0.csv"
SLEEP_INTERVAL = 1  # seconds between requests
MAX_RETRIES = 3
MAX_REQUESTS = 25  # Limit number of requests for drift testing (set to None for all)


def load_validation_data():
    """Load the validation dataset"""
    try:
        df = pd.read_csv(DATA_FILE)
        print(f"✅ Loaded {len(df)} records from {DATA_FILE}")
        return df
    except FileNotFoundError:
        print(f"❌ Error: Data file not found at {DATA_FILE}")
        print("Make sure the validation data file exists in the correct location.")
        exit(1)
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        exit(1)


def send_prediction_request(row):
    """Send a single prediction request to the API"""
    # Convert row to dictionary and remove target variable
    data = row.to_dict()
    if "Churn" in data:
        del data["Churn"]  # Remove target variable

    # --- Simulate drift: increase MonthlyCharges by 50% ---
    # Note: For detectable drift (z-score > 3.0), you may need higher drift (2.5x)
    # This 1.5x drift simulates moderate data shift that may not always trigger alerts
    try:
        if "MonthlyCharges" in data and data["MonthlyCharges"] is not None:
            original_value = float(data["MonthlyCharges"])
            drift_factor = 5.0  # change the values for drift detection confirmed values
            data["MonthlyCharges"] = original_value * drift_factor
            print(
                f"  🔄 Simulating drift: MonthlyCharges {original_value:.2f} -> {data['MonthlyCharges']:.2f} ({drift_factor}x)"
            )
    except Exception as e:
        print(f"  ⚠️  Warning: Could not apply drift to MonthlyCharges: {e}")

    try:
        response = requests.post(
            API_ENDPOINT,
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        if response.status_code == 200:
            result = response.json()
            print(
                f"✅ Prediction: {result['prediction']}, Churn Prob: {result['probability_churn']:.3f}"
            )
            return True
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ Connection error - API might not be running")
        return False
    except requests.exceptions.Timeout:
        print("❌ Request timeout - API might be slow")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def check_api_health():
    """Check if the API is healthy before starting simulation"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(
                f"✅ API is healthy - Model loaded: {health_data.get('model_loaded', False)}"
            )
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("Make sure the API is running with: docker-compose up -d")
        return False


def simulate_traffic():
    """Main simulation loop"""
    print("🚀 Starting API traffic simulation...")
    print(f"📡 API Endpoint: {API_ENDPOINT}")
    print(f"📊 Data File: {DATA_FILE}")
    print(f"⏱️  Sleep Interval: {SLEEP_INTERVAL}s")
    print("-" * 50)

    # Check API health first
    if not check_api_health():
        print("❌ API is not healthy. Exiting simulation.")
        return

    # Load data
    df = load_validation_data()

    # Shuffle data for random simulation
    df = df.sample(frac=1).reset_index(drop=True)
    print(f"🎲 Data shuffled for random simulation")

    # Limit number of requests if MAX_REQUESTS is set
    if MAX_REQUESTS is not None and MAX_REQUESTS < len(df):
        df = df.head(MAX_REQUESTS)
        print(f"📌 Limiting to {MAX_REQUESTS} requests for drift testing")

    successful_requests = 0
    total_requests = 0
    start_time = time.time()

    print(f"\n📤 Starting to send {len(df)} requests...")
    print("-" * 50)

    for idx, row in df.iterrows():
        print(f"\n📊 Request {idx + 1}/{len(df)}")

        # Retry logic
        request_successful = False
        for attempt in range(MAX_RETRIES):
            if send_prediction_request(row):
                successful_requests += 1
                request_successful = True
                break
            else:
                if attempt < MAX_RETRIES - 1:
                    print(
                        f"🔄 Retrying in 2 seconds... (attempt {attempt + 2}/{MAX_RETRIES})"
                    )
                    time.sleep(2)

        total_requests += 1

        # Sleep between requests (except for the last one)
        if idx < len(df) - 1:
            time.sleep(SLEEP_INTERVAL)

    # Calculate simulation statistics
    end_time = time.time()
    total_time = end_time - start_time
    avg_time_per_request = total_time / total_requests if total_requests > 0 else 0

    # Summary
    print("\n" + "=" * 50)
    print("📈 SIMULATION COMPLETE!")
    print("=" * 50)
    print(f"✅ Successful requests: {successful_requests}/{total_requests}")
    print(f"📊 Success rate: {successful_requests/total_requests*100:.1f}%")
    print(f"⏱️  Total time: {total_time:.2f} seconds")
    print(f"⚡ Average time per request: {avg_time_per_request:.2f} seconds")
    print(f"🔄 Requests per second: {total_requests/total_time:.2f}")


def main():
    """Main entry point"""
    print("🎯 Telco Churn API Traffic Simulator")
    print("=" * 50)

    # Check if data file exists
    if not Path(DATA_FILE).exists():
        print(f"❌ Data file not found: {DATA_FILE}")
        print("Please make sure the validation data file exists.")
        return

    try:
        simulate_traffic()
    except KeyboardInterrupt:
        print("\n\n⏹️  Simulation interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
