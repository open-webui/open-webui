# NBP Service Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run the service
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]