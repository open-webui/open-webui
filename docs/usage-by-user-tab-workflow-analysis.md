# Usage by User Tab - Workflow Analysis

## Executive Summary

The "My Organization Usage - Usage by User Tab" is a comprehensive user-level analytics feature within the mAI multi-tenant SaaS platform. This system aggregates and displays usage metrics per user within an organization, providing administrators with detailed insights into individual user consumption patterns, costs, and activity levels.

**Key Capabilities:**
- User-level usage aggregation with monthly breakdown
- Real-time PLN/USD dual currency display
- Daily batch processing for consistent reporting
- User mapping integration with OpenRouter external IDs
- Admin-only access control with environment-based multi-tenancy

## System Architecture Overview

### Component Structure
```
Frontend (Svelte/TypeScript)
├── MyOrganizationUsageContainer.svelte - Main orchestrator
├── UserDetailsTab.svelte - User usage display component
├── OrganizationUsageService.ts - API abstraction layer
└── Types & Stores - Data models and state management

Backend (FastAPI/Python)
├── usage_tracking/routers/usage_router.py - HTTP endpoints
├── usage_tracking/services/billing_service.py - Business logic
├── usage_tracking/repositories/usage_repository.py - Data access
└── models/organization_usage/ - Database models and domain logic
```

### Database Schema
```sql
-- Primary user usage aggregation table
ClientUserDailyUsage:
- id: "{client_org_id}:{user_id}:{usage_date}"
- client_org_id: Environment-based tenant isolation
- user_id: Internal OpenWebUI user identifier
- openrouter_user_id: External OpenRouter mapping
- usage_date: Date for daily aggregation
- total_tokens: Aggregated token consumption
- total_requests: Number of API requests
- raw_cost: Original OpenRouter pricing
- markup_cost: Cost with 1.3x markup applied
- created_at/updated_at: Audit timestamps
```

## Detailed Workflow: Data Collection to Display

### Phase 1: Usage Data Collection (Real-time)
**Trigger**: OpenRouter webhook or API request
**Entry Point**: `ClientUsageRepository.record_usage()`

#### Step 1.1: Usage Recording
```python
# Backend: client_usage_repository.py lines 66-150
def record_usage(self, usage_record: UsageRecordDTO) -> bool:
    """Record API usage with per-user tracking"""
    
    # 1. Create unique daily record ID
    user_usage_id = f"{client_org_id}:{user_id}:{usage_date}"
    
    # 2. Query existing record or create new
    user_usage = db.query(ClientUserDailyUsage).filter_by(id=user_usage_id).first()
    
    # 3. Aggregate usage metrics
    if user_usage:
        user_usage.total_tokens += usage_record.total_tokens
        user_usage.total_requests += 1
        user_usage.markup_cost += usage_record.markup_cost
    else:
        # Create new daily usage record
        user_usage = ClientUserDailyUsage(...)
```

**Business Rules Applied:**
- Daily aggregation per user per organization
- 1.3x markup rate applied to all costs
- Environment-based tenant isolation enforced
- OpenRouter user ID mapping maintained

### Phase 2: Monthly Aggregation Logic
**Location**: `ClientUsageRepository.get_usage_by_user()`
**Processing**: Current month calculation (1st day to today)

#### Step 2.1: Date Range Calculation
```python
# Backend: client_usage_repository.py lines 284-288
if not end_date:
    end_date = date.today()
if not start_date:
    start_date = end_date.replace(day=1)  # First day of current month
```

#### Step 2.2: User Aggregation Query
```python
# Backend: client_usage_repository.py lines 291-295
user_records = db.query(ClientUserDailyUsage).filter(
    ClientUserDailyUsage.client_org_id == client_org_id,
    ClientUserDailyUsage.usage_date >= start_date,
    ClientUserDailyUsage.usage_date <= end_date
).all()
```

#### Step 2.3: Per-User Totals Calculation
```python
# Backend: client_usage_repository.py lines 298-326
user_totals = {}
for record in user_records:
    if record.user_id not in user_totals:
        user_totals[record.user_id] = {
            'user_id': record.user_id,
            'total_tokens': 0,
            'total_requests': 0,
            'markup_cost': 0.0,
            'days_active': set()  # Track unique active days
        }
    
    # Aggregate usage metrics
    user_totals[record.user_id]['total_tokens'] += record.total_tokens
    user_totals[record.user_id]['days_active'].add(record.usage_date)
```

