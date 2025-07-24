# Generate random password for Redis
resource "random_password" "redis_auth_token" {
  length  = 32
  special = false  # Disable special characters to avoid invalid ones for ElastiCache
  upper   = true
  lower   = true
  numeric = true
}

# ElastiCache subnet group
resource "aws_elasticache_subnet_group" "redis_subnet_group" {
  name       = "openwebui-redis-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name = "OpenWebUI Redis Subnet Group"
  }
}

# Security group for Redis
resource "aws_security_group" "redis_sg" {
  name_prefix = "openwebui-redis-"
  vpc_id      = var.vpc_id
  description = "Security group for OpenWebUI Redis cluster"

  # Allow Redis traffic from ECS tasks
  ingress {
    description     = "Redis from ECS"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [var.existing_ecs_security_group_id, aws_security_group.ecs_scaled_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "OpenWebUI Redis Security Group"
  }
}

# ElastiCache Redis cluster
resource "aws_elasticache_replication_group" "redis" {
  description          = "Redis cluster for OpenWebUI horizontal scaling"
  replication_group_id = "openwebui-redis"
  
  # Use cluster mode for better scalability
  num_cache_clusters = 1
  
  node_type                  = var.redis_node_type
  port                      = 6379
  parameter_group_name      = "default.redis7"
  engine_version           = var.redis_engine_version
  
  # Security and networking
  subnet_group_name    = aws_elasticache_subnet_group.redis_subnet_group.name
  security_group_ids   = [aws_security_group.redis_sg.id]
  
  # Enable encryption
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = random_password.redis_auth_token.result
  
  # Backup configuration
  snapshot_retention_limit = 3
  snapshot_window         = "05:00-06:00"
  maintenance_window      = "sun:06:00-sun:07:00"
  
  # Performance
  apply_immediately = true
  
  # Logging
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_slow_log.name
    destination_type = "cloudwatch-logs"
    log_format       = "text"
    log_type         = "slow-log"
  }

  tags = {
    Name = "OpenWebUI Redis Cluster"
  }
}

# CloudWatch log group for Redis
resource "aws_cloudwatch_log_group" "redis_slow_log" {
  name              = "/aws/elasticache/openwebui-redis/slow-log"
  retention_in_days = 7

  tags = {
    Name = "OpenWebUI Redis Slow Log"
  }
}

# Store Redis connection details in Secrets Manager
resource "aws_secretsmanager_secret" "redis_connection" {
  name                    = "openwebui-redis-connection"
  description             = "Redis connection details for OpenWebUI"
  recovery_window_in_days = 0  # Force immediate deletion to avoid naming conflicts
  force_overwrite_replica_secret = true

  tags = {
    Name = "OpenWebUI Redis Connection Secret"
  }
}

resource "aws_secretsmanager_secret_version" "redis_connection" {
  secret_id = aws_secretsmanager_secret.redis_connection.id
  secret_string = jsonencode({
    host      = aws_elasticache_replication_group.redis.primary_endpoint_address
    port      = aws_elasticache_replication_group.redis.port
    auth_token = random_password.redis_auth_token.result
    url       = "rediss://:${random_password.redis_auth_token.result}@${aws_elasticache_replication_group.redis.primary_endpoint_address}:${aws_elasticache_replication_group.redis.port}"
  })
}
