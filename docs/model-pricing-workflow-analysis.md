# Model Pricing Workflow Analysis - mAI System

## Executive Summary

The mAI model pricing system provides real-time model pricing information through dynamic integration with the OpenRouter API. The system features automatic daily pricing updates at 00:00, intelligent fallback mechanisms, and a hierarchical categorization system that organizes models into Budget, Standard, Premium, Fast, and Reasoning tiers based on per-million-token pricing.

### Key Features
- **Dynamic Pricing**: Real-time pricing data from OpenRouter API with 24-hour caching
- **Daily Updates**: Automated pricing refresh at 00:00 via cron scheduler
- **Fallback System**: Hardcoded pricing data ensures system availability during API outages
- **Categorization**: 5-tier pricing categories with color-coded UI representation
- **Per-Million-Token Display**: Transparent pricing in USD per 1 million tokens
- **Multi-layer Caching**: In-memory and Redis caching for optimal performance

## System Architecture Overview

```mermaid
graph TB
    subgraph "Frontend Layer"
        A[ModelPricingTab.svelte] --> B[PricingService.ts]
        B --> C[API Client]
    end
    
    subgraph "API Layer"
        C --> D["/api/v1/usage-tracking/model-pricing"]
        D --> E[billing_router.py]
        E --> F[PricingService]
    end
    
    subgraph "Business Logic Layer"
        F --> G[OpenRouterModelsAPI]
        G --> H[PricingCalculatorService]
        H --> I[CachedOpenRouterRepository]
        I --> J[OpenRouterRepository]
    end
    
    subgraph "External APIs"
        J --> K[OpenRouter API]
        K --> L[/v1/models endpoint]
    end
    
    subgraph "Scheduling Layer"
        M[Cron Job 00:00] --> N[daily_batch_cron.sh]
        N --> O[BatchOrchestrator]
        O --> P[ModelPricingService]
        P --> Q[Force Refresh Cache]
    end
    
    subgraph "Caching Layer"
        R[In-Memory Cache] --> S[Redis Cache]
        S --> T[24-hour TTL]
    end
```

### Component Hierarchy

1. **Presentation Layer**
   - `ModelPricingTab.svelte` - Main UI component
   - `PricingService.ts` - Frontend service with fallback data
   - `DataTable.svelte` - Reusable table component

2. **API Layer**
   - `billing_router.py` - HTTP endpoints for pricing
   - `usage_tracking_router.py` - Main router integration
   - Response models with Pydantic validation

3. **Business Logic Layer**
   - `PricingCalculatorService` - Core pricing calculations
   - `OpenRouterRepository` - API integration
   - `CachedOpenRouterRepository` - Caching wrapper

4. **Scheduling Layer**
   - `BatchOrchestrator` - Daily batch processing
   - `ModelPricingService` - Batch pricing updates
   - Cron scheduler for automated execution

## Detailed Workflow Steps

### 1. Pricing Data Retrieval Process

#### Initial Load Workflow
```
User Request → ModelPricingTab.svelte → PricingService.getModelPricing()
    ↓
API Call: GET /api/v1/usage-tracking/model-pricing
    ↓
billing_router.get_mai_model_pricing() → PricingService.get_model_pricing()
    ↓
OpenRouterModelsAPI.get_dynamic_model_pricing()
    ↓
PricingCalculatorService.get_model_pricing()
    ↓
CachedOpenRouterRepository.fetch_all_models()
    ↓
Check Cache (24h TTL) → If Fresh: Return Cached Data
    ↓
If Stale: OpenRouterRepository.fetch_all_models()
    ↓
HTTP GET: https://openrouter.ai/api/v1/models
    ↓
Map API Response → Apply Category Logic → Filter mAI Models
    ↓
Cache Result → Return to Frontend
```

#### Business Logic Flow
1. **Cache Check**: Verify 24-hour cache validity
2. **API Request**: Fetch latest pricing from OpenRouter
3. **Data Mapping**: Convert OpenRouter format to mAI format
4. **Filtering**: Include only mAI-supported models (12 models)
5. **Categorization**: Apply pricing tier logic
6. **Caching**: Store result with 24-hour TTL
7. **Fallback**: Use hardcoded data if API fails

### 2. Daily Pricing Update Process

#### Scheduled Update Workflow
```
Cron Job (00:00 daily)
    ↓
scripts/daily_batch_cron.sh
    ↓
BatchOrchestrator.run_daily_batch()
    ↓
Phase 1: Update Reference Data
    ↓
ModelPricingService.update_model_pricing()
    ↓
get_dynamic_model_pricing(force_refresh=True)
    ↓
Invalidate Cache → Fetch Fresh Data → Update Cache
    ↓
Store Pricing Snapshot for Audit
    ↓
Log Success/Failure → Continue to Other Batch Operations
```

