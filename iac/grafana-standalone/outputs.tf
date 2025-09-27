# Pass through module outputs
output "grafana_dashboard_url" {
  description = "Grafana dashboard URL (accessible from allowed CIDR blocks)"
  value       = module.grafana_otel.grafana_dashboard_url
}

output "grafana_admin_credentials" {
  description = "Grafana admin login credentials"
  value       = module.grafana_otel.grafana_admin_credentials
  sensitive   = true
}

output "otlp_endpoints" {
  description = "OpenTelemetry OTLP endpoints for telemetry data"
  value       = module.grafana_otel.otlp_endpoints
}

output "service_discovery_info" {
  description = "Service discovery information"
  value = {
    namespace_id   = module.grafana_otel.service_discovery_namespace_id
    namespace_name = module.grafana_otel.service_discovery_namespace_name
    service_arn    = module.grafana_otel.service_discovery_service_arn
  }
}

output "security_group_id" {
  description = "Security group ID for Grafana tasks"
  value       = module.grafana_otel.security_group_id
}

output "execution_role_arn" {
  description = "IAM execution role ARN for Grafana tasks"
  value       = module.grafana_otel.execution_role_arn
}

output "cloudwatch_log_group_name" {
  description = "CloudWatch log group name for Grafana logs"
  value       = module.grafana_otel.cloudwatch_log_group_name
}

output "setup_instructions" {
  description = "Instructions for accessing and configuring Grafana monitoring"
  value       = module.grafana_otel.setup_instructions
  sensitive   = true
}
