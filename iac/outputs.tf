output "alb_dns_name" {
  description = "DNS name of the internal Application Load Balancer"
  value       = aws_lb.webui_alb.dns_name
}

output "alb_zone_id" {
  description = "Hosted zone ID of the ALB"
  value       = aws_lb.webui_alb.zone_id
}

output "redis_endpoint" {
  description = "Redis endpoint for connection"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
  sensitive   = true
}

output "redis_port" {
  description = "Redis port"
  value       = aws_elasticache_replication_group.redis.port
}

output "service_name" {
  description = "Name of the scaled ECS service"
  value       = aws_ecs_service.webui_scaled.name
}

output "task_definition_arn" {
  description = "ARN of the scaled task definition"
  value       = aws_ecs_task_definition.webui_scaled.arn
}

output "target_group_arn" {
  description = "ARN of the ALB target group"
  value       = aws_lb_target_group.webui_targets.arn
}

output "shared_secret_arn" {
  description = "ARN of the shared secret for JWT signing"
  value       = aws_secretsmanager_secret.webui_shared_secret.arn
  sensitive   = true
}

output "redis_secret_arn" {
  description = "ARN of the Redis connection secret"
  value       = aws_secretsmanager_secret.redis_connection.arn
  sensitive   = true
}

output "dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.webui_dashboard.dashboard_name}"
}

output "migration_instructions" {
  description = "Instructions for switching traffic from old to new service"
  value = <<-EOT
    
    === BLUE-GREEN MIGRATION STEPS ===
    
    1. Test new scaled service:
       curl -H "Host: ai-glondon.msappproxy.net" http://${aws_lb.webui_alb.dns_name}:8080/health
    
    2. Validate load balancing (multiple requests should hit different tasks):
       for i in {1..5}; do curl -s http://${aws_lb.webui_alb.dns_name}:8080/health; echo; done
    
    3. Monitor auto-scaling dashboard:
       ${aws_cloudwatch_dashboard.webui_dashboard.dashboard_name}
    
    4. CUTOVER: Update Entra App Proxy backend (if you have access):
       FROM: Current service discovery endpoint  
       TO:   http://${aws_lb.webui_alb.dns_name}
    
    5. After successful cutover, scale down old service:
       aws ecs update-service --cluster ${var.cluster_name} --service webui3 --desired-count 0
    
    6. Emergency rollback (if needed):
       - Revert Entra App Proxy to old endpoint
       - Scale down new service: aws ecs update-service --cluster ${var.cluster_name} --service ${var.service_name} --desired-count 0
       - Scale up old service: aws ecs update-service --cluster ${var.cluster_name} --service webui3 --desired-count 1
    
    === TESTING ENDPOINTS ===
    Internal ALB: http://${aws_lb.webui_alb.dns_name}:8080
    Health Check: http://${aws_lb.webui_alb.dns_name}:8080/health
    
  EOT
}

output "service_discovery_migration" {
  description = "Service discovery migration instructions (since Entra App Proxy cannot be modified)"
  value       = local.migration_commands
} 