#### Scheduling Configuration
- **Cron Schedule**: `0 0 * * *` (Daily at midnight)
- **Script Location**: `/scripts/daily_batch_cron.sh`
- **Log Location**: `/app/logs/daily_batch_YYYYMMDD.log`
- **Environment**: Production Docker containers
- **Timeout**: 2-minute API timeout with retry logic

### 3. Model Categorization Methodology

#### Tier Definition Logic
```python
def _determine_category(input_price: float, output_price: float) -> ModelCategory:
    avg_price = (input_price + output_price) / 2
    
    if avg_price < 1.0:
        return ModelCategory.BUDGET      # Green badge
    elif avg_price < 5.0:
        return ModelCategory.STANDARD    # Blue badge
    elif avg_price < 10.0:
        return ModelCategory.FAST        # Orange badge
    elif avg_price < 50.0:
        return ModelCategory.PREMIUM     # Purple badge
    else:
        return ModelCategory.REASONING   # Red badge
```

#### Category Characteristics
| Category | Price Range | Color | Examples | Use Cases |
|----------|-------------|-------|----------|-----------|
| **Budget** | < $1.00 avg | Green | DeepSeek Chat, GPT-4o Mini | Basic tasks, high volume |
| **Standard** | $1.00-$4.99 | Blue | Claude 3.5 Haiku, O4 Mini High | General purpose |
| **Fast** | $5.00-$9.99 | Orange | Gemini 2.5 Flash | Quick responses |
| **Premium** | $10.00-$49.99 | Purple | Claude Sonnet 4, GPT-4.1 | Advanced reasoning |
| **Reasoning** | $50.00+ | Red | OpenAI O3 | Complex problem solving |

### 4. Pricing Calculation and Per-Million-Token Conversions

#### OpenRouter API Data Transformation
```python
# OpenRouter returns prices as strings in USD per token
prompt_price = float(api_model.pricing.get("prompt", "0"))      # $0.000003 per token
completion_price = float(api_model.pricing.get("completion", "0")) # $0.000012 per token

# Convert to per million tokens for display
price_per_million_input = prompt_price * 1_000_000    # $3.00 per 1M tokens
price_per_million_output = completion_price * 1_000_000 # $12.00 per 1M tokens
```

#### Cost Calculation for Usage
```python
async def calculate_cost(
    model_id: str,
    input_tokens: int,
    output_tokens: int,
    markup_rate: float = 1.3
) -> Dict[str, float]:
    
    # Get model pricing
    model = await repository.fetch_model_by_id(model_id)
    
    # Calculate raw costs
    input_cost = (input_tokens / 1_000_000) * model.price_per_million_input
    output_cost = (output_tokens / 1_000_000) * model.price_per_million_output
    raw_cost = input_cost + output_cost
    
    # Apply mAI markup (30%)
    markup_cost = raw_cost * markup_rate
    
    return {
        "raw_cost": raw_cost,
        "markup_cost": markup_cost,
        "markup_rate": markup_rate
    }
```

### 5. Database Schema for Pricing Data Storage

#### In-Memory Caching Structure
```python
class PricingRepository:
    def __init__(self, db: AsyncDatabase):
        self._pricing_cache: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[datetime] = None
    
    # Cache structure
    pricing_cache = {
        "success": True,
        "models": [
            {
                "id": "anthropic/claude-sonnet-4",
                "name": "Claude Sonnet 4",
                "provider": "Anthropic",
                "price_per_million_input": 8.00,
                "price_per_million_output": 24.00,
                "context_length": 1000000,
                "category": "Premium"
            }
        ],
        "last_updated": "2025-01-28T10:00:00Z",
        "source": "openrouter_api"
    }
```

#### No Persistent Database Storage
- **Storage Method**: In-memory caching only
- **Cache Duration**: 24 hours (3600 seconds)
- **Backup Strategy**: Hardcoded fallback data
- **Audit Trail**: Pricing snapshots stored temporarily
- **Rationale**: Pricing data is dynamic and externally sourced

### 6. API Endpoints and Data Flow Mapping

#### Primary Endpoints
```
GET /api/v1/usage-tracking/model-pricing
├── Purpose: Retrieve current model pricing
├── Authentication: None required (public pricing data)
├── Response: ModelPricingResponse
├── Cache: 24-hour server-side cache
└── Fallback: Hardcoded pricing data

POST /webhook/openrouter-usage (Related)
├── Purpose: Usage tracking with pricing lookup
├── Authentication: API key required
├── Response: WebhookResponse
└── Pricing: Real-time model price lookup
```

