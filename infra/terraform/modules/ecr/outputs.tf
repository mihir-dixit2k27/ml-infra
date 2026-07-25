output "api_repository_url"       { value = aws_ecr_repository.api.repository_url }
output "mlflow_repository_url"    { value = aws_ecr_repository.mlflow.repository_url }
output "dashboard_repository_url" { value = aws_ecr_repository.dashboard.repository_url }
