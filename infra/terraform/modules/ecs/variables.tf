variable "project"                  { type = string }
variable "environment"              { type = string }
variable "aws_region"               { type = string }
variable "vpc_id"                   { type = string }
variable "public_subnet_ids"        { type = list(string) }
variable "private_subnet_ids"       { type = list(string) }
variable "alb_sg_id"                { type = string }
variable "ecs_tasks_sg_id"          { type = string }
variable "task_execution_role_arn"  { type = string }
variable "task_role_arn"            { type = string }
variable "api_image_url"            { type = string }
variable "mlflow_image_url"         { type = string }
variable "dashboard_image_url"      { type = string }
variable "db_host"                  { type = string }
variable "db_name"                  { type = string }
variable "db_username"              { type = string }
variable "db_password"              { type = string; sensitive = true }
variable "model_name"               { type = string }
variable "model_alias"              { type = string }
variable "mlflow_artifact_bucket"   { type = string; default = "" }
variable "api_cpu"                  { type = number }
variable "api_memory"               { type = number }
variable "mlflow_cpu"               { type = number }
variable "mlflow_memory"            { type = number }
variable "dashboard_cpu"            { type = number }
variable "dashboard_memory"         { type = number }
