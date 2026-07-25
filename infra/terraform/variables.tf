# ── General ─────────────────────────────────────────────────────────────────

variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (dev | staging | prod)"
  type        = string
  default     = "dev"
}

variable "project" {
  description = "Project name — used in resource naming"
  type        = string
  default     = "mlops-churn"
}

# ── Networking ───────────────────────────────────────────────────────────────

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDRs for public subnets (one per AZ)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDRs for private subnets (one per AZ)"
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24"]
}

variable "availability_zones" {
  description = "List of AZs to use"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

# ── Database (RDS) ───────────────────────────────────────────────────────────

variable "db_name" {
  description = "Postgres database name"
  type        = string
  default     = "mlflow_db"
}

variable "db_username" {
  description = "Postgres master username"
  type        = string
  default     = "mlflow_user"
}

variable "db_password" {
  description = "Postgres master password — do NOT hardcode; set via tfvars or env var"
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  description = "RDS instance type"
  type        = string
  default     = "db.t3.micro"
}

# ── ECS / Application ────────────────────────────────────────────────────────

variable "model_name" {
  description = "MLflow registered model name"
  type        = string
  default     = "telco-churn-champion"
}

variable "model_alias" {
  description = "MLflow model alias to serve"
  type        = string
  default     = "production"
}

variable "api_cpu" {
  description = "CPU units for FastAPI task (1024 = 1 vCPU)"
  type        = number
  default     = 512
}

variable "api_memory" {
  description = "Memory (MiB) for FastAPI task"
  type        = number
  default     = 1024
}

variable "mlflow_cpu" {
  description = "CPU units for MLflow server task"
  type        = number
  default     = 512
}

variable "mlflow_memory" {
  description = "Memory (MiB) for MLflow server task"
  type        = number
  default     = 1024
}

variable "dashboard_cpu" {
  description = "CPU units for Streamlit dashboard task"
  type        = number
  default     = 256
}

variable "dashboard_memory" {
  description = "Memory (MiB) for Streamlit dashboard task"
  type        = number
  default     = 512
}

# ── Monitoring ───────────────────────────────────────────────────────────────

variable "alarm_email" {
  description = "Email address for CloudWatch alarm SNS notifications"
  type        = string
  default     = ""
}

variable "api_latency_threshold_ms" {
  description = "P99 API latency threshold (ms) — alerts above this value"
  type        = number
  default     = 500
}

variable "api_error_rate_threshold" {
  description = "API 5xx error rate % threshold for alerting"
  type        = number
  default     = 5
}
