# NBP Exchange Rate Service

A FastAPI microservice that provides USD/PLN exchange rates for mAI usage tracking.

## Features

- Fetches real-time USD/PLN rates from NBP (Narodowy Bank Polski) API
- Mock mode for development and testing
- In-memory caching to reduce API calls
- RESTful API endpoints
- Docker-ready deployment

## API Endpoints

### Health Check
```
GET /health
```
Returns service health status and current mode (mock/live).

### Get Current Rate
```
GET /api/usd-pln-rate
```
Returns the current USD/PLN exchange rate.

### Get Rate by Date
```
GET /api/usd-pln-rate?date=2025-01-15
```
Returns the USD/PLN rate for a specific date (YYYY-MM-DD format).

### Get Rate Range
```
GET /api/usd-pln-rate/range?start_date=2025-01-01&end_date=2025-01-07
```
Returns USD/PLN rates for a date range.

### Clear Cache
```
POST /api/cache/clear
```
Clears the exchange rate cache (admin endpoint).

## Development

### Local Setup

1. Install dependencies:
```bash
cd nbp-service
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export MOCK_MODE=true
export PORT=8001
```

3. Run the service:
```bash
uvicorn app.main:app --reload --port 8001
```

### Docker

Build and run with Docker:
```bash
docker build -t mai-nbp-service .
docker run -p 8001:8001 -e MOCK_MODE=true mai-nbp-service
```

### Testing

Run tests:
```bash
pytest tests/
```

## Mock Mode

When `MOCK_MODE=true`, the service returns realistic mock exchange rates:
- Base rate: 4.00 PLN per USD
- Variation: ±0.10 PLN based on date
- Excludes weekends (NBP doesn't publish weekend rates)

## Production Configuration

For production deployment:
1. Set `MOCK_MODE=false`
2. Configure Redis for distributed caching
3. Set appropriate CORS origins
4. Add authentication for admin endpoints

## Integration with mAI

The NBP service is used by mAI's batch processor to convert USD costs to PLN:
- Daily batch runs at 13:00 CET/CEST
- Fetches exchange rate for billing calculations
- Caches rates to minimize external API calls