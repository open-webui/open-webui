export CORS_ALLOW_ORIGIN="http://localhost:5173;http://localhost:8080"
PORT="${PORT:-8080}"

# Load OpenAI API configuration from environment variables if set
# These can be overridden by exporting them before running this script
# Example: export OPENAI_API_KEY="sk-..." && export OPENAI_API_BASE_URL="https://api.openai.com/v1" && ./dev.sh
if [ -n "$OPENAI_API_KEY" ]; then
    export OPENAI_API_KEY="$OPENAI_API_KEY"
fi
if [ -n "$OPENAI_API_BASE_URL" ]; then
    export OPENAI_API_BASE_URL="$OPENAI_API_BASE_URL"
fi

uvicorn open_webui.main:app --port $PORT --host localhost --forwarded-allow-ips '*' --reload