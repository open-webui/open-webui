# Security group for the new scaled ECS service
resource "aws_security_group" "ecs_scaled_sg" {
  name_prefix = "openwebui-ecs-scaled-"
  vpc_id      = var.vpc_id
  description = "Security group for OpenWebUI scaled ECS tasks"

  # Allow traffic from ALB
  ingress {
    description     = "HTTP from ALB"
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
  }

  # Allow traffic from existing services for gradual migration
  ingress {
    description     = "HTTP from existing services"
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [var.existing_ecs_security_group_id]
  }

  # Allow traffic from Entra proxy (for direct testing)
  ingress {
    description = "HTTP from Entra Proxy (testing)"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = [var.entra_proxy_ip]
  }

  # Allow traffic from GG VPN (for direct testing)
  ingress {
    description = "HTTP from GG VPN (testing)"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = [var.gg_vpn_cidr]
  }

  ingress {
    description     = "HTTP from n8n"
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = ["sg-0b5ec78a0bbbd49af"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "OpenWebUI ECS Scaled Security Group"
  }
}

# CloudWatch log group for the new service
resource "aws_cloudwatch_log_group" "ecs_scaled_logs" {
  name              = "/ecs/webUIfargate-scaled"
  retention_in_days = 7

  tags = {
    Name = "OpenWebUI ECS Scaled Logs"
  }
}

# ECS Task Definition for scaled deployment
resource "aws_ecs_task_definition" "webui_scaled" {
  family                   = var.task_family_name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = var.existing_task_execution_role_arn
  task_role_arn           = var.existing_task_execution_role_arn

  container_definitions = jsonencode([
    {
      name      = "openwebui"
      image     = var.container_image
      cpu       = 0
      essential = true

      portMappings = [
        {
          containerPort = 8080
          hostPort      = 8080
          protocol      = "tcp"
          name          = "openwebui-http"
          appProtocol   = "http"
        }
      ]

      environment = [
        {
          name  = "WEBUI_AUTH_TRUSTED_EMAIL_HEADER"
          value = "X-User-Email"
        },
        {
          name  = "WEBUI_AUTH_TRUSTED_NAME_HEADER"
          value = "X-User-Name"
        },
        {
          name  = "WEBUI_AUTH_TRUSTED_GROUPS_HEADER"
          value = "X-User-Groups"
        },
        {
          name  = "WEBUI_AUTH_SIGNOUT_REDIRECT_URL"
          value = "https://ai-glondon.msappproxy.net/auth?redirect=%2F"
        },
        {
          name  = "ENABLE_QDRANT_MULTITENANCY_MODE"
          value = "true"
        },
        {
          name  = "QDRANT_API_KEY"
          value = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.WysrVwMLMAnxxLUS70cWWVpr-sc1C8jcAOvn6yC3aLA"
        },
        {
          name  = "DATABASE_POOL_SIZE"
          value = "35"
        },
        {
          name  = "DATA_DIR"
          value = "/app/backend/data"
        },
        {
          name  = "DATABASE_POOL_TIMEOUT"
          value = "20"
        },
        {
          name  = "RAG_EMBEDDING_MODEL"
          value = "text-embedding-3-small"
        },
        {
          name  = "DATABASE_POOL_MAX_OVERFLOW"
          value = "40"
        },
        {
          name  = "QDRANT_URI"
          value = "https://7a1bbdf2-28a8-41aa-a5c6-853bf2a20153.us-east-1-0.aws.cloud.qdrant.io:6333"
        },
        {
          name  = "ENABLE_OAUTH_SIGNUP"
          value = "true"
        },
        {
          name  = "ENABLE_LOGIN_FORM"
          value = "true"
        },
        {
          name  = "DATABASE_POOL_RECYCLE"
          value = "1800"
        },
        {
          name  = "ENABLE_SIGNUP"
          value = "true"
        },
        {
          name  = "VECTOR_DB"
          value = "qdrant"
        },
        {
          name  = "RAG_EMBEDDING_ENGINE"
          value = "openai"
        },
        {
          name  = "ADMIN_TOKEN"
          value = "sk-1058d94e5be04f27b2bdb3448412b117"
        },
        {
          name  = "ROLLBAR_ACCESS_TOKEN"
          value = "f02be04c46be43c791f5fab1415bde0c"
        },
        {
          name  = "THREAD_POOL_SIZE"
          value = "40"
        },
        # Redis configuration for horizontal scaling
        {
          name  = "WEBSOCKET_MANAGER"
          value = "redis"
        },
        {
          name  = "ENABLE_WEBSOCKET_SUPPORT"
          value = "true"
        },
        {
          name  = "UVICORN_WORKERS"
          value = "2"  # Multiple workers per instance
        },
        # Teams webhook
        {
          name  = "TEAMS_WEBHOOK_URL"
          value = "https://glondon.webhook.office.com/webhookb2/f651a310-942d-4a5e-9860-1bdf77c4eb2d@7cd05640-6cd4-4d9f-9a12-93a92969cb7f/IncomingWebhook/6a55a5a763ea471698566539c50fc2ec/e16b1a11-05ec-4ede-b1fb-77f4e5df7ea9/V2Bi1qX-90j7n8eLSoWM7VH_RMeJynrakV2-v6j4s1YOo1"
        },
        {
          name  = "ENABLE_RAG_HYBRID_SEARCH"
          value = "true"
        },
        {
          name  = "FASTEMBED_CACHE_PATH"
          value = "/app/backend/data/cache/fastembed"
        }
      ]

      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = "${var.existing_database_secret_arn}:fullurl::"
        },
        {
          name      = "PGVECTOR_DB_URL"  
          valueFrom = "${var.existing_database_secret_arn}:standard_fullurl::"
        },
        {
          name      = "WEBUI_SECRET_KEY"
          valueFrom = aws_secretsmanager_secret.webui_shared_secret.arn
        },
        # Redis configuration using secrets for better security
        {
          name      = "REDIS_URL"
          valueFrom = "${aws_secretsmanager_secret.redis_connection.arn}:url::"
        },
        {
          name      = "WEBSOCKET_REDIS_URL"
          valueFrom = "${aws_secretsmanager_secret.redis_connection.arn}:url::"
        }
      ]

      mountPoints = [
        {
          sourceVolume  = "webuidata"
          containerPath = "/app/backend/data"
          readOnly      = false
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs_scaled_logs.name
          "mode"                  = "non-blocking"
          "awslogs-create-group"  = "true"
          "max-buffer-size"       = "25m"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command = [
          "CMD-SHELL",
          "curl --silent --fail http://localhost:8080/health | jq -ne 'input.status == true' || exit 1"
        ]
        interval    = 60
        timeout     = 15
        retries     = 10
        startPeriod = 300
      }

      systemControls = []
    }
  ])

  volume {
    name = "webuidata"

    efs_volume_configuration {
      file_system_id     = var.efs_file_system_id
      root_directory     = "/"
      transit_encryption = "ENABLED"

      authorization_config {
        access_point_id = var.efs_access_point_id
        iam             = "DISABLED"
      }
    }
  }

  tags = {
    Name = "OpenWebUI Scaled Task Definition"
  }
}

# ECS Service for scaled deployment
resource "aws_ecs_service" "webui_scaled" {
  name            = var.service_name
  cluster         = var.cluster_name
  task_definition = aws_ecs_task_definition.webui_scaled.arn
  desired_count   = var.desired_count
  
  triggers = {
    redeployment = sha1(jsonencode(aws_ecs_task_definition.webui_scaled.container_definitions))
  }

  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight           = 1
    base             = 0
  }

  platform_version = "LATEST"

  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 100
  
  deployment_circuit_breaker {
    enable   = true
    rollback = false
  }

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs_scaled_sg.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.webui_targets.arn
    container_name   = "openwebui"
    container_port   = 8080
  }

  # Wait for target group to be ready
  depends_on = [aws_lb_listener.webui_listener]

  # Enable deployment circuit breaker
  deployment_controller {
    type = "ECS"
  }

  # Enable execute command for debugging
  enable_execute_command = true

  tags = {
    Name = "OpenWebUI Scaled Service"
  }

  lifecycle {
    ignore_changes = [desired_count]
  }
}
