FROM python:3.11-slim

WORKDIR /app/backend

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Make scripts executable
RUN chmod +x start.sh

# Create empty CHANGELOG.md
RUN touch /app/backend/open_webui/CHANGELOG.md

# Set environment variables
ENV HOST=0.0.0.0
ENV PORT=8080

# Create data directory
RUN mkdir -p /app/backend/data

# Run the application
CMD ["sh", "start.sh"]
