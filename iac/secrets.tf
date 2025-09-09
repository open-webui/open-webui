# Generate shared secret for JWT signing
resource "random_password" "webui_secret_key" {
  length  = 32
  special = false  # Avoid special characters that might cause issues
}

# Shared secret for consistent JWT tokens across instances
resource "aws_secretsmanager_secret" "webui_shared_secret" {
  name                    = "openwebui-shared-secret"
  description             = "Shared secret for OpenWebUI JWT signing across instances"
  recovery_window_in_days = 0  # Force immediate deletion to avoid naming conflicts
  force_overwrite_replica_secret = true

  tags = {
    Name = "OpenWebUI Shared Secret"
  }
}

resource "aws_secretsmanager_secret_version" "webui_shared_secret" {
  secret_id     = aws_secretsmanager_secret.webui_shared_secret.id
  secret_string = random_password.webui_secret_key.result
}

# Dedicated ECS task execution role for OpenWebUI scaled service
resource "aws_iam_role" "openwebui_execution_role" {
  name = "openwebui-scaled-execution-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Name = "OpenWebUI Scaled Execution Role"
  }
}

# Attach AWS managed ECS execution policy
resource "aws_iam_role_policy_attachment" "openwebui_execution_role_policy" {
  role       = aws_iam_role.openwebui_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Service-specific secrets access via inline policy
resource "aws_iam_role_policy" "openwebui_secrets_policy" {
  name = "openwebui-scaled-secrets-access"
  role = aws_iam_role.openwebui_execution_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["secretsmanager:GetSecretValue"]
        Resource = [
          aws_secretsmanager_secret.webui_shared_secret.arn,
          aws_secretsmanager_secret.redis_connection.arn,
          var.existing_database_secret_arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = "*"
      }
    ]
  })
}
