# CloudWatch log group for Grafana OTEL
resource "aws_cloudwatch_log_group" "grafana_logs" {
  name              = "/ecs/grafana-otel-lgtm"
  retention_in_days = 7

  tags = {
    Name = "Grafana OTEL Logs"
  }
}

# Security Group for direct Grafana ECS access
resource "aws_security_group" "grafana_ecs_direct_sg" {
  name_prefix = "grafana-ecs-direct-"
  vpc_id      = var.vpc_id
  description = "Security group for direct Grafana OTEL ECS access"

  # Allow Grafana UI access from VPN
  ingress {
    description = "Grafana UI from VPN"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = [var.gg_vpn_cidr]
  }

  # Allow OTLP gRPC from OpenWebUI ECS tasks
  ingress {
    description     = "OTLP gRPC from OpenWebUI ECS"
    from_port       = 4317
    to_port         = 4317
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_scaled_sg.id]
  }

  # Allow OTLP HTTP from OpenWebUI ECS tasks
  ingress {
    description     = "OTLP HTTP from OpenWebUI ECS"
    from_port       = 4318
    to_port         = 4318
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_scaled_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "Grafana ECS Direct Access Security Group"
  }
}

# IAM role for Grafana ECS tasks (reuse existing execution role)
# The existing openwebui_execution_role should have sufficient permissions

# ECS Task Definition for Grafana OTEL LGTM
resource "aws_ecs_task_definition" "grafana_otel" {
  family                   = "grafana-otel-lgtm"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = aws_iam_role.openwebui_execution_role.arn
  task_role_arn           = aws_iam_role.openwebui_execution_role.arn

  container_definitions = jsonencode([
    {
      name      = "grafana-otel-lgtm"
      image     = "grafana/otel-lgtm:latest"
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
          value = "openwebui_monitoring_2024"
        },
        {
          name  = "GF_SECURITY_ADMIN_USER"
          value = "admin"
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
          "awslogs-group"         = aws_cloudwatch_log_group.grafana_logs.name
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

  tags = {
    Name = "Grafana OTEL LGTM Task Definition"
  }
}

# ECS Service for Grafana OTEL
resource "aws_ecs_service" "grafana_otel" {
  name            = "grafana-otel-lgtm"
  cluster         = var.cluster_name
  task_definition = aws_ecs_task_definition.grafana_otel.arn
  desired_count   = 1

  triggers = {
    redeployment = sha1(jsonencode(aws_ecs_task_definition.grafana_otel.container_definitions))
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
    security_groups  = [aws_security_group.grafana_ecs_direct_sg.id]
    assign_public_ip = false
  }

  # No load balancer - using direct service discovery
  service_registries {
    registry_arn = aws_service_discovery_service.otel_monitor.arn
  }

  # Enable deployment circuit breaker
  deployment_controller {
    type = "ECS"
  }

  # Enable execute command for debugging
  enable_execute_command = true

  tags = {
    Name = "Grafana OTEL LGTM Service"
  }

  lifecycle {
    ignore_changes = [desired_count]
  }
}

# Auto Scaling Target for Grafana (optional, keep at 1 for now)
resource "aws_appautoscaling_target" "grafana_target" {
  max_capacity       = 2
  min_capacity       = 1
  resource_id        = "service/${var.cluster_name}/grafana-otel-lgtm"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"

  depends_on = [aws_ecs_service.grafana_otel]
}

# Auto Scaling Policy - Scale Up based on CPU (conservative for monitoring)
resource "aws_appautoscaling_policy" "grafana_scale_up" {
  name               = "grafana-scale-up"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.grafana_target.resource_id
  scalable_dimension = aws_appautoscaling_target.grafana_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.grafana_target.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 80.0

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }

    scale_out_cooldown = 600  # 10 minutes
    scale_in_cooldown  = 300  # 5 minutes
  }
}