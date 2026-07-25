module "networking" {
  source = "./modules/networking"

  project              = var.project
  environment          = var.environment
  vpc_cidr             = var.vpc_cidr
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  availability_zones   = var.availability_zones
}

module "ecr" {
  source = "./modules/ecr"

  project     = var.project
  environment = var.environment
}

module "iam" {
  source = "./modules/iam"

  project     = var.project
  environment = var.environment
}

module "rds" {
  source = "./modules/rds"

  project           = var.project
  environment       = var.environment
  private_subnet_ids = module.networking.private_subnet_ids
  rds_sg_id         = module.networking.rds_sg_id
  db_name           = var.db_name
  db_username       = var.db_username
  db_password       = var.db_password
  db_instance_class = var.db_instance_class
}

module "ecs" {
  source = "./modules/ecs"

  project                 = var.project
  environment             = var.environment
  aws_region              = var.aws_region
  vpc_id                  = module.networking.vpc_id
  public_subnet_ids       = module.networking.public_subnet_ids
  private_subnet_ids      = module.networking.private_subnet_ids
  alb_sg_id               = module.networking.alb_sg_id
  ecs_tasks_sg_id         = module.networking.ecs_tasks_sg_id
  task_execution_role_arn = module.iam.ecs_task_execution_role_arn
  task_role_arn           = module.iam.ecs_task_role_arn
  api_image_url           = module.ecr.api_repository_url
  mlflow_image_url        = module.ecr.mlflow_repository_url
  dashboard_image_url     = module.ecr.dashboard_repository_url
  db_host                 = split(":", module.rds.db_endpoint)[0]
  db_name                 = var.db_name
  db_username             = var.db_username
  db_password             = var.db_password
  model_name              = var.model_name
  model_alias             = var.model_alias
  api_cpu                 = var.api_cpu
  api_memory              = var.api_memory
  mlflow_cpu              = var.mlflow_cpu
  mlflow_memory           = var.mlflow_memory
  dashboard_cpu           = var.dashboard_cpu
  dashboard_memory        = var.dashboard_memory
}

module "monitoring" {
  source = "./modules/monitoring"

  project                     = var.project
  environment                 = var.environment
  alarm_email                 = var.alarm_email
  api_latency_threshold_ms    = var.api_latency_threshold_ms
  api_error_rate_threshold    = var.api_error_rate_threshold
  alb_arn_suffix              = module.ecs.alb_arn_suffix
  api_target_group_arn_suffix = module.ecs.api_target_group_arn_suffix
  ecs_cluster_name            = module.ecs.ecs_cluster_name
  api_service_name            = module.ecs.api_service_name
  db_instance_id              = module.rds.db_instance_id
}
