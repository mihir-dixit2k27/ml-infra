#!/usr/bin/env python3
"""
Script to insert drifted prediction logs directly into the database for drift testing.
This is a workaround when the model is not available for API predictions.
"""

import psycopg2
import pandas as pd
import random
from datetime import datetime
import os

# Database configuration
DB_NAME = os.getenv("POSTGRES_DB", "mlflow_db")
DB_USER = os.getenv("POSTGRES_USER", "mlflow_user")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "mlflow_password")
DB_HOST = "localhost"
DB_PORT = "5433"

# Load validation data to get realistic feature values
DATA_FILE = "data/processed/validation_v1.0.csv"

def get_db_connection():
    """Establish database connection"""
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT
    )

def insert_drifted_logs(num_logs=25):
    """Insert prediction logs with drifted MonthlyCharges values"""
    print(f"📊 Loading validation data from {DATA_FILE}...")
    df = pd.read_csv(DATA_FILE)
    
    # Remove target variable if present
    if 'Churn' in df.columns:
        df = df.drop('Churn', axis=1)
    
    # Shuffle and take sample
    df = df.sample(frac=1).reset_index(drop=True).head(num_logs)
    
    print(f"🔄 Inserting {len(df)} prediction logs with drifted MonthlyCharges (2.5x)...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    inserted_count = 0
    for idx, row in df.iterrows():
        try:
            # Apply drift: increase MonthlyCharges by 2.5x to ensure detectable drift (z-score > 3.0)
            # Baseline mean: 64.99, std: 30.11
            # Target: mean > 155 to get z-score > 3.0
            monthly_charges = float(row['MonthlyCharges']) * 2.5
            
            # Prepare data (all lowercase to match DB schema)
            log_data = (
                "1",  # model_version
                0,    # prediction (placeholder)
                str(row.get('gender', 'Unknown')).lower(),
                int(row.get('SeniorCitizen', 0)),
                str(row.get('Partner', 'Unknown')).lower(),
                str(row.get('Dependents', 'Unknown')).lower(),
                int(row.get('tenure', 0)),
                str(row.get('PhoneService', 'Unknown')).lower(),
                str(row.get('MultipleLines', 'Unknown')).lower(),
                str(row.get('InternetService', 'Unknown')).lower(),
                str(row.get('OnlineSecurity', 'Unknown')).lower(),
                str(row.get('OnlineBackup', 'Unknown')).lower(),
                str(row.get('DeviceProtection', 'Unknown')).lower(),
                str(row.get('TechSupport', 'Unknown')).lower(),
                str(row.get('StreamingTV', 'Unknown')).lower(),
                str(row.get('StreamingMovies', 'Unknown')).lower(),
                str(row.get('Contract', 'Unknown')).lower(),
                str(row.get('PaperlessBilling', 'Unknown')).lower(),
                str(row.get('PaymentMethod', 'Unknown')).lower(),
                float(monthly_charges),  # drifted value
                float(row.get('TotalCharges', 0.0))
            )
            
            query = """
            INSERT INTO prediction_logs (
                model_version, prediction, gender, seniorcitizen, partner, dependents,
                tenure, phoneservice, multiplelines, internetservice, onlinesecurity, onlinebackup,
                deviceprotection, techsupport, streamingtv, streamingmovies, contract, paperlessbilling,
                paymentmethod, monthlycharges, totalcharges
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(query, log_data)
            inserted_count += 1
            
            original_value = float(row['MonthlyCharges'])
            print(f"  ✅ Log {idx + 1}/{len(df)}: MonthlyCharges {original_value:.2f} -> {monthly_charges:.2f} (2.5x)")
            
        except Exception as e:
            print(f"  ❌ Error inserting log {idx + 1}: {e}")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"\n✅ Successfully inserted {inserted_count}/{len(df)} prediction logs with drifted data")
    return inserted_count

if __name__ == "__main__":
    print("=" * 60)
    print("Inserting Drifted Prediction Logs for Drift Testing")
    print("=" * 60)
    print()
    
    try:
        inserted = insert_drifted_logs(num_logs=25)
        print(f"\n🎯 Ready for drift detection! {inserted} logs with drifted MonthlyCharges inserted.")
        print("   Run: python src/drift_monitor.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

