# Additional Security Group Rules for Integration
# This file manages access from our new ECS service to existing infrastructure

# Get the RDS security group
data "aws_security_group" "rds_sg" {
  id = var.rds_security_group_id
}

# Get the EFS security groups
data "aws_security_group" "efs_sg_1" {
  id = var.efs_security_group_1_id
}

data "aws_security_group" "efs_sg_2" {
  id = var.efs_security_group_2_id
}

# Allow new ECS service to access RDS PostgreSQL
resource "aws_security_group_rule" "ecs_to_rds" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.ecs_scaled_sg.id
  security_group_id        = data.aws_security_group.rds_sg.id
  description              = "Allow scaled ECS service to access RDS PostgreSQL"
}

# Allow new ECS service to access EFS (first security group)
resource "aws_security_group_rule" "ecs_to_efs_1" {
  type                     = "ingress"
  from_port                = 2049
  to_port                  = 2049
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.ecs_scaled_sg.id
  security_group_id        = data.aws_security_group.efs_sg_1.id
  description              = "Allow scaled ECS service to access EFS (sg1)"
}

# Allow new ECS service to access EFS (second security group)
resource "aws_security_group_rule" "ecs_to_efs_2" {
  type                     = "ingress"
  from_port                = 2049
  to_port                  = 2049
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.ecs_scaled_sg.id
  security_group_id        = data.aws_security_group.efs_sg_2.id
  description              = "Allow scaled ECS service to access EFS (sg2)"
}

# Get the pipelines security group
data "aws_security_group" "pipelines_sg" {
  id = var.pipelines_security_group_id
}

# Allow new ECS service to access pipelines service
resource "aws_security_group_rule" "ecs_to_pipelines" {
  type                     = "ingress"
  from_port                = 9099
  to_port                  = 9099
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.ecs_scaled_sg.id
  security_group_id        = data.aws_security_group.pipelines_sg.id
  description              = "Allow scaled ECS service to access pipelines service"
}

# Get the docling-serve security group
data "aws_security_group" "docling_serve_sg" {
  id = var.docling_serve_security_group_id
}

# Allow new ECS service to access docling-serve service
resource "aws_security_group_rule" "ecs_to_docling_serve" {
  type                     = "ingress"
  from_port                = 5001
  to_port                  = 5001
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.ecs_scaled_sg.id
  security_group_id        = data.aws_security_group.docling_serve_sg.id
  description              = "Allow scaled ECS service to access docling-serve service"
}

# Get the mcpo security group
data "aws_security_group" "mcpo_sg" {
  id = var.mcpo_security_group_id
}

# Allow new ECS service to access mcpo service
resource "aws_security_group_rule" "ecs_to_mcpo" {
  type                     = "ingress"
  from_port                = 7000
  to_port                  = 7000
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.ecs_scaled_sg.id
  security_group_id        = data.aws_security_group.mcpo_sg.id
  description              = "Allow scaled ECS service to access mcpo service"
}

# Get the jupyter-notebook security group
data "aws_security_group" "jupyter_notebook_sg" {
  id = var.jupyter_notebook_security_group_id
}

# Allow new ECS service to access jupyter-notebook service
resource "aws_security_group_rule" "ecs_to_jupyter_notebook" {
  type                     = "ingress"
  from_port                = 8888
  to_port                  = 8888
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.ecs_scaled_sg.id
  security_group_id        = data.aws_security_group.jupyter_notebook_sg.id
  description              = "Allow scaled ECS service to access jupyter-notebook service"
}
