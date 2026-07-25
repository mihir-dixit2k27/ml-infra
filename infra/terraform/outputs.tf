output "alb_url" {
  description = "ALB DNS — paste into your browser to reach the API"
  value       = "http://${module.ecs.alb_dns_name}"
}

output "ecr_api_url" {
  description = "ECR URL for the FastAPI image"
  value       = module.ecr.api_repository_url
}

output "ecr_mlflow_url" {
  description = "ECR URL for the MLflow image"
  value       = module.ecr.mlflow_repository_url
}

output "ecr_dashboard_url" {
  description = "ECR URL for the Streamlit dashboard image"
  value       = module.ecr.dashboard_repository_url
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = module.rds.db_endpoint
  sensitive   = true
}

output "ecs_cluster_name" {
  description = "ECS cluster name — use this in aws ecs commands"
  value       = module.ecs.ecs_cluster_name
}

output "sns_alarm_topic_arn" {
  description = "SNS topic ARN for CloudWatch alarms"
  value       = module.monitoring.sns_alarm_topic_arn
}
