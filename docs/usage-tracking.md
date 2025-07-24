# Usage Tracking System

## Overview

The mAI Usage Tracking System provides comprehensive monitoring and billing capabilities for OpenRouter API usage in a multi-tenant reseller environment. The system tracks usage per organization, user, and AI model while maintaining a 1.3x markup pricing structure.

## Architecture

### Option 1: Simplified Daily Summaries (Implemented)
- **99% storage reduction** compared to per-request logging
- **Hybrid approach**: Real-time counters for today + daily summaries for history
- **Live updates**: Today's usage refreshes every 30 seconds
- **Historical data**: Daily rollups for efficient long-term storage

## Key Features

### 1. Multi-Tenant Organization Management
- **Client Organizations**: Each client gets dedicated OpenRouter API key
- **User Mapping**: Users are assigned to client organizations
- **Automatic Provisioning**: Default organization creation for new users
- **API Key Management**: Integrated with OpenRouter Provisioning API

### 2. Real-Time Usage Tracking
- **Token Counting**: Input/output tokens tracked separately
- **Cost Calculation**: Raw costs + 1.3x markup automatically calculated
- **Model Tracking**: Usage broken down by AI model and provider
- **User Attribution**: Per-user usage within each organization

### 3. Usage Analytics & Reporting
- **Live Dashboard**: Real-time today's usage with 30-second updates
- **Daily Trends**: Historical usage patterns over time
- **Per-User Breakdown**: Individual user consumption within organizations
- **Per-Model Analysis**: Usage statistics by AI model and provider
- **Monthly Summaries**: Aggregated monthly totals and averages

### 4. Billing & Cost Management
- **Markup Pricing**: Configurable markup rates (default 1.3x)
- **Monthly Limits**: Per-organization spending limits
- **Profit Tracking**: Automatic profit margin calculations
- **Export Capabilities**: Usage data export for billing systems

## Database Schema

### Core Tables

#### `client_organizations`
- Client organization management
- OpenRouter API key storage
- Markup rates and monthly limits
- Billing contact information

#### `user_client_mappings`
- Maps users to client organizations
- OpenRouter user ID tracking
- Active/inactive status management

#### `client_daily_usage`
- Daily usage summaries per organization
- Token counts, costs, and request statistics
- Efficient storage for historical data

#### `client_user_daily_usage`
- Per-user daily usage within organizations
- Granular user-level tracking
- OpenRouter user ID correlation

#### `client_model_daily_usage`
- Per-model daily usage statistics
- Provider and model performance metrics
- Cost breakdown by AI model

## API Endpoints

### Admin Endpoints (requires admin authentication)

#### Global Settings
- `GET /client_organizations/settings` - Get global OpenRouter settings
- `POST /client_organizations/settings` - Update provisioning settings

#### Organization Management
- `GET /client_organizations/clients` - List all client organizations
- `POST /client_organizations/clients` - Create new client organization
- `PATCH /client_organizations/clients/{id}` - Update organization settings
- `DELETE /client_organizations/clients/{id}` - Deactivate organization

#### User Mappings
- `GET /client_organizations/user-mappings` - List all user mappings
- `POST /client_organizations/user-mappings` - Create user mapping
- `DELETE /client_organizations/user-mappings/{user_id}` - Remove mapping

#### Usage & Billing
- `GET /client_organizations/usage/summary` - Organization usage statistics
- `GET /client_organizations/usage/today` - Real-time today's usage
- `GET /client_organizations/usage/billing` - Billing summary for all clients
- `GET /client_organizations/usage/by-user/{client_id}` - Per-user usage breakdown
- `GET /client_organizations/usage/by-model/{client_id}` - Per-model usage breakdown
- `GET /client_organizations/usage/export` - Export usage data

### User Endpoints (requires user authentication)

#### Personal Usage
- `GET /client_organizations/usage/my-organization` - User's organization usage
- `GET /client_organizations/usage/my-organization/today` - Today's usage for user's org

