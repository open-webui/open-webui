#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

echo "INFO: Generating temporary IAM database auth token..."

# These variables are already set in your ECS Task Definition from the owui-stack
# We just need the database name, which is typically 'postgres' by default for Aurora
DB_USER=$(echo "$DATABASE_URL" | jq -r .username)
DB_NAME=$(echo "$DATABASE_URL" | jq -r .dbname)

# The AWS_REGION is automatically available in the ECS environment
# Generate the temporary auth token using the ECS Task Role's permissions
IAM_AUTH_TOKEN=$(aws rds generate-db-auth-token \
  --hostname "$DB_HOST" \
  --port "$DB_PORT" \
  --username "$DB_USER" \
  --region "$AWS_REGION")

echo "INFO: Successfully generated IAM auth token."

# Construct the final DATABASE_URL with the temporary token as the password
# The application will use this environment variable to connect
export DATABASE_URL="postgresql://${DB_USER}:${IAM_AUTH_TOKEN}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

echo "INFO: Starting Open-WebUI..."

# Execute the original command passed to the container (e.g., the web server)
exec "$@"
