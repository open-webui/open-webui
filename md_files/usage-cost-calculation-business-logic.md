Oczywiście. Oto w pełni zaktualizowana i poprawiona wersja dokumentu analitycznego. Zmiany odzwierciedlają obecny, działający stan systemu, który wspólnie zdiagnozowaliśmy i naprawiliśmy.

### Canvas: `Updated - mAI Usage Cost Calculation - Business Logic Analysis.md`

# mAI Usage Cost Calculation - Business Logic Analysis

## Executive Summary

This document analyzes the complete business logic workflow for total cost calculation in the mAI Admin Panel usage tab, from raw OpenRouter API data to the final displayed costs in USD and PLN. The system is built on a robust, multi-tier architecture that includes a dedicated microservice for currency exchange rate retrieval.

## System Architecture Overview

The mAI usage tracking system follows a **multi-tier architecture**:

1.  **Frontend**: Svelte components displaying usage statistics
2.  **API Layer**: FastAPI routers handling HTTP requests
3.  **Service Layer**: Business logic and cost calculations
4.  **Repository Layer**: Database operations (SQLite + InfluxDB)
5.  **External Services**: A dedicated **NBP Microservice** which proxies and caches requests to the Polish Central Bank API.

## Complete Cost Calculation Workflow

### 1\. Data Input Sources

#### OpenRouter Webhook Data

  - **Endpoint**: `POST /api/v1/usage-tracking/webhook/openrouter-usage`
  - **Raw Fields**:
      - `tokens_prompt`, `tokens_completion` (input/output tokens)
      - `usage` (raw cost in USD)
      - `model` (AI model identifier)
      - `external_user` (user identifier)

#### File References:

  - `/backend/open_webui/usage_tracking/routers/webhook_router.py`
  - `/backend/open_webui/utils/cost_calculator.py`

### 2\. Core Cost Calculation Logic

#### Step 1: Raw Cost Processing

```python
# Extract raw cost from OpenRouter webhook
raw_cost = float(generation_data.get("usage", 0.0))  # USD amount
total_tokens = tokens_prompt + tokens_completion
```

#### Step 2: Markup Application

```python
# Apply client-specific markup rate (default: 1.3x = 30% markup)
markup_cost = raw_cost * client.markup_rate
```

**Business Rule**: Each client organization has a configurable markup rate stored in the database, typically 1.3 (30% markup over OpenRouter costs).

#### File References:

  - `/backend/open_webui/utils/cost_calculator.py`
  - `/backend/open_webui/usage_tracking/services/usage_service.py`

### 3\. Currency Conversion Process

#### NBP Microservice Integration

The system fetches USD/PLN exchange rates via a dedicated **NBP Microservice**. This service acts as a reliable, cached proxy to Poland's Central Bank (NBP) API and provides sophisticated fallback handling.

```python
# The application calls the internal NBP service
response = await http_client.get("http://mai-nbp-service:8001/api/usd-pln-rate")
usd_pln_rate = response.json()['rate']  # e.g., 3.9876

# The microservice itself has a fallback if the NBP API is unavailable
FALLBACK_USD_PLN_RATE = 4.0
```

#### Conversion Logic

```python
# Convert USD markup cost to PLN
cost_pln = markup_cost * usd_pln_rate
cost_pln_rounded = round(cost_pln, 2)
```

#### File References:

  - `/backend/open_webui/utils/currency_converter.py` (Client-side logic)
  - `nbp-service/app/main.py` (Microservice implementation)

### 4\. Data Aggregation Workflow

#### Daily Batch Processing (13:00 CET)

The system runs automated daily batch processing to consolidate usage data:

1.  **Fetch Exchange Rate**: Get current NBP USD/PLN rate from the NBP microservice.
2.  **Query InfluxDB**: Retrieve raw usage data for each client organization.
3.  **Apply Business Logic**: Calculate markup costs and PLN conversions.
4.  **Aggregate Data**: Sum totals by client, user, and model.
5.  **Store Results**: Save consolidated data to SQLite for fast retrieval.

#### Manual Execution

For debugging and operational purposes, the batch process can be triggered manually from the command line for any specific date.

```bash
docker exec mai-backend-dev python3 -m open_webui.utils.unified_batch_processor --run-now --date YYYY-MM-DD
```

#### File References:

  - `/backend/open_webui/utils/unified_batch_processor.py`
  - `/backend/open_webui/utils/batch_scheduler.py`

### 5\. Database Storage Structure

#### Primary Aggregation Tables

1.  **ClientDailyUsage**: Daily totals per client organization
2.  **ClientUserDailyUsage**: Daily totals per user within each client
3.  **ClientModelDailyUsage**: Daily totals per AI model within each client
4.  **DailyExchangeRateDB**: Historical USD/PLN rates used for conversions

#### Cost Fields Stored

  - `raw_cost`: Original OpenRouter cost (USD)
  - `markup_cost`: Cost after markup application (USD)
  - `total_cost_pln`: Final cost in Polish Zloty

