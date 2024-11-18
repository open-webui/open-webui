# D3 Open WebUI Updates

## New Features
- AWS Bedrock Integration: Added support for AWS Bedrock, including:
    - Support for Claude 3.5 Sonnet model
    - AWS Bedrock client initialization
    - Region configuration

## Requirements Added
- aws-requests-auth: AWS request signing

## Environment Variables
``` bash
# AWS Bedrock Configuration
BEDROCK_REGION=us-east-1  # Default AWS region
ENABLE_BEDROCK_API=true   # Enable/disable Bedrock integration
AWS_ACCESS_KEY_ID=         # AWS credentials
AWS_SECRET_ACCESS_KEY=     # AWS credentials  
AWS_SESSION_TOKEN=         # Optional session token
```

## API Changes
- New /bedrock API endpoint mounted
- Added Bedrock chat completion endpoint at /chat/completions
- Response conversion between Bedrock and OpenAI formats

## Frontend Updates
- Chat interface handles Bedrock responses

## Configuration
New AppConfig settings for Bedrock
```bash
ENABLE_BEDROCK_API: bool = True
BEDROCK_REGION: str = "us-east-1"
```

## What next
- Files are not being shared to Claude properly. The chunking impacts the response from Claude.
- Making the AWS credentials passing more salient. Passing env variables for AWS access is not scalable.