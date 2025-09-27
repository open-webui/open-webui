# Local values for consistent naming
locals {
  name_prefix = var.name_prefix
  common_tags = merge(
    {
      Environment = var.environment
      Module      = "grafana-otel"
      ManagedBy   = "terraform"
    },
    var.tags
  )
}

# Service Discovery Namespace (create if not provided)
resource "aws_service_discovery_private_dns_namespace" "grafana" {
  count = var.service_discovery_namespace_id == "" ? 1 : 0
  
  name = var.service_discovery_namespace_name
  vpc  = var.vpc_id
  
  description = "Service discovery namespace for Grafana OTEL monitoring"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-namespace"
  })
}


# Service Discovery Service for Grafana
resource "aws_service_discovery_service" "grafana" {
  name = var.service_name

  dns_config {
    namespace_id = var.service_discovery_namespace_id != "" ? var.service_discovery_namespace_id : aws_service_discovery_private_dns_namespace.grafana[0].id

    dns_records {
      ttl  = 60
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }

  description = "Grafana OTEL LGTM monitoring stack service discovery"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-service-discovery"
  })
}

# CloudWatch Log Group for Grafana
resource "aws_cloudwatch_log_group" "grafana" {
  name              = "/ecs/${local.name_prefix}"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-logs"
  })
}

# Security Group for Grafana ECS Tasks
resource "aws_security_group" "grafana" {
  name_prefix = "${local.name_prefix}-"
  vpc_id      = var.vpc_id
  description = "Security group for Grafana OTEL ECS tasks"

  # Allow Grafana UI access from specified CIDR blocks
  ingress {
    description = "Grafana UI access"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  # Allow OTLP gRPC from specified security groups
  dynamic "ingress" {
    for_each = length(var.otlp_sources_security_group_ids) > 0 ? [1] : []
    content {
      description     = "OTLP gRPC from sources"
      from_port       = 4317
      to_port         = 4317
      protocol        = "tcp"
      security_groups = var.otlp_sources_security_group_ids
    }
  }

  # Allow OTLP HTTP from specified security groups
  dynamic "ingress" {
    for_each = length(var.otlp_sources_security_group_ids) > 0 ? [1] : []
    content {
      description     = "OTLP HTTP from sources"
      from_port       = 4318
      to_port         = 4318
      protocol        = "tcp"
      security_groups = var.otlp_sources_security_group_ids
    }
  }

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-security-group"
  })
}

# IAM Role for ECS Task Execution
resource "aws_iam_role" "grafana_execution" {
  name = "${local.name_prefix}-execution-role"
  
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
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-execution-role"
  })
}

# Attach AWS managed ECS execution policy
resource "aws_iam_role_policy_attachment" "grafana_execution_policy" {
  role       = aws_iam_role.grafana_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Additional policy for CloudWatch logs
resource "aws_iam_role_policy" "grafana_logs_policy" {
  name = "${local.name_prefix}-logs-policy"
  role = aws_iam_role.grafana_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.grafana.arn}:*"
      }
    ]
  })
}

# ECS Task Definition for Grafana OTEL LGTM
resource "aws_ecs_task_definition" "grafana" {
  family                   = local.name_prefix
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.grafana_execution.arn
  task_role_arn           = aws_iam_role.grafana_execution.arn

  container_definitions = jsonencode([
    {
      name      = "grafana-otel-lgtm"
      image     = var.container_image
      cpu       = 0
      essential = true

      portMappings = [
        {
          containerPort = 3000
          hostPort      = 3000
          protocol      = "tcp"
          name          = "grafana-ui"
          appProtocol   = "http"
        },
        {
          containerPort = 4317
          hostPort      = 4317
          protocol      = "tcp"
          name          = "otlp-grpc"
        },
        {
          containerPort = 4318
          hostPort      = 4318
          protocol      = "tcp"
          name          = "otlp-http"
          appProtocol   = "http"
        }
      ]

      environment = [
        {
          name  = "GF_SECURITY_ADMIN_PASSWORD"
          value = var.grafana_admin_password
        },
        {
          name  = "GF_SECURITY_ADMIN_USER"
          value = var.grafana_admin_user
        },
        {
          name  = "GF_INSTALL_PLUGINS"
          value = ""
        },
        {
          name  = "GF_FEATURE_TOGGLES_ENABLE"
          value = "traceqlEditor"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.grafana.name
          "mode"                  = "non-blocking"
          "awslogs-create-group"  = "true"
          "max-buffer-size"       = "25m"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "grafana"
        }
      }

      healthCheck = {
        command = [
          "CMD-SHELL",
          "curl --silent --fail http://localhost:3000/api/health || exit 1"
        ]
        interval    = 30
        timeout     = 10
        retries     = 3
        startPeriod = 60
      }

      systemControls = []
    }
  ])

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-task-definition"
  })
}

# ECS Service for Grafana
resource "aws_ecs_service" "grafana" {
  name            = local.name_prefix
  cluster         = var.cluster_name
  task_definition = aws_ecs_task_definition.grafana.arn
  desired_count   = var.desired_count

  triggers = {
    redeployment = sha1(jsonencode(aws_ecs_task_definition.grafana.container_definitions))
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
    subnets = var.private_subnet_ids
    security_groups = concat(
      [aws_security_group.grafana.id],
      var.additional_security_group_ids
    )
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.grafana.arn
  }

  deployment_controller {
    type = "ECS"
  }

  enable_execute_command = var.enable_execute_command

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-service"
  })

  lifecycle {
    ignore_changes = [desired_count]
  }
}

# Auto Scaling Target (if enabled)
resource "aws_appautoscaling_target" "grafana" {
  count = var.enable_autoscaling ? 1 : 0
  
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${var.cluster_name}/${aws_ecs_service.grafana.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"

  depends_on = [aws_ecs_service.grafana]

  tags = local.common_tags
}

# Auto Scaling Policy (if enabled)
resource "aws_appautoscaling_policy" "grafana_scale_up" {
  count = var.enable_autoscaling ? 1 : 0
  
  name               = "${local.name_prefix}-scale-up"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.grafana[0].resource_id
  scalable_dimension = aws_appautoscaling_target.grafana[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.grafana[0].service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = var.cpu_target_value

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }

    scale_out_cooldown = 600  # 10 minutes
    scale_in_cooldown  = 300  # 5 minutes
  }
}
