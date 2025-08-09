#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

echo "🔍 DEBUG: Checking for RDS certificate at startup..."
if [ -f "/root/.postgresql/root.crt" ]; then
    echo "✅ Certificate found: $(ls -la /root/.postgresql/root.crt)"
    echo "🔧 Certificate details: $(file /root/.postgresql/root.crt)"
else
    echo "❌ Certificate NOT found at /root/.postgresql/root.crt"
    echo "📂 Contents of /root/.postgresql/: $(ls -la /root/.postgresql/ 2>/dev/null || echo 'Directory does not exist')"
fi

echo "INFO: Generating temporary IAM database auth token..."

# Define the application entrypoint module path
APP_MODULE="open_webui.main:app"

# Check if the DATABASE_URL environment variable contains a JSON object.
# This is how we differentiate between a local sqlite string and the AWS Secrets Manager JSON.
if [[ "$DATABASE_URL" == *{* ]]; then
  echo "INFO: Production environment detected. Parsing DATABASE_URL from JSON secret."
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
  
  # Debug logging to understand what we're working with
  echo "DEBUG: DB_USER='${DB_USER}'"
  echo "DEBUG: DB_HOST='${DB_HOST}'" 
  echo "DEBUG: DB_PORT='${DB_PORT}'"
  echo "DEBUG: DB_NAME='${DB_NAME}'"
  echo "DEBUG: AWS_REGION='${AWS_REGION}'"
  echo "DEBUG: IAM_AUTH_TOKEN length: ${#IAM_AUTH_TOKEN} characters"
  echo "DEBUG: First 50 chars of token: ${IAM_AUTH_TOKEN:0:50}..."
  
  # URL-encode the IAM auth token since it contains special characters (&, =, ?, etc.)
  # that can break URL parsing when used as a password in the connection string
  ENCODED_TOKEN=$(python3 -c "import urllib.parse; print(urllib.parse.quote('${IAM_AUTH_TOKEN}', safe=''))")
  echo "DEBUG: ENCODED_TOKEN length: ${#ENCODED_TOKEN} characters"
  echo "DEBUG: First 50 chars of encoded token: ${ENCODED_TOKEN:0:50}..."
  
  # Construct the final DATABASE_URL with the URL-encoded token as the password
  export DATABASE_URL="postgresql://${DB_USER}:${ENCODED_TOKEN}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
  echo "DEBUG: Final DATABASE_URL (with token redacted): postgresql://${DB_USER}:[REDACTED]@${DB_HOST}:${DB_PORT}/${DB_NAME}"
else
  echo "INFO: Local development environment detected. Skipping IAM token generation."
  # In this case, we just use the DATABASE_URL as-is (e.g., "sqlite:///data/db.sqlite")
fi

# Construct the final DATABASE_URL with the temporary token as the password
# The application will use this environment variable to connect
## export DATABASE_URL="postgresql://${DB_USER}:${IAM_AUTH_TOKEN}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
## echo "INFO: Starting Open-WebUI..."
# Execute the original command passed to the container (e.g., the web server)
##exec "$@"

# Check if we are in debugging mode.
# The `debugpy` command is added only if this variable is set.
if [ "$DEBUGGER" = "True" ]; then
    echo "INFO: Starting application with debugger attached on module: $APP_MODULE"
    # The --wait-for-client flag pauses the application until your debugger attaches.
    # The --listen flag exposes the debugger on all container network interfaces on port 5678.
    exec python -m debugpy --wait-for-client --listen 0.0.0.0:5678 -m uvicorn $APP_MODULE --host 0.0.0.0 --port 8080 --reload
else
    echo "INFO: Starting application without debugger on module: $APP_MODULE"
    # This is the standard production startup command
    exec uvicorn $APP_MODULE --host 0.0.0.0 --port 8080
fi
