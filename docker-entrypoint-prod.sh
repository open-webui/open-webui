#!/bin/bash
# Production entrypoint for mAI with usage tracking initialization

set -e

echo "🚀 Starting mAI production deployment..."

# Wait for database to be ready
sleep 2

# Run migrations (handled safely by the application)
echo "📊 Checking database migrations..."

# Initialize usage tracking if needed
if [ "$INIT_USAGE_TRACKING" = "true" ]; then
    echo "🔧 Initializing usage tracking..."
    cd /app/backend
    python -m open_webui.scripts.init_usage_tracking || {
        echo "⚠️  Usage tracking initialization failed (non-fatal)"
    }
fi

# Start the application
echo "✅ Starting mAI server..."
exec "$@"