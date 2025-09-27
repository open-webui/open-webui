# Grafana OTEL Standalone Deployment

This directory contains a complete example for deploying the Grafana OTEL monitoring stack as a standalone service, independent from the main OpenWebUI infrastructure.

**Location**: This deployment example is located in `iac/grafana-standalone/` and uses the module from `iac/modules/grafana-otel/`.

## Quick Start

### 1. Prerequisites

- AWS CLI configured with appropriate permissions
- Terraform >= 1.0 installed
- Existing ECS cluster
- VPC with private subnets
- Access to S3 bucket `gg-ai-terraform-states` for state storage

### 2. Configuration

1. Copy the example variables file:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. Edit `terraform.tfvars` with your environment values:
   ```hcl
   # Required: Update these values for your environment
   vpc_id = "vpc-your-vpc-id"
   private_subnet_ids = ["subnet-12345", "subnet-67890"]
   cluster_name = "your-ecs-cluster"
   
   # Optional: Customize as needed
   grafana_admin_password = "your-secure-password"
   allowed_cidr_blocks = ["your-vpn-cidr/24"]
   ```

### 3. Deploy

```bash
# Initialize Terraform with remote backend
terraform init

# Review the plan
terraform plan

# Deploy the infrastructure
terraform apply
```

**Note**: If you encounter AWS credential errors during `terraform init`, ensure your AWS CLI session is active:
```bash
# Refresh AWS credentials if needed
aws sts get-caller-identity --profile 908027381725_AdministratorAccess
```

## Remote State Backend

This deployment uses an S3 remote backend for state management with the following configuration:

```hcl
backend "s3" {
  bucket         = "gg-ai-terraform-states"
  key            = "production/grafana-monitoring/terraform.tfstate"
  region         = "us-east-1"
  profile        = "908027381725_AdministratorAccess"
  dynamodb_table = "terraform-state-locks"
  encrypt        = true
}
```

### Key Benefits:

- **Team Collaboration**: Multiple team members can work with the same state
- **State Locking**: DynamoDB table prevents concurrent modifications
- **Encryption**: State file is encrypted at rest
- **Separate State**: Independent from main OpenWebUI infrastructure state
- **Versioning**: S3 bucket versioning enables state history and recovery

### State Path Structure:

- **Main Infrastructure**: `production/gravity-ai-chat/terraform.tfstate`
- **Grafana Monitoring**: `production/grafana-monitoring/terraform.tfstate`

This separation allows independent deployment and management of the monitoring stack.

### 4. Access Grafana

After deployment, Terraform will output the access information:

```bash
# Get the Grafana URL and credentials
terraform output grafana_dashboard_url
terraform output -json grafana_admin_credentials

# Get setup instructions
terraform output -raw setup_instructions
```

## Configuration Options

### Basic Configuration

For a simple deployment with default settings:

```hcl
# terraform.tfvars
vpc_id = "vpc-12345678"
private_subnet_ids = ["subnet-12345", "subnet-67890"]
cluster_name = "my-cluster"
```

### Production Configuration

For a production deployment with custom settings:

```hcl
# terraform.tfvars
environment = "production"
name_prefix = "prod-grafana"

# Increased resources
cpu           = 2048
memory        = 4096
desired_count = 2

# Autoscaling enabled
enable_autoscaling = true
max_capacity       = 3
min_capacity       = 2

# Longer log retention
log_retention_days = 30

# Custom Grafana credentials
grafana_admin_user     = "monitoring-admin"
grafana_admin_password = "very-secure-password-123"

# Network access from specific CIDRs
allowed_cidr_blocks = [
  "192.168.1.0/24",    # Office network
  "10.100.0.0/16",     # VPN network
]

# Applications that will send telemetry
otlp_sources_security_group_ids = [
  "sg-app1-security-group",
  "sg-app2-security-group",
]
```

### Integration with Existing Service Discovery

If you have an existing service discovery namespace:

```hcl
# Use existing namespace
service_discovery_namespace_id = "ns-existing-12345"
service_name = "monitoring"
```

## Integration with Applications

After deploying Grafana, configure your applications to send telemetry data:

### 1. Add Application Security Groups

Update your `terraform.tfvars`:

