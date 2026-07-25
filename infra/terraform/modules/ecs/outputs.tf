output "ecs_cluster_name"               { value = aws_ecs_cluster.main.name }
output "alb_dns_name"                   { value = aws_lb.main.dns_name }
output "alb_arn_suffix"                 { value = aws_lb.main.arn_suffix }
output "api_target_group_arn_suffix"    { value = aws_lb_target_group.api.arn_suffix }
output "api_service_name"               { value = aws_ecs_service.api.name }
output "mlflow_service_name"            { value = aws_ecs_service.mlflow.name }
output "dashboard_service_name"         { value = aws_ecs_service.dashboard.name }
output "mlflow_artifact_bucket"         { value = aws_s3_bucket.mlflow_artifacts.bucket }
