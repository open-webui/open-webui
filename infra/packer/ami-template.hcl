packer {
  required_plugins {
    amazon = {
      version = ">= 1.0.2"
      source  = "github.com/hashicorp/amazon"
    }
  }
}

data "aws_ami" "latest_ubuntu" {
  owners      = ["099720109477"]  # Canonical's account ID for official Ubuntu images
  most_recent = true
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

source "amazon-ebs" "open-webui" {
  region               = "us-west-2"  # Specify your desired AWS region
  instance_type       = "t2.micro"    # Choose an instance type
  source_ami          = data.aws_ami.latest_ubuntu.id  # Use the fetched Ubuntu AMI ID
  ssh_username        = "ubuntu"      # Change to your base image’s username
  ami_name            = "OpenWebUI-AMI-{{timestamp}}"
  ami_description     = "AMI with Open WebUI installed"
}

build {
  sources = ["source.amazon-ebs.open-webui"]

  provisioner "ansible" {
    playbook_file = "packer/ansible/playbook.yml"
    inventory_file = "packer/ansible/inventory.ini"
  }
}