#### File References:

  - `/backend/open_webui/models/organization_usage/client_usage_repository.py`
  - `/backend/open_webui/models/organization_usage/database.py`

### 6\. Frontend Display Logic

#### Admin Panel Usage Tab

The frontend retrieves and displays cost information through several API endpoints:

```typescript
// Main usage summary endpoint
GET /api/v1/usage-tracking/my-organization/usage-summary

// Response structure
{
  current_month: {
    total_cost: 45.67,        // USD markup cost
    total_cost_pln: 181.79,   // PLN converted cost (example with 4.0 rate)
    exchange_rate_info: {
      usd_pln: 4.0000,        // Rate used for conversion
      effective_date: "2025-08-01"
    }
  }
}
```

#### File References:

  - `/src/lib/components/admin/Settings/MyOrganizationUsage/MyOrganizationUsageContainer.svelte`
  - `/src/lib/apis/organizations/index.ts`

### 7\. Business Rules and Constraints

#### Markup Calculation Rules

  - **Default Markup**: 1.3x (30% over OpenRouter costs)
  - **Client-Specific**: Each organization can have custom markup rates
  - **Validation**: Markup rate must be \> 0, negative costs rejected
  - **Precision**: Costs stored with 6 decimal precision, displayed with 2-6 decimals

#### Currency Conversion Rules

  - **Primary Source**: NBP (Polish Central Bank) Table A average rates, proxied via the NBP Microservice.
  - **Publication Time**: 11:00 AM CET daily (with 30-minute buffer)
  - **Fallback Rate**: **4.0 PLN/USD** when NBP API is unavailable (handled by the microservice).
  - **Holiday Handling**: Uses last working day rate for weekends/holidays (handled by the microservice).
  - **Caching**: Handled by the NBP microservice (Redis for production).

#### Data Processing Rules

  - **Batch Time**: 13:00 CET daily to use same-day NBP rates
  - **Aggregation Period**: Calendar month (1st to current day)
  - **Retention**: Historical data maintained indefinitely
  - **Validation**: Negative tokens/costs rejected, zero values allowed

### 8\. Key Pricing Factors

#### Primary Cost Components

1.  **OpenRouter Base Cost**: Raw API usage cost in USD
2.  **Markup Multiplier**: Client-specific rate (typically 1.3x)
3.  **Exchange Rate**: NBP USD/PLN rate for currency conversion
4.  **Token Count**: Input + output tokens for usage measurement

#### Cost Calculation Formula

```
Final Cost USD = OpenRouter Raw Cost × Client Markup Rate
Final Cost PLN = Final Cost USD × NBP Exchange Rate
```

### 9\. Error Handling and Fallbacks

#### NBP API Resilience

The dedicated **NBP microservice** provides resilience through:

  - **Timeout Protection**: Timeouts on external API calls to NBP.
  - **Multiple Fallback Strategies**: Includes holiday calendar, last-working-day logic, and a hardcoded fallback rate.
  - **Graceful Degradation**: Uses the fallback rate when NBP is unavailable, ensuring the main application always receives a rate.
  - **User Notification**: Admin panel shows exchange rate source and warnings.

#### Cost Calculation Safeguards

  - **Input Validation**: Rejects negative costs and invalid markup rates.
  - **Exception Handling**: Returns zero values on calculation errors.
  - **Database Transactions**: Ensures data consistency during batch processing.
  - **Logging**: Comprehensive error logging for troubleshooting.

### 10\. Performance Optimizations

#### Data Access Patterns

  - **Pre-aggregation**: Daily batch processing eliminates real-time calculations.
  - **Smart Caching**: Exchange rates are cached effectively by the NBP microservice.
  - **Database Indexing**: Optimized queries for client/date/user lookups.
  - **Lazy Loading**: Frontend tabs load data on demand.

#### File References:

  - `/backend/open_webui/models/organization_usage/client_usage_repository.py`
  - `/src/lib/components/admin/Settings/MyOrganizationUsage/MyOrganizationUsageContainer.svelte`

## Technical Implementation Summary

The mAI cost calculation system implements a **robust, multi-stage workflow** that:

1.  **Receives** raw usage data from OpenRouter webhooks.
2.  **Applies** client-specific markup rates for business pricing.
3.  **Converts** USD costs to PLN using a resilient **NBP microservice** that provides official exchange rates.
4.  **Aggregates** data through a daily batch process at 13:00 CET.
5.  **Stores** consolidated results in SQLite for fast retrieval.
6.  **Displays** formatted costs in the admin panel with full transparency.

The system balances **accuracy, performance, and reliability** through comprehensive error handling, intelligent caching, and fallback mechanisms that ensure uninterrupted service even when external APIs are unavailable.

### Key Strengths

  - **Transparent Pricing**: Shows both USD and PLN with exchange rate details.
  - **Regulatory Compliance**: Uses official NBP rates for financial accuracy.
  - **High Availability**: The microservice architecture for currency rates prevents single points of failure.
  - **Audit Trail**: Complete historical record of costs and exchange rates.
  - **Scalable Architecture**: Clean separation between data collection, currency conversion, and presentation.