**Data Transformations:**
- Daily records → Monthly user totals
- Set-based days active calculation
- Cost descending sort for display priority

### Phase 3: API Layer Processing
**Endpoint**: `GET /api/v1/usage-tracking/my-organization/usage-by-user`
**Handler**: `get_my_organization_usage_by_user()`

#### Step 3.1: Service Layer Enhancement
```python
# Backend: billing_service.py lines 20-121
async def get_user_usage_breakdown(self, client_org_id: str = None):
    """Enhanced user data with OpenWebUI user details"""
    
    # 1. Get environment client ID
    client_org_id = self.client_repo.get_environment_client_id()
    
    # 2. Fetch aggregated usage data
    usage_data = self.usage_repo.get_usage_by_user(client_org_id)
    
    # 3. Get OpenWebUI user registry
    all_users = Users.get_users()
    user_dict = {u.id: u for u in all_users}
    
    # 4. Enhance with user details and PLN conversion
    for usage in usage_data:
        user_obj = user_dict.get(usage['user_id'])
        enhanced_usage = {
            "user_id": usage['user_id'],
            "user_name": user_obj.name if user_obj else usage['user_id'],
            "total_tokens": usage['total_tokens'],
            "markup_cost": usage['markup_cost'],
            "cost_pln": round(usage['markup_cost'] * usd_pln_rate, 2),
            "days_active": usage['days_active']
        }
```

**Business Logic Applied:**
- Real-time USD/PLN exchange rate conversion via NBP API
- User details enrichment from OpenWebUI registry
- Zero-usage user inclusion for complete organizational view
- External user ID mapping for OpenRouter integration

### Phase 4: Frontend Data Flow
**Component**: `MyOrganizationUsageContainer.svelte`
**Display**: `UserDetailsTab.svelte`

#### Step 4.1: Container Orchestration
```typescript
// Frontend: MyOrganizationUsageContainer.svelte lines 88-105
const loadUserUsage = async (): Promise<void> => {
    if (!clientOrgIdValidated || !clientOrgId) {
        toast.error('Unable to load user usage data');
        return;
    }
    
    const result = await OrganizationUsageService.getUserUsage($user.token, clientOrgId);
    if (result.success && result.data) {
        usageActions.setUserUsageData(result.data);
    }
};
```

#### Step 4.2: Tab Navigation Logic
```typescript
// Frontend: MyOrganizationUsageContainer.svelte lines 170-197
const handleTabChange = async (tab: TabType): Promise<void> => {
    // Admin-only access control
    if ($user?.role !== 'admin' && tab === 'users') {
        toast.error('Administrator privileges required');
        return;
    }
    
    // Lazy loading pattern
    if (tab === 'users' && userUsageData.length === 0) {
        await loadUserUsage();
    }
};
```

#### Step 4.3: User Display Component
```svelte
<!-- Frontend: UserDetailsTab.svelte lines 31-56 -->
<DataTable headers={tableHeaders} data={userUsageData || []}>
    {#each data as userUsage}
        <tr>
            <td>{userUsage.user_id}</td>
            <td>{FormatterService.formatNumber(userUsage.total_tokens)}</td>
            <td>{FormatterService.formatNumber(userUsage.total_requests)}</td>
            <td>{FormatterService.formatDualCurrency(userUsage.markup_cost, userUsage.cost_pln)}</td>
            <td>{userUsage.days_active}</td>
        </tr>
    {/each}
</DataTable>
```

## API Endpoints and Data Flow

### Primary Endpoint
```
GET /api/v1/usage-tracking/my-organization/usage-by-user
Authorization: Bearer {token}
Response: UserUsageResponse
```

### Response Structure
```json
{
  "success": true,
  "user_usage": [
    {
      "user_id": "user123",
      "user_name": "John Doe",
      "user_email": "john@company.com",
      "external_user_id": "openrouter_user_456",
      "total_tokens": 150000,
      "total_requests": 89,
      "markup_cost": 12.50,
      "cost_pln": 48.75,
      "days_active": 15,
      "user_mapping_enabled": true
    }
  ],
  "organization_name": "My Organization",
  "total_users": 25
}
```

### Data Flow Mapping
```
OpenRouter Webhook → Usage Recording → Daily Aggregation
    ↓
Database (ClientUserDailyUsage) → Monthly Query → User Totals
    ↓
Service Layer → User Enhancement → PLN Conversion
    ↓
API Response → Frontend Store → User Display Table
```