## Frontend Components

### MyOrganizationUsage.svelte
Comprehensive usage dashboard with:
- **Real-time metrics**: Live today's usage with auto-refresh
- **Historical trends**: Daily usage history visualization
- **Tabbed interface**: Overview, Stats, By User, By Model views
- **Usage statistics**: Token counts, costs, request metrics
- **Responsive design**: Mobile-friendly dashboard layout

### Key UI Features
- **Live indicators**: Green pulsing dots for real-time data
- **Auto-refresh**: 30-second intervals for today's usage
- **Currency formatting**: Proper USD formatting for costs
- **Number formatting**: Comma-separated large numbers
- **Tab navigation**: Easy switching between different views

## Configuration

### Environment Variables
- `OPENROUTER_PROVISIONING_KEY` - OpenRouter organization API key
- `DEFAULT_MARKUP_RATE` - Default markup multiplier (1.3)
- `BILLING_CURRENCY` - Currency for billing (USD)

### Global Settings (Database)
- OpenRouter provisioning key configuration
- Default markup rates for new organizations
- Billing currency preferences

## Usage Recording Flow

1. **API Request**: User makes request through mAI
2. **Organization Lookup**: System identifies user's organization
3. **Real-time Recording**: Usage recorded immediately in live counters
4. **Daily Rollup**: At midnight, daily summaries are created/updated
5. **Multi-level Tracking**: Usage recorded at organization, user, and model levels

## Billing Integration

### Markup Calculation
```
Raw Cost (from OpenRouter) × Markup Rate = Client Cost
Example: $0.10 × 1.3 = $0.13 (charged to client)
Profit: $0.03 per request
```

### Monthly Limits
- Organizations have configurable monthly spending limits
- Limits enforced through OpenRouter API key restrictions
- Automatic alerts when approaching limits

## Performance Optimizations

### Storage Efficiency
- **Daily summaries** instead of per-request logs (99% reduction)
- **Indexed queries** for fast dashboard loading
- **Partitioned tables** for historical data management

### Real-time Updates
- **Live counters** for today's usage only
- **Background sync** for historical data reconciliation
- **Cached calculations** for dashboard metrics

## Security Features

### Authentication & Authorization
- **Admin-only endpoints** for organization management
- **User-scoped access** to personal organization data
- **API key security** with encrypted storage

### Data Protection
- **Encrypted API keys** in database storage
- **Audit logging** for all configuration changes
- **Rate limiting** on usage endpoints

## Monitoring & Alerts

### Health Checks
- Database connectivity monitoring
- OpenRouter API status verification
- Usage recording pipeline health

### Business Metrics
- Daily revenue tracking
- Usage trend analysis
- Client activity monitoring
- Profit margin calculations

## Setup & Deployment

### Initial Configuration
1. Configure OpenRouter provisioning API key
2. Set default markup rates and currency
3. Create client organizations
4. Map users to organizations

### Database Migrations
- Automated schema updates
- Backward compatibility maintained
- Data integrity checks included

### Testing
- Unit tests for usage calculations
- Integration tests for API endpoints
- End-to-end workflow validation
- Performance benchmarking

## Support & Troubleshooting

### Common Issues
- **"Failed to load usage statistics"**: Check user-organization mapping
- **Zero usage displayed**: Verify usage recording integration
- **Authentication errors**: Confirm proper API key configuration

### Debug Tools
- Usage recording verification endpoints
- Database query performance monitoring
- OpenRouter API connectivity testing
- Real-time usage counter validation

## Future Enhancements

### Planned Features
- **CSV export** for billing data
- **Usage alerts** for approaching limits
- **Advanced analytics** with charts and graphs
- **Custom reporting** with date range selection
- **Webhook integration** for external billing systems

### Scalability Improvements
- **Redis caching** for high-frequency queries
- **Database sharding** for large-scale deployments
- **Async processing** for usage aggregation
- **CDN integration** for dashboard assets