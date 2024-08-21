variable "aws_region" {
  description = "The AWS region to build the AMI in."
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "The instance type to use."
  type        = string
  default     = "t3.micro"
}

variable "ami_name" {
  description = "The name of the AMI to be created."
  type        = string
  default     = "OpenWebUI-AMI-{{timestamp}}"
}

variable "ami_description" {
  description = "Description of the AMI."
  type        = string
  default     = "AMI with Open WebUI installed"
}

variable "key_name" {
  description = "The name of the SSH key pair to use."
  default     = "miai-dev-imagine"
}

variable "private_key_path" {
  description = "The path to the private key file associated with the SSH key pair."
  default     = "../terraform/secrets/miai-dev-imagine.pem"
}

packer {
  required_plugins {
    amazon = {
      source  = "github.com/hashicorp/amazon"
      version = "~> 1"
    }
    ansible = {
      version = "~> 1"
      source = "github.com/hashicorp/ansible"
    }
  }
  
}

data "amazon-ami" "latest_ubuntu" {
  region = var.aws_region
  filters = {
      virtualization-type = "hvm"
      name = "ubuntu/images/*ubuntu-jammy-22.04-amd64-server-*"
      root-device-type = "ebs"
  }
  owners = ["099720109477"]
  most_recent = true
}


source "amazon-ebs" "open-webui" {
  region         = var.aws_region
  instance_type  = var.instance_type
  source_ami     = data.amazon-ami.latest_ubuntu.id
  ssh_username   = "ubuntu"
  ami_name       = var.ami_name
  ami_description = var.ami_description

  ssh_keypair_name      = var.key_name
  ssh_private_key_file  = var.private_key_path
}

build {
  sources = ["source.amazon-ebs.open-webui"]

  provisioner "breakpoint" {
    disable = false
    note    = "Shall we continue with the build?"
  }

  provisioner "ansible" {
    playbook_file = "ansible/playbook-v2.yml"
    inventory_file = "ansible/inventory.ini"
  }
}
