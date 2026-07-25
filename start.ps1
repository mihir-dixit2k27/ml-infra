# =============================================================
#  MLOps Churn Project — One-Click Startup Script
#  Run from project root: .\start.ps1
# =============================================================

$ErrorActionPreference = "Stop"

function Write-Step($n, $msg) {
    Write-Host "`n[$n] $msg" -ForegroundColor Cyan
}

function Write-Ok($msg) {
    Write-Host "    ✅ $msg" -ForegroundColor Green
}

function Write-Waiting($msg) {
    Write-Host "    ⏳ $msg" -ForegroundColor Yellow
}

function Write-Fail($msg) {
    Write-Host "    ❌ $msg" -ForegroundColor Red
}

function Wait-ForUrl($url, $label, $maxSeconds = 60) {
    $elapsed = 0
    while ($elapsed -lt $maxSeconds) {
        try {
            $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
            if ($response.StatusCode -lt 500) {
                Write-Ok "$label is up at $url"
                return $true
            }
        } catch {}
        Start-Sleep -Seconds 3
        $elapsed += 3
        Write-Host "    ... waiting ($elapsed/$maxSeconds s)" -ForegroundColor DarkGray
    }
    Write-Fail "$label did not respond at $url after ${maxSeconds}s"
    return $false
}

function Wait-ForDockerHealth($service, $maxSeconds = 60) {
    $elapsed = 0
    while ($elapsed -lt $maxSeconds) {
        $status = docker inspect --format "{{.State.Health.Status}}" $service 2>$null
        if ($status -eq "healthy") {
            Write-Ok "$service is healthy"
            return $true
        }
        Start-Sleep -Seconds 3
        $elapsed += 3
        Write-Host "    ... $service status: $status ($elapsed/$maxSeconds s)" -ForegroundColor DarkGray
    }
    Write-Fail "$service did not become healthy after ${maxSeconds}s"
    return $false
}

# =============================================================
Write-Host ""
Write-Host "=============================================" -ForegroundColor Magenta
Write-Host "   MLOps Churn Project — Starting Up" -ForegroundColor Magenta
Write-Host "=============================================" -ForegroundColor Magenta

# -------------------------------------------------------------
Write-Step "1/7" "Setting up environment file"
if (-Not (Test-Path ".env")) {
    Copy-Item env.example .env
    Write-Ok ".env created from env.example"
} else {
    Write-Ok ".env already exists — skipping"
}

# -------------------------------------------------------------
Write-Step "2/7" "Starting PostgreSQL + MLflow"
docker compose up -d postgres mlflow-ui
Write-Waiting "Waiting for PostgreSQL to be healthy..."
Wait-ForDockerHealth "postgres_db" -maxSeconds 60 | Out-Null
Write-Waiting "Waiting for MLflow UI to be ready..."
Wait-ForUrl "http://localhost:5001" "MLflow UI" -maxSeconds 90 | Out-Null

# -------------------------------------------------------------
Write-Step "3/7" "Training and registering model (skipped if already registered)"

$env:MLFLOW_TRACKING_URI = "http://localhost:5001"

# Check if model already exists in MLflow registry
try {
    $registered = Invoke-RestMethod -Uri "http://localhost:5001/api/2.0/mlflow/registered-models/get?name=telco-churn-champion" -ErrorAction Stop
    Write-Ok "Model 'telco-churn-champion' already registered — skipping training"
} catch {
    Write-Waiting "Model not found — running train_and_register.py ..."
    python scripts/train_and_register.py
    Write-Ok "Model trained and registered"
}

# -------------------------------------------------------------
Write-Step "4/7" "Starting FastAPI prediction service"
docker compose up -d api
Write-Waiting "Waiting for FastAPI to be ready..."
Wait-ForUrl "http://localhost:8000/health" "FastAPI" -maxSeconds 90 | Out-Null

# Verify model loaded
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -ErrorAction Stop
    if ($health.model_loaded) {
        Write-Ok "Model loaded: version $($health.model_version)"
    } else {
        Write-Fail "API is up but model is NOT loaded. Check: docker compose logs api"
    }
} catch {
    Write-Fail "Could not reach /health. Check: docker compose logs api"
}

# -------------------------------------------------------------
Write-Step "5/7" "Starting Streamlit Dashboard"
docker compose up -d dashboard
Write-Waiting "Waiting for Dashboard to be ready..."
Wait-ForUrl "http://localhost:8501" "Streamlit Dashboard" -maxSeconds 60 | Out-Null

# -------------------------------------------------------------
Write-Step "6/7" "Starting Airflow (init + webserver + scheduler)"
docker compose up -d airflow-init

Write-Waiting "Waiting for airflow-init to complete..."
$elapsed = 0
while ($elapsed -lt 120) {
    $exitCode = docker inspect --format "{{.State.ExitCode}}" mlops-churn-project-airflow-init-1 2>$null
    $status   = docker inspect --format "{{.State.Status}}"   mlops-churn-project-airflow-init-1 2>$null
    if ($status -eq "exited" -and $exitCode -eq "0") {
        Write-Ok "airflow-init completed successfully"
        break
    }
    if ($status -eq "exited" -and $exitCode -ne "0") {
        Write-Fail "airflow-init exited with code $exitCode — check: docker compose logs airflow-init"
        break
    }
    Start-Sleep -Seconds 3
    $elapsed += 3
    Write-Host "    ... waiting for airflow-init ($elapsed/120 s)" -ForegroundColor DarkGray
}

docker compose up -d airflow-webserver airflow-scheduler
Write-Waiting "Waiting for Airflow webserver to be ready..."
Wait-ForUrl "http://localhost:8080" "Airflow UI" -maxSeconds 90 | Out-Null

# -------------------------------------------------------------
Write-Step "7/7" "Opening browser tabs"
Start-Sleep -Seconds 2

$urls = @(
    "http://localhost:5001",   # MLflow
    "http://localhost:8000/docs",  # FastAPI Swagger
    "http://localhost:8501",   # Streamlit
    "http://localhost:8080"    # Airflow
)

foreach ($url in $urls) {
    Start-Process $url
    Start-Sleep -Milliseconds 500
}

Write-Ok "All browser tabs opened"

# =============================================================
Write-Host ""
Write-Host "=============================================" -ForegroundColor Magenta
Write-Host "   All services are up! 🚀" -ForegroundColor Magenta
Write-Host "=============================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "  MLflow UI      →  http://localhost:5001" -ForegroundColor White
Write-Host "  FastAPI Docs   →  http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Dashboard      →  http://localhost:8501" -ForegroundColor White
Write-Host "  Airflow UI     →  http://localhost:8080  (admin / admin)" -ForegroundColor White
Write-Host ""
Write-Host "  To simulate traffic:" -ForegroundColor DarkGray
Write-Host "    python scripts/simulate_traffic.py" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  To stop everything:" -ForegroundColor DarkGray
Write-Host "    docker compose down" -ForegroundColor DarkGray
Write-Host ""
