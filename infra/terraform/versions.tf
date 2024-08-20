terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.9.0"
    }
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      "TerraformManaged" = "true",
      "BusinessUnit"     = "PER1",
      "Snapshot"         = "true"
    }
  }
}
