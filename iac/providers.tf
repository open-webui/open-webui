terraform {
  required_version = ">= 1.0"
  
  # Remote state backend configuration
  backend "s3" {
    bucket         = "gg-ai-terraform-states"
    key            = "production/gravity-ai-chat/terraform.tfstate"
    region         = "us-east-1"
    profile        = "908027381725_AdministratorAccess"
    dynamodb_table = "terraform-state-locks"
    encrypt        = true
  }
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
  
  default_tags {
    tags = {
      Project     = "Gravity-AI-Chat-Horizontal-Scaling"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Maintainer  = "loi.tra@gravityglobal.com"
    }
  }
}
