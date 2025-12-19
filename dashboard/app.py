import pandas as pd
import streamlit as st
import plotly.express as px
from db_utils import load_data
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
import numpy as np
from mlflow_utils import get_model_performance, get_latest_model_version
DB_URI = "postgresql://mlflow_user:mlflow_password@postgres_db:5432/mlflow_db"


# Define your model name exactly as it appears in MLflow
MODEL_NAME = "telco-churn-champion"
def get_drift_live_data():
    """Fetches specifically numeric fields for drift analysis."""
    try:
        engine = create_engine(DB_URI)
        # FIX: Use lowercase names to match the database table
        query = """
        SELECT 
            tenure,
            monthlycharges as "MonthlyCharges",
            totalcharges as "TotalCharges"
        FROM prediction_logs
        LIMIT 500
        """
        return pd.read_sql(query, engine)
    except Exception as e:
        st.error(f"Error fetching live data for drift: {e}")
        return pd.DataFrame()
   
    

def get_drift_reference_data():
    """Generates 'Normal' baseline data (Simulated Training Data)."""
    np.random.seed(42)
    return pd.DataFrame({
        "tenure": np.random.randint(1, 72, 500),
        "MonthlyCharges": np.random.uniform(20, 100, 500),
        "TotalCharges": np.random.uniform(20, 5000, 500)
    })