#### Data Flow Architecture
```
Frontend Request
    ↓
API Gateway (/api/v1/usage-tracking/)
    ↓
FastAPI Router (billing_router.py)
    ↓
Business Service (PricingService)
    ↓
Repository Layer (CachedOpenRouterRepository)
    ↓
External API (OpenRouter) | Fallback Data
    ↓
Response Transformation (Pydantic Models)
    ↓
JSON Response to Frontend
```

### 7. Business Rules for Pricing Tiers and Model Classification

#### Model Filtering Rules
```python
# Only include mAI-supported models
mai_model_ids = {
    "anthropic/claude-sonnet-4",
    "google/gemini-2.5-flash", 
    "google/gemini-2.5-pro",
    "deepseek/deepseek-chat-v3-0324",
    "anthropic/claude-3.7-sonnet",
    "google/gemini-2.5-flash-lite-preview-06-17",
    "openai/gpt-4.1",
    "x-ai/grok-4",
    "openai/gpt-4o-mini",
    "openai/o4-mini-high",
    "openai/o3",
    "openai/chatgpt-4o-latest"
}
```

#### Provider Extraction Logic
```python
# Extract provider from model ID
provider = api_model.id.split("/")[0].title() if "/" in api_model.id else "Unknown"
# Examples:
# "anthropic/claude-sonnet-4" → "Anthropic"
# "openai/gpt-4o" → "OpenAI"
# "google/gemini-2.5-pro" → "Google"
```

#### Category Color Mapping
```python
def getCategoryColorClass(category: string): string {
    switch (category) {
        case 'Budget': return 'bg-green-100 text-green-800';
        case 'Standard': return 'bg-blue-100 text-blue-800';
        case 'Premium': return 'bg-purple-100 text-purple-800';
        case 'Fast': return 'bg-orange-100 text-orange-800';
        case 'Reasoning': return 'bg-red-100 text-red-800';
        default: return 'bg-gray-100 text-gray-800';
    }
}
```

### 8. Currency Conversion Integration and Display Logic

#### Exchange Rate Integration
```python
# Currency conversion is handled in usage tracking, not pricing display
from open_webui.utils.currency_converter import get_exchange_rate_info

exchange_info = await get_exchange_rate_info()
# Returns USD/PLN exchange rate information

# Pricing is always displayed in USD
# Currency conversion applied only to usage costs, not model pricing
```

#### Display Logic
- **Pricing Display**: Always in USD (per 1M tokens)
- **Usage Costs**: Converted to PLN using NBP exchange rates
- **Separation**: Model pricing (USD) vs Usage billing (PLN)
- **Update Frequency**: Exchange rates updated daily, pricing updated daily

### 9. Frontend Component Structure for Pricing Display

#### Component Architecture
```
ModelPricingTab.svelte
├── Header Section
│   ├── Title: "Available Models & Pricing"
│   └── Status: "Prices updated daily at 00:00"
├── Information Card
│   ├── Pricing explanation
│   ├── Token information
│   └── Context length details
├── Category Filters
│   ├── Budget badge (green)
│   ├── Standard badge (blue)
│   ├── Premium badge (purple)
│   ├── Fast badge (orange)
│   └── Reasoning badge (red)
├── Data Table
│   ├── Model name and ID
│   ├── Provider
│   ├── Input pricing ($X.XX per 1M tokens)
│   ├── Output pricing ($X.XX per 1M tokens)
│   ├── Context length (formatted)
│   └── Category badge
└── Feature Cards
    ├── Pricing transparency
    ├── Usage tracking integration
    └── Model availability stats
```

#### State Management
```typescript
// Frontend store structure
interface PricingStore {
    modelPricingData: ModelPricing[];
    loading: LoadingState;
    error: string | null;
    lastUpdated: string | null;
}

// Service integration
class PricingService {
    static async getModelPricing(): Promise<PricingServiceResponse>;
    static getCategories(): string[];
    static filterByCategory(models: ModelPricing[], category: string): ModelPricing[];
    static getCategoryColorClass(category: string): string;
}
```

### 10. Integration Points with OpenRouter and Usage Tracking Systems

#### OpenRouter API Integration
```
mAI System ←→ OpenRouter API
    ↓
Pricing Endpoint: GET /api/v1/models
    ↓
Response Format:
{
    "data": [
        {
            "id": "anthropic/claude-sonnet-4",
            "name": "Claude Sonnet 4",
            "pricing": {
                "prompt": "0.000008",      // USD per token
                "completion": "0.000024"   // USD per token
            },
            "context_length": 1000000,
            "description": "...",
            "created": 1640995200,
            "architecture": {...},
            "top_provider": {...}
        }
    ]
}
```

