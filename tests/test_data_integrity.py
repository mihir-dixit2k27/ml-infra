import pandas as pd
import pytest
import os

# Define file paths
TRAIN_DATA_PATH = "data/processed/train_v1.0.csv"
VAL_DATA_PATH = "data/processed/validation_v1.0.csv"

def test_data_files_exist():
    """Tests that the processed data files exist."""
    assert os.path.exists(TRAIN_DATA_PATH), f"File not found: {TRAIN_DATA_PATH}"
    assert os.path.exists(VAL_DATA_PATH), f"File not found: {VAL_DATA_PATH}"

def test_train_data_no_nulls():
    """Tests that the training data has no null values."""
    df = pd.read_csv(TRAIN_DATA_PATH)
    assert df.isnull().sum().sum() == 0, "Null values found in training data."

def test_validation_data_no_nulls():
    """Tests that the validation data has no null values."""
    df = pd.read_csv(VAL_DATA_PATH)
    assert df.isnull().sum().sum() == 0, "Null values found in validation data."

def test_data_target_variable_exists():
    """Tests that the 'Churn' column exists in both datasets."""
    train_df = pd.read_csv(TRAIN_DATA_PATH)
    val_df = pd.read_csv(VAL_DATA_PATH)
    assert 'Churn' in train_df.columns, "Target 'Churn' not in training data."
    assert 'Churn' in val_df.columns, "Target 'Churn' not in validation data."