# --- THE MAIN DRIFT TAB FUNCTION ---
def render_drift_monitoring_tabv2():
    st.header("📉 Data Drift Analysis (Training vs. Live)")
    
    live_df = get_drift_live_data()
    ref_df = get_drift_reference_data()

    if not live_df.empty:
        # Allow user to choose which feature to inspect
        feature = st.selectbox("Select Feature to Analyze", ["MonthlyCharges", "tenure", "TotalCharges"])
        
        # Create the Comparison Histogram
        fig = go.Figure()
        
        # 1. Plot Baseline (Blue)
        fig.add_trace(go.Histogram(
            x=ref_df[feature],
            name='Training Data (Baseline)',
            opacity=0.75,
            marker_color='#3366CC', # Blue
            histnorm='probability density'
        ))
        
        # 2. Plot Live Data (Red)
        fig.add_trace(go.Histogram(
            x=live_df[feature],
            name='Live Traffic (Recent)',
            opacity=0.75,
            marker_color='#DC3912', # Red
            histnorm='probability density'
        ))

        # Formatting
        fig.update_layout(
            barmode='overlay',
            title=f"Distribution Shift: {feature}",
            xaxis_title=f"{feature} Value",
            yaxis_title="Density",
            legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Auto-Insight
        live_mean = live_df[feature].mean()
        ref_mean = ref_df[feature].mean()
        delta = ((live_mean - ref_mean) / ref_mean) * 100
        
        if abs(delta) > 20:
             st.error(f"⚠️ DRIFT DETECTED! Live {feature} average ({live_mean:.2f}) has shifted by {delta:+.1f}% from training.")
        else:
             st.success(f"✅ Status: Stable. Shift is only {delta:+.1f}%.")
             
    else:
        st.warning("No live data found yet. Run 'python3 src/send_traffic.py --mode drift'")

def render_live_traffic_tab():
    st.header("Live Traffic & Predictions")

    # Manual refresh button, as in the day-by-day plan
    if st.button("Refresh Data"):
        st.experimental_rerun()

    df = load_data(
        "SELECT * FROM prediction_logs ORDER BY timestamp DESC LIMIT 1000"
    )
    
    # KPIs
    if df.empty:
        total_predictions = 0
        churn_rate = 0
    else:
        total_predictions = len(df)
        churn_rate = df["prediction"].mean() if "prediction" in df else 0

    # --- BUG FIX START ---
    # OLD CODE (Commented out):
    # model_version = (
    #     df["model_version"].iloc[0]
    #     if "model_version" in df and not df["model_version"].empty
    #     else "N/A"
    # )
    
    # NEW CODE: Fetch the REAL latest version from MLflow directly
    try:
        real_latest_version = get_latest_model_version(MODEL_NAME)
        if real_latest_version:
            model_version = real_latest_version
        else:
            # Fallback to logs if MLflow is unreachable
            model_version = df["model_version"].iloc[0] if "model_version" in df and not df.empty else "N/A"
    except Exception:
        model_version = "Error"
    # --- BUG FIX END ---

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Predictions", f"{total_predictions}")
    with col2:
        if churn_rate is not None:
            st.metric("Churn Rate", f"{churn_rate * 100:.2f}%")
        else:
            st.metric("Churn Rate", "N/A")
    with col3:
        st.metric("Current Model Version", str(model_version))

    if df.empty:
        st.info("No prediction logs found yet.")
        return

    # Requests per minute time series
    if "timestamp" in df:
        df_ts = df.copy()
        df_ts["timestamp_minute"] = pd.to_datetime(df_ts["timestamp"]).dt.floor("T")
        ts_counts = (
            df_ts.groupby("timestamp_minute")
            .size()
            .reset_index(name="requests_per_minute")
        )
        ts_counts = ts_counts.set_index("timestamp_minute")
        st.subheader("Requests per Minute")
        st.line_chart(ts_counts["requests_per_minute"])

    # Prediction distribution
    if "prediction" in df:
        pred_counts = df["prediction"].value_counts().reset_index()
        pred_counts.columns = ["prediction", "count"]
        pred_counts["label"] = pred_counts["prediction"].map(
            {0: "No Churn", 1: "Churn"}
        )
        fig = px.pie(
            pred_counts,
            names="label",
            values="count",
            title="Prediction Distribution",
        )
        st.subheader("Prediction Distribution")
        st.plotly_chart(fig, use_container_width=True)

    # Recent logs
    st.subheader("Recent Prediction Logs")
    st.dataframe(df.head(10))


def render_drift_monitoring_tab():
    st.header("Drift Monitoring")

    # Use created_at column from drift_reports table (there is no 'timestamp' column)
    df = load_data("SELECT * FROM drift_reports ORDER BY created_at DESC")
    if df.empty:
        st.info("No drift reports found yet.")
        return

    if "drift_detected" not in df:
        st.warning("Column 'drift_detected' not found in drift_reports.")
        return

    df["drift_detected_int"] = df["drift_detected"].astype(int)

    # Status banner based on latest drift flag
    latest_status = bool(df.iloc[0]["drift_detected"])
    if latest_status:
        st.error("🚨 DRIFT DETECTED in latest scan!")
    else:
        st.success("✅ System Healthy - No Drift Detected")

    # Drift timeline
    if "created_at" in df:
        df_timeline = df.copy()
        df_timeline["created_at"] = pd.to_datetime(df_timeline["created_at"])
        df_timeline = df_timeline.set_index("created_at")
        st.subheader("Drift Events Over Time")
        st.bar_chart(df_timeline["drift_detected_int"])

    # Drift details
    st.subheader("Drifted Batches")
    drifted = df[df["drift_detected"] == True]
    if drifted.empty:
        st.info("No drift detected so far.")
    else:
        st.dataframe(drifted)


def render_model_performance_tab():
    st.header("Model Performance History")

    df_runs = get_model_performance()

    if df_runs.empty:
        st.info("No metrics found for finished runs.")
        return

    # Performance trend
    st.subheader("Performance Trend Over Time")
    melted = df_runs.melt(
        id_vars=["start_time"],
        value_vars=["accuracy", "f1_score"],
        var_name="metric",
        value_name="value",
    ).dropna()
    if not melted.empty:
        fig = px.line(
            melted,
            x="start_time",
            y="value",
            color="metric",
            markers=True,
            labels={"start_time": "Date", "value": "Score"},
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No accuracy or f1_score metrics available to plot.")

    # Model comparison table
    st.subheader("Model Comparison")
    if "accuracy" in df_runs:
        st.dataframe(
            df_runs.sort_values("accuracy", ascending=False).reset_index(drop=True)
        )
    else:
        st.dataframe(df_runs)


def main():
    st.set_page_config(layout="wide", page_title="MLOps Dashboard")
    st.title("📡 MLOps Observability")

    # Tab-based layout as in the plan
    tab1, tab2, tab3 = st.tabs(
        ["📈 Live Traffic", "📉 Data Drift", "🏆 Model Performance"]
    )

    with tab1:
        render_live_traffic_tab()
    with tab2:
        render_drift_monitoring_tabv2()
    with tab3:
        render_model_performance_tab()


if __name__ == "__main__":
    main()
    