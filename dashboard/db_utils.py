import os
from typing import Optional

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


@st.cache_resource
def get_db_engine() -> Engine:
    """Creates and caches the SQLAlchemy engine."""
    user = os.getenv("POSTGRES_USER", "mlflow_user")
    password = os.getenv("POSTGRES_PASSWORD", "mlflow_password")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "mlflow_db")

    db_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    return create_engine(db_url)


def load_data(query: str) -> pd.DataFrame:
    """Executes a SQL query and returns a Pandas DataFrame."""
    engine = get_db_engine()
    try:
        with engine.connect() as conn:
            return pd.read_sql(text(query), conn)
    except Exception as e:
        st.error(f"Database Error: {e}")
        return pd.DataFrame()


