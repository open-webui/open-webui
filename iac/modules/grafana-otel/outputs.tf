# Service Information
output "service_name" {
  description = "Name of the Grafana ECS service"
  value       = aws_ecs_service.grafana.name
}

output "service_arn" {
  description = "ARN of the Grafana ECS service"
  value       = aws_ecs_service.grafana.id
}

output "task_definition_arn" {
  description = "ARN of the Grafana task definition"
  value       = aws_ecs_task_definition.grafana.arn
}

# Access Information
output "grafana_dashboard_url" {
  description = "Grafana dashboard URL (accessible from allowed CIDR blocks)"
  value       = var.service_discovery_namespace_id != "" ? "http://${var.service_name}.${var.service_discovery_namespace_name}:3000" : "http://${var.service_name}.${aws_service_discovery_private_dns_namespace.grafana[0].name}:3000"
}

output "grafana_admin_credentials" {
  description = "Grafana admin login credentials"
  value = {
    username = var.grafana_admin_user
    password = var.grafana_admin_password
  }
  sensitive = true
}

output "otlp_endpoints" {
  description = "OpenTelemetry OTLP endpoints for telemetry data"
  value = {
    grpc = var.service_discovery_namespace_id != "" ? "http://${var.service_name}.${var.service_discovery_namespace_name}:4317" : "http://${var.service_name}.${aws_service_discovery_private_dns_namespace.grafana[0].name}:4317"
    http = var.service_discovery_namespace_id != "" ? "http://${var.service_name}.${var.service_discovery_namespace_name}:4318" : "http://${var.service_name}.${aws_service_discovery_private_dns_namespace.grafana[0].name}:4318"
  }
}

# Service Discovery Information
output "service_discovery_namespace_id" {
  description = "Service discovery namespace ID"
  value       = var.service_discovery_namespace_id != "" ? var.service_discovery_namespace_id : aws_service_discovery_private_dns_namespace.grafana[0].id
}

output "service_discovery_namespace_name" {
  description = "Service discovery namespace name"
  value       = var.service_discovery_namespace_id != "" ? var.service_discovery_namespace_name : aws_service_discovery_private_dns_namespace.grafana[0].name
}

output "service_discovery_service_arn" {
  description = "Service discovery service ARN"
  value       = aws_service_discovery_service.grafana.arn
}

# Security Information
output "security_group_id" {
  description = "Security group ID for Grafana tasks"
  value       = aws_security_group.grafana.id
}

output "execution_role_arn" {
  description = "IAM execution role ARN for Grafana tasks"
  value       = aws_iam_role.grafana_execution.arn
}

# Monitoring Information
output "cloudwatch_log_group_name" {
  description = "CloudWatch log group name for Grafana logs"
  value       = aws_cloudwatch_log_group.grafana.name
}

output "cloudwatch_log_group_arn" {
  description = "CloudWatch log group ARN for Grafana logs"
  value       = aws_cloudwatch_log_group.grafana.arn
}

# Setup Instructions
output "setup_instructions" {
  description = "Instructions for accessing and configuring Grafana monitoring"
  value = <<-EOT

    === GRAFANA OTEL MONITORING SETUP ===

    1. VERIFICATION COMMANDS (run from within VPC):
       nslookup ${var.service_name}.${var.service_discovery_namespace_id != "" ? var.service_discovery_namespace_name : aws_service_discovery_private_dns_namespace.grafana[0].name}
       curl ${var.service_discovery_namespace_id != "" ? "http://${var.service_name}.${var.service_discovery_namespace_name}:3000" : "http://${var.service_name}.${aws_service_discovery_private_dns_namespace.grafana[0].name}:3000"}

    2. GRAFANA ACCESS:
       URL: ${var.service_discovery_namespace_id != "" ? "http://${var.service_name}.${var.service_discovery_namespace_name}:3000" : "http://${var.service_name}.${aws_service_discovery_private_dns_namespace.grafana[0].name}:3000"}
       Username: ${var.grafana_admin_user}
       Password: ${var.grafana_admin_password}

    3. OPENTELEMETRY ENDPOINTS:
       - OTLP gRPC: ${var.service_discovery_namespace_id != "" ? "http://${var.service_name}.${var.service_discovery_namespace_name}:4317" : "http://${var.service_name}.${aws_service_discovery_private_dns_namespace.grafana[0].name}:4317"}
       - OTLP HTTP: ${var.service_discovery_namespace_id != "" ? "http://${var.service_name}.${var.service_discovery_namespace_name}:4318" : "http://${var.service_name}.${aws_service_discovery_private_dns_namespace.grafana[0].name}:4318"}

    4. MONITORING DATA SOURCES:
       - Prometheus: Pre-configured for metrics
       - Tempo: Pre-configured for distributed traces
       - Loki: Pre-configured for logs aggregation

    5. TROUBLESHOOTING:
       - Check ECS service status: aws ecs describe-services --cluster ${var.cluster_name} --services ${local.name_prefix}
       - View Grafana logs: aws logs tail ${aws_cloudwatch_log_group.grafana.name} --follow
       - Test connectivity from application security groups

    6. INTEGRATION WITH APPLICATIONS:
       To send telemetry data to this Grafana instance, configure your applications with:
       - OTEL_EXPORTER_OTLP_ENDPOINT: ${var.service_discovery_namespace_id != "" ? "http://${var.service_name}.${var.service_discovery_namespace_name}:4317" : "http://${var.service_name}.${aws_service_discovery_private_dns_namespace.grafana[0].name}:4317"}
       - Ensure your application security groups are added to otlp_sources_security_group_ids

  EOT
}
