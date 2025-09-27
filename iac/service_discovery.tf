# Service Discovery Integration for ALB Traffic Routing
# This allows Entra App Proxy to continue using ai.ggai:8080
# while traffic gets routed to our ALB for horizontal scaling

# Data source for existing service discovery namespace
data "aws_service_discovery_dns_namespace" "ggai" {
  name = "ggai"
  type = "DNS_PRIVATE"
}

# Data source for existing service discovery service  
data "aws_service_discovery_service" "ai" {
  name         = "ai"
  namespace_id = data.aws_service_discovery_dns_namespace.ggai.id
}

# Create service discovery service for our scaled service
# This will create ai-scaled.ggai:8080 pointing to ALB
resource "aws_service_discovery_service" "ai_scaled" {
  name = "ai-scaled"
  
  dns_config {
    namespace_id = data.aws_service_discovery_dns_namespace.ggai.id
    
    dns_records {
      ttl  = 60
      type = "CNAME"
    }
    
    routing_policy = "WEIGHTED"
  }
  
  description = "Scaled OpenWebUI service pointing to ALB"
  
  tags = {
    Name = "OpenWebUI Scaled Service Discovery"
  }
}

# Register ALB with the scaled service discovery
resource "aws_service_discovery_instance" "alb_instance" {
  instance_id = "alb-primary"
  service_id  = aws_service_discovery_service.ai_scaled.id
  
  attributes = {
    # Point to ALB DNS name using CNAME record
    AWS_INSTANCE_CNAME = aws_lb.webui_alb.dns_name
  }
}

# Create service discovery service for Grafana OTEL monitoring
resource "aws_service_discovery_service" "otel_monitor" {
  name = "otel-monitor"

  dns_config {
    namespace_id = data.aws_service_discovery_dns_namespace.ggai.id

    dns_records {
      ttl  = 60
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }

  description = "Grafana OTEL LGTM monitoring stack - direct ECS access"

  tags = {
    Name = "OTEL Monitor Service Discovery"
  }
}

# Output for manual migration
locals {
  migration_commands = <<-EOT

    === SERVICE DISCOVERY MIGRATION ===

    CURRENT SETUP:
    - Entra App Proxy → ai.ggai:8080 → Single task

    NEW SETUP OPTIONS:

    Option 1: Create new endpoint (RECOMMENDED)
    - Entra App Proxy → ai-scaled.ggai:8080 → ALB → Multiple tasks
    - Test endpoint: ai-scaled.ggai:8080
    - Safer migration with rollback capability

    Option 2: Update existing endpoint (RISKIER)
    - Requires manual AWS CLI commands to update existing service discovery
    - Direct replacement of ai.ggai:8080 records

    === GRAFANA OTEL MONITORING ===

    NEW MONITORING ENDPOINTS:
    - Grafana Dashboard: http://grafana-monitoring.ggai:3000
    - OTLP gRPC Endpoint: http://grafana-monitoring.ggai:4317
    - OTLP HTTP Endpoint: http://grafana-monitoring.ggai:4318

    TESTING COMMANDS (from within VPC):
    nslookup ai-scaled.ggai
    nslookup grafana-monitoring.ggai

    MIGRATION VERIFICATION:
    curl -H "Host: ai-glondon.msappproxy.net" http://ai-scaled.ggai:8080/health

    GRAFANA ACCESS (via VPN):
    curl http://grafana-monitoring.ggai:3000
    # Default login: admin / openwebui_monitoring_2024

  EOT
}
