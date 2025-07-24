variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS CLI profile to use"
  type        = string
  default     = "908027381725_AdministratorAccess"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "vpc_id" {
  description = "VPC ID where resources will be deployed"
  type        = string
  default     = "vpc-01bc2784063a567d3"
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for deployment"
  type        = list(string)
  default     = ["subnet-01296c54f7bff84bc", "subnet-00da3547f2178dd85"]
}

variable "existing_ecs_security_group_id" {
  description = "Existing ECS security group ID to reference"
  type        = string
  default     = "sg-05e12bd2e202e19f6"
}

variable "cluster_name" {
  description = "ECS cluster name"
  type        = string
  default     = "webUIcluster2"
}

variable "service_name" {
  description = "New ECS service name for scaled deployment"
  type        = string
  default     = "webui3-scaled"
}

variable "task_family_name" {
  description = "ECS task definition family name"
  type        = string
  default     = "webUIfargate-scaled"
}

variable "container_image" {
  description = "Container image URI"
  type        = string
  default     = "908027381725.dkr.ecr.us-east-1.amazonaws.com/github/open-webui/open-webui:v0.6.18-hybrid-search-2"
}

variable "desired_count" {
  description = "Desired number of tasks"
  type        = number
  default     = 2
}

variable "cpu" {
  description = "CPU units for each task"
  type        = number
  default     = 4096
}

variable "memory" {
  description = "Memory (MB) for each task"
  type        = number
  default     = 8192
}

variable "efs_file_system_id" {
  description = "EFS file system ID"
  type        = string
  default     = "fs-0bffb5d27667773bf"
}

variable "efs_access_point_id" {
  description = "EFS access point ID"
  type        = string
  default     = "fsap-0af54ce708a21816e"
}

variable "existing_task_execution_role_arn" {
  description = "Existing ECS task execution role ARN"
  type        = string
  default     = "arn:aws:iam::908027381725:role/ecsTaskExecutionRole"
}

variable "existing_database_secret_arn" {
  description = "Existing database secret ARN"
  type        = string
  default     = "arn:aws:secretsmanager:us-east-1:908027381725:secret:webUIpostgresDB-IlIf3w"
}

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_engine_version" {
  description = "Redis engine version"
  type        = string
  default     = "7.0"
}

variable "entra_proxy_ip" {
  description = "Entra proxy server IP for ALB access"
  type        = string
  default     = "192.168.144.11/32"
}

variable "gg_vpn_cidr" {
  description = "GG VPN CIDR for ALB access"
  type        = string
  default     = "192.168.158.0/24"
}

variable "rds_security_group_id" {
  description = "Security group ID for RDS PostgreSQL instance"
  type        = string
  default     = "sg-09b2b27665b7e7ccc"
}

variable "efs_security_group_1_id" {
  description = "First EFS security group ID"
  type        = string
  default     = "sg-0dddfef211b1bee1f"
}

variable "efs_security_group_2_id" {
  description = "Second EFS security group ID"
  type        = string
  default     = "sg-0067670c2a1f54b18"
}

variable "pipelines_security_group_id" {
  description = "Security group ID for the pipelines service"
  type        = string
  default     = "sg-049461f6151961660"
}

variable "docling_serve_security_group_id" {
  description = "Security group ID for the docling-serve service"
  type        = string
  default     = "sg-001574b4a259a765f"
}

variable "mcpo_security_group_id" {
  description = "Security group ID for the mcpo service"
  type        = string
  default     = "sg-0cdc36e6d551602e4"
}

variable "jupyter_notebook_security_group_id" {
  description = "Security group ID for the jupyter-notebook service"
  type        = string
  default     = "sg-0cf8422fe6d4ff14d"
}
