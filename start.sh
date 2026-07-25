#!/bin/bash
# =============================================================
#  MLOps Churn Project — One-Click Startup Script (Bash/WSL)
#  Run from project root: bash start.sh
# =============================================================

# Note: NOT using set -e so individual step failures don't abort the whole script

GREEN="\033[0;32m"
CYAN="\033[0;36m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
RESET="\033[0m"

step()    { echo -e "\n${CYAN}[$1] $2${RESET}"; }
ok()      { echo -e "    ${GREEN}✅ $1${RESET}"; }
waiting() { echo -e "    ${YELLOW}⏳ $1${RESET}"; }
fail()    { echo -e "    ${RED}❌ $1${RESET}"; }

wait_for_url() {
    local url=$1
    local label=$2
    local max=${3:-60}
    local elapsed=0
    while [ $elapsed -lt $max ]; do
        if curl -sf "$url" -o /dev/null 2>/dev/null; then
            ok "$label is up at $url"
            return 0
        fi
        sleep 3
        elapsed=$((elapsed + 3))
        echo -e "    ... waiting ($elapsed/${max}s)"
    done
    fail "$label did not respond after ${max}s"
    return 1
}

wait_for_docker_health() {
    local container=$1
    local max=${2:-60}
    local elapsed=0
    while [ $elapsed -lt $max ]; do
        status=$(docker inspect --format "{{.State.Health.Status}}" "$container" 2>/dev/null || echo "unknown")
        if [ "$status" = "healthy" ]; then
            ok "$container is healthy"
            return 0
        fi
        sleep 3
        elapsed=$((elapsed + 3))
        echo "    ... $container status: $status ($elapsed/${max}s)"
    done
    fail "$container did not become healthy after ${max}s"
    return 1
}

# =============================================================
echo ""
echo "============================================="
echo "   MLOps Churn Project — Starting Up"
echo "============================================="

# -------------------------------------------------------
step "1/7" "Setting up environment file"
if [ ! -f ".env" ]; then
    cp env.example .env
    ok ".env created from env.example"
else
    ok ".env already exists — skipping"
fi

# -------------------------------------------------------
step "Pre-check" "Removing any orphaned containers from previous runs"
for name in postgres_db mlflow_server fast_api mlops_dashboard; do
    if docker inspect "$name" &>/dev/null; then
        docker rm -f "$name" &>/dev/null || true
        echo "    🧹 Removed stale container: $name"
    fi
done
docker compose down --remove-orphans 2>/dev/null || true
ok "Cleanup done"

# -------------------------------------------------------
step "2/7" "Starting PostgreSQL + MLflow"
docker compose up -d postgres mlflow-ui
waiting "Waiting for PostgreSQL to be healthy..."
wait_for_docker_health "postgres_db" 60

# Auto-create airflow_db (Airflow needs its own DB separate from mlflow_db)
echo "    🗄️  Ensuring airflow_db exists in Postgres..."
docker exec postgres_db psql -U mlflow_user -d mlflow_db \
    -c "SELECT 1 FROM pg_database WHERE datname='airflow_db'" \
    | grep -q 1 || \
    docker exec postgres_db psql -U mlflow_user -d mlflow_db \
    -c "CREATE DATABASE airflow_db" 2>/dev/null || true
ok "airflow_db ready"

waiting "Waiting for MLflow UI to be ready..."
wait_for_url "http://localhost:5001" "MLflow UI" 90

# -------------------------------------------------------
step "3/7" "Training and registering model (skipped if already registered)"

if curl -sf "http://localhost:5001/api/2.0/mlflow/registered-models/get?name=telco-churn-champion" -o /dev/null 2>/dev/null; then
    ok "Model already registered — skipping training"
else
    waiting "Model not found — building api image and running train_and_register.py inside Docker..."
    # Run training inside the api container — it already has all Python deps installed
    docker compose run --rm \
        -e MLFLOW_TRACKING_URI=http://mlflow-ui:5000 \
        -v "$(pwd)/scripts:/scripts" \
        -v "$(pwd)/data:/app/data" \
        --entrypoint python \
        api /scripts/train_and_register.py
    ok "Model trained and registered"
fi