```hcl
otlp_sources_security_group_ids = [
  "sg-your-app-security-group",
]
```

Then run `terraform apply` to update the security group rules.

### 2. Configure Application Environment Variables

In your application deployment (ECS task definition, Kubernetes deployment, etc.):

```bash
# OpenTelemetry configuration
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-monitor.grafana-monitoring:4317
OTEL_EXPORTER_OTLP_INSECURE=true
OTEL_SERVICE_NAME=my-application
OTEL_RESOURCE_ATTRIBUTES=service.version=1.0.0,deployment.environment=production
```

### 3. Verify Integration

```bash
# Check service discovery
nslookup otel-monitor.grafana-monitoring

# Test OTLP endpoint connectivity
curl http://otel-monitor.grafana-monitoring:4317

# Access Grafana dashboard
curl http://otel-monitor.grafana-monitoring:3000
```

## Monitoring and Maintenance

### Viewing Logs

```bash
# View Grafana container logs
aws logs tail /ecs/grafana-otel --follow

# Check ECS service events
aws ecs describe-services --cluster your-cluster --services grafana-otel
```

### Scaling

```bash
# Manual scaling (if autoscaling is disabled)
aws ecs update-service --cluster your-cluster --service grafana-otel --desired-count 2

# Update autoscaling settings via Terraform
# Edit terraform.tfvars and run terraform apply
```

### Updates

```bash
# Update to latest Grafana OTEL image
terraform apply -var="container_image=grafana/otel-lgtm:latest"

# Update configuration
# Edit terraform.tfvars and run terraform apply
```

## Troubleshooting

### Common Issues

1. **Service not starting**
   - Check CloudWatch logs for container errors
   - Verify ECS cluster has capacity
   - Check security group rules

2. **Cannot access Grafana UI**
   - Verify allowed_cidr_blocks includes your IP
   - Check VPC connectivity (VPN, bastion host)
   - Confirm service discovery is working

3. **No telemetry data**
   - Verify otlp_sources_security_group_ids
   - Check application OTLP endpoint configuration
   - Confirm network connectivity between services

### Useful Commands

```bash
# Check service status
terraform show | grep -A 10 "aws_ecs_service"

# Verify service discovery
aws servicediscovery list-services

# Check security groups
aws ec2 describe-security-groups --group-ids $(terraform output -raw security_group_id)

# View all outputs
terraform output
```

## Cleanup

To remove all resources:

```bash
terraform destroy
```

## State Management Commands

### Working with Remote State

```bash
# Initialize with remote backend (first time setup)
terraform init

# Migrate from local to remote state (if you have existing local state)
terraform init -migrate-state

# View remote state
terraform show

# List resources in state
terraform state list

# Pull remote state to local (for inspection)
terraform state pull > current-state.json

# Check state lock status
aws dynamodb describe-table --table-name terraform-state-locks --profile 908027381725_AdministratorAccess
```

### State Recovery and Backup

```bash
# Download current state from S3
aws s3 cp s3://gg-ai-terraform-states/production/grafana-monitoring/terraform.tfstate ./backup-state.tfstate --profile 908027381725_AdministratorAccess

# List state versions (if bucket versioning is enabled)
aws s3api list-object-versions --bucket gg-ai-terraform-states --prefix production/grafana-monitoring/terraform.tfstate --profile 908027381725_AdministratorAccess

# Force unlock state (if locked and lock is stale)
terraform force-unlock LOCK_ID
```

## Security Considerations

- Store sensitive variables (passwords) in environment variables or use AWS Secrets Manager
- Restrict `allowed_cidr_blocks` to minimum required networks
- Use strong passwords for Grafana admin account
- Regularly update the Grafana OTEL container image
- Monitor CloudWatch logs for security events

## Cost Estimation

Default configuration (1 task, 1 vCPU, 2GB RAM):
- ECS Fargate: ~$35-50/month
- CloudWatch Logs: ~$1-5/month (depending on log volume)
- Service Discovery: ~$0.50/month

Total estimated cost: ~$40-60/month

## Support

For issues or questions:
1. Check the module documentation: `../modules/grafana-otel/README.md`
2. Review Terraform and AWS documentation
3. Check CloudWatch logs for detailed error messages