## Business Rules Documentation

### User Aggregation Rules
1. **Monthly Scope**: Always calculates from 1st day of current month to today
2. **Daily Deduplication**: One record per user per day per organization
3. **Cost Calculation**: Raw OpenRouter cost × 1.3 markup rate
4. **Days Active**: Unique count of days with any usage activity
5. **Zero Users**: Include all registered users, even with zero usage

### Access Control Rules
1. **Admin Only**: Usage by User tab restricted to admin role users
2. **Environment Isolation**: Users only see their organization's data
3. **Token Validation**: All requests require valid Bearer authentication
4. **Lazy Loading**: Data fetched only when tab is accessed

### Currency Conversion Rules
1. **Dual Display**: Always show both USD and PLN amounts
2. **Real-time Rates**: NBP exchange rates fetched per request
3. **Fallback Handling**: Graceful degradation if PLN conversion fails
4. **Precision**: PLN amounts rounded to 2 decimal places

## Integration Points

### Daily Batch Processing
- **Schedule**: 00:00 daily automatic processing
- **Scope**: Consolidate previous day's usage into daily summaries
- **Exchange Rates**: NBP API integration with holiday-aware logic
- **Data Validation**: Automated corrections and consistency checks

### User Mapping System
- **Internal IDs**: OpenWebUI user identifiers for access control
- **External IDs**: OpenRouter user mapping for API tracking
- **Sync Strategy**: Real-time mapping during usage recording
- **Error Handling**: Fallback to internal IDs if mapping fails

### Multi-Tenant Architecture
- **Environment-based**: Client organization determined by container
- **Data Isolation**: Strict filtering by client_org_id in all queries
- **Shared Infrastructure**: Single codebase, isolated data per tenant
- **Scalability**: SQLite per container for performance isolation

## Performance Considerations

### Database Optimization
- **Composite Primary Keys**: Efficient lookups via compound IDs
- **Date Range Queries**: Indexed filtering on usage_date columns
- **Aggregation Strategy**: Pre-calculated daily summaries vs real-time
- **Connection Pooling**: Context manager pattern for database access

### Frontend Performance
- **Lazy Loading**: Tab content loaded on-demand only
- **State Management**: Svelte stores for efficient reactivity
- **API Caching**: Service layer caching for repeated requests
- **Progressive Enhancement**: Graceful loading states and error handling

### Scalability Patterns
- **Horizontal Scaling**: Independent Docker containers per organization
- **Database Sharding**: SQLite per tenant natural partitioning
- **API Rate Limiting**: Environment-based request throttling
- **Memory Management**: Efficient data structures and cleanup

## Error Handling and Edge Cases

### Data Availability
- **Empty Organizations**: Handle new organizations with no usage
- **Missing Users**: Display all registered users with zero values
- **Exchange Rate Failures**: USD-only fallback with clear messaging
- **Database Connectivity**: Graceful degradation with cached data

### User Experience
- **Loading States**: Clear progress indicators during data fetching
- **Permission Errors**: Informative messages for non-admin users
- **Network Timeouts**: 10-second timeout with retry suggestions
- **Data Refresh**: Manual refresh capability for stale data

### Business Continuity
- **Backup Strategies**: Daily database snapshots per container
- **Monitoring**: Usage pattern anomaly detection
- **Audit Trails**: Complete usage recording history
- **Recovery Procedures**: Point-in-time restoration capabilities

## Maintenance and Operations

### Daily Operations
- **Batch Processing**: Automated 00:00 daily consolidation
- **Exchange Rate Updates**: NBP API sync with holiday handling
- **Data Validation**: Consistency checks and anomaly detection
- **Performance Monitoring**: Query performance and response times

### Business Intelligence
- **Pre-calculated Metrics**: All displayed data batch-processed
- **Historical Analysis**: Complete usage history maintained
- **Trend Analysis**: Month-over-month usage patterns
- **Cost Optimization**: Markup rate and pricing tier analysis

### Security and Compliance
- **Data Privacy**: User data isolation per organization
- **Access Logging**: Complete audit trail of data access
- **API Security**: Token-based authentication and authorization
- **Data Retention**: Configurable retention policies per tenant

---

**Document Version**: 2.0  
**Last Updated**: 2025-01-28  
**Analysis Coverage**: Complete end-to-end user usage workflow  
**Technical Accuracy**: Based on production codebase analysis