# AWS Configuration
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
  description = "Environment name (e.g., production, staging, dev)"
  type        = string
  default     = "production"
}

variable "name_prefix" {
  description = "Prefix for all resource names"
  type        = string
  default     = "grafana-otel"
}

# Core Infrastructure (Required)
variable "vpc_id" {
  description = "VPC ID where Grafana will be deployed"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for Grafana ECS tasks"
  type        = list(string)
}

variable "cluster_name" {
  description = "ECS cluster name where Grafana will be deployed"
  type        = string
}

# Network Access Configuration
variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access Grafana UI (port 3000)"
  type        = list(string)
  default     = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
}

# Grafana Configuration
variable "grafana_admin_user" {
  description = "Grafana admin username"
  type        = string
  default     = "admin"
}

variable "grafana_admin_password" {
  description = "Grafana admin password"
  type        = string
  default     = "openwebui_monitoring_2024"
  sensitive   = true
}

# Service Discovery Configuration
variable "service_discovery_namespace_id" {
  description = "Service discovery namespace ID (if using existing namespace)"
  type        = string
  default     = ""
}

variable "service_discovery_namespace_name" {
  description = "Service discovery namespace name (creates new if namespace_id not provided)"
  type        = string
  default     = "grafana-monitoring"
}

variable "service_name" {
  description = "Service discovery service name"
  type        = string
  default     = "otel-monitor"
}

# Resource Configuration
variable "cpu" {
  description = "CPU units for Grafana task"
  type        = number
  default     = 1024
}

variable "memory" {
  description = "Memory (MB) for Grafana task"
  type        = number
  default     = 2048
}

variable "desired_count" {
  description = "Desired number of Grafana tasks"
  type        = number
  default     = 1
}

# Scaling Configuration
variable "enable_autoscaling" {
  description = "Enable ECS autoscaling for Grafana"
  type        = bool
  default     = true
}

variable "max_capacity" {
  description = "Maximum number of tasks for autoscaling"
  type        = number
  default     = 2
}

variable "min_capacity" {
  description = "Minimum number of tasks for autoscaling"
  type        = number
  default     = 1
}

variable "cpu_target_value" {
  description = "Target CPU utilization for autoscaling"
  type        = number
  default     = 80.0
}

# Monitoring Configuration
variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

# Security Configuration
variable "otlp_sources_security_group_ids" {
  description = "Security group IDs that should be allowed to send OTLP data to Grafana"
  type        = list(string)
  default     = []
}

variable "additional_security_group_ids" {
  description = "Additional security group IDs to attach to Grafana tasks"
  type        = list(string)
  default     = []
}

# Tags
variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default = {
    Project   = "grafana-monitoring"
    ManagedBy = "terraform"
  }
}
