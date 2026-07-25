# DB Subnet Group — place RDS in private subnets
resource "aws_db_subnet_group" "main" {
  name       = "${var.project}-${var.environment}-db-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = { Name = "${var.project}-${var.environment}-db-subnet-group" }
}

# RDS PostgreSQL instance
resource "aws_db_instance" "postgres" {
  identifier = "${var.project}-${var.environment}-postgres"

  engine         = "postgres"
  engine_version = "15.4"
  instance_class = var.db_instance_class

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [var.rds_sg_id]

  allocated_storage     = 20
  max_allocated_storage = 100 # autoscaling up to 100 GiB
  storage_type          = "gp3"
  storage_encrypted     = true

  # Free-tier / dev settings
  multi_az               = false
  publicly_accessible    = false
  skip_final_snapshot    = true  # Set to false for production!
  deletion_protection    = false # Set to true for production!
  backup_retention_period = 7

  performance_insights_enabled = false

  tags = { Name = "${var.project}-${var.environment}-postgres" }
}
