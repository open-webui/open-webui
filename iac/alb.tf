# Security group for ALB
resource "aws_security_group" "alb_sg" {
  name_prefix = "openwebui-alb-"
  vpc_id      = var.vpc_id
  description = "Security group for OpenWebUI Internal ALB"

  # Allow HTTP traffic from Entra proxy and VPN
  ingress {
    description = "HTTP from Entra Proxy"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = [var.entra_proxy_ip]
  }

  ingress {
    description = "HTTP from GG VPN"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = [var.gg_vpn_cidr]
  }

  egress {
    description = "To ECS tasks"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["192.168.144.0/23"]  # VPC CIDR
  }

  tags = {
    Name = "OpenWebUI ALB Security Group"
  }
}

# Internal Application Load Balancer
resource "aws_lb" "webui_alb" {
  name               = "openwebui-internal-alb"
  internal           = true
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets            = var.private_subnet_ids

  enable_deletion_protection = false

  # Access logs (optional)
  access_logs {
    bucket  = aws_s3_bucket.alb_logs.bucket
    prefix  = "openwebui-alb"
    enabled = true
  }

  tags = {
    Name = "OpenWebUI Internal ALB"
  }
}

# S3 bucket for ALB access logs
resource "aws_s3_bucket" "alb_logs" {
  bucket        = "openwebui-alb-logs-${random_id.bucket_suffix.hex}"
  force_destroy = true

  tags = {
    Name = "OpenWebUI ALB Access Logs"
  }
}

resource "random_id" "bucket_suffix" {
  byte_length = 8
}

resource "aws_s3_bucket_versioning" "alb_logs_versioning" {
  bucket = aws_s3_bucket.alb_logs.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "alb_logs_encryption" {
  bucket = aws_s3_bucket.alb_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "alb_logs_lifecycle" {
  bucket = aws_s3_bucket.alb_logs.id

  rule {
    id     = "log_lifecycle"
    status = "Enabled"

    filter {
      prefix = "openwebui-alb/"
    }

    expiration {
      days = 30
    }

    noncurrent_version_expiration {
      noncurrent_days = 7
    }
  }
}

# ALB bucket policy for access logs
resource "aws_s3_bucket_policy" "alb_logs_policy" {
  bucket = aws_s3_bucket.alb_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::127311923021:root"  # US East 1 ELB service account
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.alb_logs.arn}/openwebui-alb/AWSLogs/${data.aws_caller_identity.current.account_id}/*"
      },
      {
        Effect = "Allow"
        Principal = {
          Service = "delivery.logs.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.alb_logs.arn}/openwebui-alb/AWSLogs/${data.aws_caller_identity.current.account_id}/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-acl" = "bucket-owner-full-control"
          }
        }
      },
      {
        Effect = "Allow"
        Principal = {
          Service = "delivery.logs.amazonaws.com"
        }
        Action   = "s3:GetBucketAcl"
        Resource = aws_s3_bucket.alb_logs.arn
      }
    ]
  })
}

data "aws_caller_identity" "current" {}

# Target group for ECS tasks
resource "aws_lb_target_group" "webui_targets" {
  name     = "openwebui-targets"
  port     = 8080
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 3
    unhealthy_threshold = 10
    timeout             = 15
    interval            = 60
    path                = "/health"
    matcher             = "200"
    port                = "traffic-port"
    protocol            = "HTTP"
  }

  # Enable sticky sessions for session affinity
  stickiness {
    type            = "lb_cookie"
    cookie_duration = 86400  # 24 hours
    enabled         = true
  }

  tags = {
    Name = "OpenWebUI Target Group"
  }

  # Important: Allow the target group to be recreated
  lifecycle {
    create_before_destroy = true
  }
}

# ALB listener
resource "aws_lb_listener" "webui_listener" {
  load_balancer_arn = aws_lb.webui_alb.arn
  port              = "8080"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.webui_targets.arn
  }

  tags = {
    Name = "OpenWebUI ALB Listener"
  }
} 