#### Usage Tracking Integration
```python
# When processing OpenRouter webhooks
async def process_webhook(webhook_data):
    model_id = webhook_data.get("model")
    
    # Get current pricing for cost calculation
    pricing_service = PricingService()
    model_pricing = await pricing_service.get_model_by_id(model_id)
    
    # Calculate costs with pricing
    cost_calculation = await pricing_service.calculate_cost(
        model_id=model_id,
        input_tokens=webhook_data.get("input_tokens"),
        output_tokens=webhook_data.get("output_tokens"),
        markup_rate=1.3  # mAI 30% markup
    )
    
    # Store usage with calculated costs
    await store_usage_record(cost_calculation)
```

### 11. Error Handling and Fallback Mechanisms

#### Multi-Layer Fallback System
```
1. Primary: OpenRouter API (live pricing)
    ↓ (on failure)
2. Secondary: Cached data (up to 24h old)
    ↓ (on failure)
3. Tertiary: Hardcoded fallback data (12 models)
    ↓ (always available)
4. UI: Graceful degradation with error messages
```

#### Error Handling Logic
```python
async def get_model_pricing():
    try:
        # Attempt API call
        result = await get_dynamic_model_pricing()
        if result.get("success") and result.get("models"):
            return result
    except Exception as e:
        log.error(f"API failed: {e}")
    
    # Use fallback data
    return {
        "success": False,
        "models": FALLBACK_PRICING,
        "source": "hardcoded_fallback",
        "error": "API unavailable"
    }
```

#### Frontend Error States
```typescript
// Loading states
loading: {
    loading: boolean;
    error: string | null;
}

// Error display
{#if loading.loading}
    <LoadingState message="Loading model pricing..." />
{:else if loading.error}
    <ErrorState message="Failed to load pricing" fallback={true} />
{:else}
    <DataTable data={modelPricingData} />
{/if}
```

### 12. Performance Considerations and Caching Strategies

#### Caching Architecture
```
Level 1: Browser Cache (Frontend)
├── Duration: Session-based
├── Scope: Component state
└── Invalidation: Page refresh

Level 2: In-Memory Cache (Backend)
├── Duration: 24 hours
├── Scope: Application instance
└── Invalidation: Daily batch or manual refresh

Level 3: Redis Cache (Optional)
├── Duration: 24 hours
├── Scope: Cross-instance
└── Invalidation: TTL expiration

Level 4: Fallback Data (Static)
├── Duration: Indefinite
├── Scope: Application code
└── Invalidation: Code deployment
```

#### Performance Metrics
- **API Response Time**: < 200ms (cached)
- **API Response Time**: < 2s (fresh fetch)
- **Cache Hit Rate**: > 95% during normal operation
- **Fallback Activation**: < 1% of requests
- **Daily Update Duration**: < 30 seconds
- **Memory Usage**: < 10MB for pricing cache

#### Optimization Strategies
1. **Batch Updates**: Daily refresh instead of per-request
2. **Selective Filtering**: Only 12 models instead of full catalog
3. **Tiered Caching**: Multiple cache levels for resilience
4. **Background Refresh**: Update cache before expiration
5. **Circuit Breaker**: Prevent cascade failures

## System Health and Monitoring

### Key Performance Indicators
- **Pricing Data Freshness**: < 24 hours
- **API Availability**: > 99.5% uptime
- **Cache Hit Rate**: > 95%
- **Daily Batch Success**: > 99% completion rate
- **Fallback Usage**: < 1% of requests

### Monitoring Points
1. **Daily Batch Logs**: `/app/logs/daily_batch_YYYYMMDD.log`
2. **API Response Times**: OpenRouter integration metrics
3. **Cache Performance**: Hit/miss ratios
4. **Error Rates**: API failures and fallback activation
5. **Data Accuracy**: Pricing comparison audits

### Troubleshooting Guide
1. **Pricing Data Outdated**: Check daily batch execution
2. **API Failures**: Verify OpenRouter service status
3. **Cache Issues**: Clear in-memory cache via restart
4. **Display Problems**: Verify fallback data integrity
5. **Performance Issues**: Monitor cache hit rates

---

## Conclusion

The mAI model pricing system provides a robust, scalable solution for displaying dynamic AI model pricing information. Through intelligent caching, automated daily updates, and comprehensive fallback mechanisms, the system ensures reliable pricing data availability while maintaining optimal performance. The hierarchical categorization system and transparent per-million-token pricing enable users to make informed decisions about model selection based on their budget and performance requirements.

The system's architecture supports future enhancements including additional model providers, more granular pricing tiers, and enhanced analytics capabilities while maintaining backward compatibility and system reliability.