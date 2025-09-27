# Configure the AWS Provider
terraform {
  required_version = ">= 1.0"
  
  # Remote state backend configuration for Grafana standalone
  backend "s3" {
    bucket         = "gg-ai-terraform-states"
    key            = "production/grafana-monitoring/terraform.tfstate"
    region         = "us-east-1"
    profile        = "908027381725_AdministratorAccess"
    dynamodb_table = "terraform-state-locks"
    encrypt        = true
  }
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

# Deploy Grafana OTEL monitoring stack
module "grafana_otel" {
  source = "../modules/grafana-otel"

  # Core Infrastructure (required)
  vpc_id             = var.vpc_id
  private_subnet_ids = var.private_subnet_ids
  cluster_name       = var.cluster_name

  # Environment Configuration
  environment = var.environment
  aws_region  = var.aws_region
  name_prefix = var.name_prefix

  # Network Access Configuration
  allowed_cidr_blocks = var.allowed_cidr_blocks

  # Grafana Configuration
  grafana_admin_user     = var.grafana_admin_user
  grafana_admin_password = var.grafana_admin_password

  # Service Discovery Configuration
  service_discovery_namespace_id   = var.service_discovery_namespace_id
  service_discovery_namespace_name = var.service_discovery_namespace_name
  service_name                     = var.service_name

  # Resource Configuration
  cpu           = var.cpu
  memory        = var.memory
  desired_count = var.desired_count

  # Scaling Configuration
  enable_autoscaling = var.enable_autoscaling
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  cpu_target_value   = var.cpu_target_value

  # Monitoring Configuration
  log_retention_days = var.log_retention_days

  # Security Configuration
  otlp_sources_security_group_ids = var.otlp_sources_security_group_ids
  additional_security_group_ids   = var.additional_security_group_ids

  # Tags
  tags = var.tags
}