# -------------------------------------------------------
step "4/7" "Starting FastAPI prediction service"
docker compose up -d api
waiting "Waiting for FastAPI to be ready..."
wait_for_url "http://localhost:8000/health" "FastAPI" 90

# Check model loaded
health=$(curl -sf http://localhost:8000/health 2>/dev/null || echo "{}")
if echo "$health" | grep -q '"model_loaded": *true'; then
    ok "Model is loaded and API is healthy"
else
    fail "API is up but model may not be loaded. Run: docker compose logs api"
fi

# -------------------------------------------------------
step "5/7" "Starting Streamlit Dashboard"
docker compose up -d dashboard
waiting "Waiting for Dashboard to be ready..."
wait_for_url "http://localhost:8501" "Streamlit Dashboard" 60

# -------------------------------------------------------
step "6/7" "Starting Airflow"
docker compose up -d airflow-init
waiting "Waiting for airflow-init to complete (first run builds image — can take 5-10 min)..."

# Auto-detect the actual container name (varies by Docker Compose version)
AIRFLOW_INIT_CONTAINER=$(docker ps -a --filter "name=airflow-init" --format "{{.Names}}" | head -1)
echo "    Detected airflow-init container: $AIRFLOW_INIT_CONTAINER"

MAX_WAIT=600   # 10 minutes — covers first-run pip install in the image
elapsed=0
INIT_OK=false
while [ $elapsed -lt $MAX_WAIT ]; do
    if [ -z "$AIRFLOW_INIT_CONTAINER" ]; then
        # Try to find it again — may not have started yet
        AIRFLOW_INIT_CONTAINER=$(docker ps -a --filter "name=airflow-init" --format "{{.Names}}" | head -1)
    fi
    if [ -n "$AIRFLOW_INIT_CONTAINER" ]; then
        exit_code=$(docker inspect --format "{{.State.ExitCode}}" "$AIRFLOW_INIT_CONTAINER" 2>/dev/null || echo "-1")
        status=$(docker inspect --format "{{.State.Status}}" "$AIRFLOW_INIT_CONTAINER" 2>/dev/null || echo "unknown")
        if [ "$status" = "exited" ] && [ "$exit_code" = "0" ]; then
            ok "airflow-init completed successfully"
            INIT_OK=true
            break
        elif [ "$status" = "exited" ] && [ "$exit_code" != "0" ]; then
            fail "airflow-init exited with error code $exit_code"
            echo "    Run: docker compose logs airflow-init"
            break
        fi
    fi
    sleep 5
    elapsed=$((elapsed + 5))
    echo "    ... airflow-init running ($elapsed/${MAX_WAIT}s)"
done

if [ "$INIT_OK" = false ] && [ $elapsed -ge $MAX_WAIT ]; then
    fail "airflow-init timed out — check: docker compose logs airflow-init"
fi

echo "    Starting airflow-webserver and airflow-scheduler..."
docker compose up -d airflow-webserver airflow-scheduler
waiting "Waiting for Airflow UI to be ready..."
wait_for_url "http://localhost:8080" "Airflow UI" 120

# -------------------------------------------------------
step "7/7" "Opening browser (xdg-open)"

# WSL: open in Windows browser
open_url() {
    if command -v explorer.exe &>/dev/null; then
        explorer.exe "$1" 2>/dev/null || true
    elif command -v xdg-open &>/dev/null; then
        xdg-open "$1" 2>/dev/null || true
    fi
}

sleep 1
open_url "http://localhost:5001"
sleep 0.5
open_url "http://localhost:8000/docs"
sleep 0.5
open_url "http://localhost:8501"
sleep 0.5
open_url "http://localhost:8080"
ok "Browser tabs opened"

# =============================================================
echo ""
echo "============================================="
echo "   All services are up! 🚀"
echo "============================================="
echo ""
echo "  MLflow UI      →  http://localhost:5001"
echo "  FastAPI Docs   →  http://localhost:8000/docs"
echo "  Dashboard      →  http://localhost:8501"
echo "  Airflow UI     →  http://localhost:8080  (admin / admin)"
echo ""
echo "  To simulate traffic:"
echo "    python3 scripts/simulate_traffic.py"
echo ""
echo "  To stop everything:"
echo "    docker compose down"
echo ""
