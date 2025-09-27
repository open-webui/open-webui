# Grafana OTEL Module

This Terraform module deploys a standalone Grafana OTEL LGTM (Logs, Grafana, Tempo, Mimir) stack on AWS ECS Fargate for OpenTelemetry monitoring and observability.

## Features

- **Complete OTEL Stack**: Grafana + Prometheus + Tempo + Loki in a single container
- **ECS Fargate Deployment**: Serverless, scalable container deployment
- **Service Discovery**: Automatic DNS registration for easy service connectivity
- **Security**: Configurable security groups and network access controls
- **Auto Scaling**: Optional ECS autoscaling based on CPU utilization
- **CloudWatch Integration**: Structured logging with configurable retention

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Applications  │───▶│   OTLP Endpoints │───▶│    Grafana UI   │
│                 │    │   (4317/4318)    │    │     (3000)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  ECS Fargate     │
                       │  - Grafana       │
                       │  - Prometheus    │
                       │  - Tempo         │
                       │  - Loki          │
                       └──────────────────┘
```

## Usage

### Basic Usage

```hcl
module "grafana_monitoring" {
  source = "./modules/grafana-otel"
  
  # Core Infrastructure
  vpc_id             = "vpc-12345678"
  private_subnet_ids = ["subnet-12345678", "subnet-87654321"]
  cluster_name       = "my-ecs-cluster"
  
  # Network Access
  allowed_cidr_blocks = ["10.0.0.0/8", "192.168.0.0/16"]
  
  # Optional: OpenTelemetry Sources
  otlp_sources_security_group_ids = ["sg-app1", "sg-app2"]
  
  tags = {
    Environment = "production"
    Project     = "monitoring"
  }
}
```

### Advanced Usage with Existing Service Discovery

```hcl
module "grafana_monitoring" {
  source = "./modules/grafana-otel"
  
  # Core Infrastructure
  vpc_id             = "vpc-12345678"
  private_subnet_ids = ["subnet-12345678", "subnet-87654321"]
  cluster_name       = "my-ecs-cluster"
  
  # Use existing service discovery namespace
  service_discovery_namespace_id = "ns-12345678"
  service_name                   = "monitoring"
  
  # Custom configuration
  environment         = "staging"
  cpu                = 2048
  memory             = 4096
  desired_count      = 2
  enable_autoscaling = true
  max_capacity       = 3
  
  # Custom Grafana credentials
  grafana_admin_user     = "monitoring-admin"
  grafana_admin_password = "secure-password-123"
  
  tags = {
    Environment = "staging"
    Project     = "monitoring"
  }
}
```

## Requirements

| Name | Version |
|------|---------|
| terraform | >= 1.0 |
| aws | >= 5.0 |

## Providers

| Name | Version |
|------|---------|
| aws | >= 5.0 |

## Resources Created

- **ECS Service & Task Definition**: Fargate-based Grafana OTEL LGTM container
- **Service Discovery**: DNS service registration for easy connectivity
- **Security Groups**: Network access controls for Grafana UI and OTLP endpoints
- **IAM Roles**: Execution role with necessary permissions
- **CloudWatch Log Group**: Centralized logging with configurable retention
- **Auto Scaling** (optional): CPU-based scaling for high availability

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| vpc_id | VPC ID where Grafana will be deployed | `string` | n/a | yes |
| private_subnet_ids | Private subnet IDs for Grafana ECS tasks | `list(string)` | n/a | yes |
| cluster_name | ECS cluster name where Grafana will be deployed | `string` | n/a | yes |
| aws_region | AWS region for deployment | `string` | `"us-east-1"` | no |
| allowed_cidr_blocks | CIDR blocks allowed to access Grafana UI | `list(string)` | `["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]` | no |
| otlp_sources_security_group_ids | Security group IDs that should be allowed to send OTLP data | `list(string)` | `[]` | no |
| grafana_admin_user | Grafana admin username | `string` | `"admin"` | no |
| grafana_admin_password | Grafana admin password | `string` | `"openwebui_monitoring_2024"` | no |
| cpu | CPU units for Grafana task | `number` | `1024` | no |
| memory | Memory (MB) for Grafana task | `number` | `2048` | no |
| enable_autoscaling | Enable ECS autoscaling for Grafana | `bool` | `true` | no |

See [variables.tf](./variables.tf) for complete list of inputs.

## Outputs

| Name | Description |
|------|-------------|
| grafana_dashboard_url | Grafana dashboard URL |
| grafana_admin_credentials | Grafana admin login credentials (sensitive) |
| otlp_endpoints | OpenTelemetry OTLP endpoints (gRPC and HTTP) |
| security_group_id | Security group ID for Grafana tasks |
| setup_instructions | Complete setup and integration instructions |

See [outputs.tf](./outputs.tf) for complete list of outputs.

## Integration with Applications

To send telemetry data from your applications to this Grafana instance:

### 1. Add Application Security Groups

```hcl
module "grafana_monitoring" {
  source = "./modules/grafana-otel"
  # ... other configuration
  
  otlp_sources_security_group_ids = [
    aws_security_group.my_app.id,
    aws_security_group.another_app.id
  ]
}
```

### 2. Configure Application Environment Variables

```bash
# In your application environment
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-monitor.my-namespace:4317
OTEL_EXPORTER_OTLP_INSECURE=true
OTEL_SERVICE_NAME=my-application
```

### 3. Verify Integration

```bash
# Check service discovery
nslookup otel-monitor.my-namespace

# Test OTLP endpoint
curl http://otel-monitor.my-namespace:4317

# Access Grafana UI
curl http://otel-monitor.my-namespace:3000
```

## Monitoring and Troubleshooting

### Access Grafana Dashboard

1. Connect to your VPC (via VPN or bastion host)
2. Navigate to the Grafana URL from module outputs
3. Login with the admin credentials
4. Explore pre-configured data sources:
   - **Prometheus**: Metrics and monitoring
   - **Tempo**: Distributed tracing
   - **Loki**: Log aggregation

### Common Issues

- **Connection refused**: Check security group rules and CIDR blocks
- **Service not starting**: Check CloudWatch logs and ECS service events
- **No telemetry data**: Verify OTLP source security groups and endpoints

### Useful Commands

```bash
# Check ECS service status
aws ecs describe-services --cluster my-cluster --services grafana-otel

# View logs
aws logs tail /ecs/grafana-otel --follow

# Check service discovery
aws servicediscovery list-services --filters Name=NAMESPACE_ID,Values=ns-12345678
```

## Security Considerations

- Grafana admin password is configurable but stored in Terraform state
- Consider using AWS Secrets Manager for production passwords
- Network access is controlled via security groups and CIDR blocks
- ECS tasks run with least privilege IAM permissions

## Cost Optimization

- Default configuration uses 1 vCPU and 2GB RAM (estimated $35-50/month)
- Enable autoscaling to handle traffic spikes efficiently
- Adjust log retention period to control CloudWatch costs
- Consider using Spot instances for non-production environments

## License

This module is part of the OpenWebUI infrastructure project.
