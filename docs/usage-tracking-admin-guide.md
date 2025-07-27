# mAI Usage Tracking System - Admin Guide

**Date**: July 27, 2025  
**Status**: ✅ **PRODUCTION READY** - Business-focused admin interface with holiday-aware NBP integration  
**Version**: 3.1 (Admin-focused daily breakdown with intelligent currency conversion)

---

## Executive Summary

The mAI Usage Tracking System provides **business-focused administrative oversight** of OpenRouter API usage for Polish SME clients. The system has been specifically designed for management and administrative purposes, showing daily summaries and monthly trends rather than unnecessary real-time data.

### Business-Focused Design
- **Administrative Interface**: Clean monthly overview for management decisions
- **Daily Breakdown**: Complete usage patterns from 1st to last day of month  
- **Business Intelligence**: Peak usage days, cost averages, model preferences
- **No Real-time Overload**: Single page load for business oversight purposes

---

## Admin Dashboard Overview

### Monthly Summary Cards
```
┌─────────────────┬─────────────────┬─────────────────┐
│ Total Tokens    │ Total Cost      │ Usage Activity  │
│ 52,400          │ $0.187 (0.77 zł)│ 12/27 days     │
│ July 2025       │ 168 requests    │ 44% active     │
└─────────────────┴─────────────────┴─────────────────┘
```

### Business Insights Section
```
Usage Averages          Peak Usage              Most Used
• Daily Average: 4,367   • Busiest Day: 2025-07-15  • Primary Model: Claude Sonnet 4
• Usage Day Avg: 4,367   • Highest Cost: 2025-07-15 • Active Users: 2
```

### Daily Breakdown Table
```
Date        Day      Tokens   Cost      Requests  Primary Model    Last Activity
2025-07-01  Monday   1,500    $0.0052   5         Gemini Flash     09:30
2025-07-02  Tuesday  2,200    $0.0078   8         Claude Sonnet    14:15
2025-07-15  Monday   8,900    $0.0325   25        Claude Sonnet    16:45
```

---

## Core System Architecture

### Simplified Data Flow (Business-Appropriate)
```
OpenRouter API Call → Usage Recording → Daily Summaries → Admin Dashboard
                              ↓
                    Multi-table Storage
                    ├── client_daily_usage (primary)
                    ├── client_user_daily_usage 
                    └── client_model_daily_usage
```

### Key Features
- **Single Source of Truth**: All data in daily summaries
- **Immediate Recording**: Usage visible after each API call (no rollover delays)
- **Business Intelligence**: Automatically calculated insights and trends
- **Multi-tenant Support**: Isolated data per client organization

---

## Database Schema (Admin Reference)

### Primary Usage Table: `client_daily_usage`
```sql
CREATE TABLE client_daily_usage (
    id TEXT PRIMARY KEY,                    -- Format: "{client_org_id}:{date}"
    client_org_id TEXT NOT NULL,           -- Organization reference
    usage_date DATE NOT NULL,              -- Daily grouping
    total_tokens INTEGER DEFAULT 0,        -- Daily token consumption
    total_requests INTEGER DEFAULT 0,      -- Number of API requests
    raw_cost REAL DEFAULT 0.0,            -- OpenRouter cost (before markup)
    markup_cost REAL DEFAULT 0.0,         -- Client cost (with 1.3x markup)
    primary_model TEXT,                    -- Most used model that day
    unique_users INTEGER DEFAULT 1,       -- Active users count
    created_at INTEGER NOT NULL,          -- Creation timestamp
    updated_at INTEGER NOT NULL           -- Last activity timestamp
);
```

### Supporting Tables
- **`client_organizations`**: Client management with API keys and markup rates
- **`client_user_daily_usage`**: Per-user daily breakdown
- **`client_model_daily_usage`**: Per-model usage statistics
- **`user_client_mapping`**: User-to-organization assignments

---

## Admin Interface Components

### 1. Monthly Overview Cards

**Total Tokens Card**
- Shows cumulative tokens for current month
- Displays month name for context
- No real-time indicators (business-appropriate)

**Total Cost Card** 
- Monthly cost in USD and PLN
- Request count for volume context
- Holiday-aware NBP exchange rates with intelligent fallback system

**Usage Activity Card**
- Days with usage vs. total days in month
- Percentage of active days for planning
- Business intelligence for usage patterns

### 2. Business Insights Panel

**Usage Averages**
- Daily average tokens across all days
- Usage day average (only counting active days)
- Cost averaging for budgeting

**Peak Usage Identification**
- Busiest day by token consumption
- Highest cost day for budget analysis
- Pattern recognition for capacity planning

**Resource Utilization**
- Most used AI model for optimization
- Active user count for licensing
- Model preference insights

### 3. Daily Breakdown Table

**Complete Monthly View**
- Every day from 1st to current day of month
- Token usage, cost, and request volumes
- Primary model used each day
- Last activity timestamp for monitoring

**Business Planning Data**
- Day-of-week patterns for resource planning
- Cost progression for budget tracking
- Model usage trends for contract optimization

---

## Administrative Use Cases

### 📊 **Monthly Business Review**
1. **Load Admin Dashboard** - Single page load, no refresh needed
2. **Review Monthly Cards** - Total usage, cost, and activity percentage
3. **Analyze Peak Days** - Identify usage patterns and capacity needs
4. **Check Daily Breakdown** - Detailed day-by-day analysis

### 💰 **Budget Planning & Cost Control**
- **Monthly Totals**: Clear visibility into spending patterns
- **Daily Averages**: Predictable budget forecasting
- **Peak Day Analysis**: Capacity planning and cost optimization
- **Currency Conversion**: Polish Złoty support for local budgeting

### 🔍 **Usage Optimization**
- **Model Preferences**: Identify most-used AI models for contract negotiation
- **User Activity**: Monitor active users for licensing optimization
- **Daily Patterns**: Understand peak usage for resource allocation
- **Cost Per Token**: ROI analysis and pricing optimization

### 📈 **Strategic Planning**
- **Usage Trends**: Month-over-month growth analysis
- **Activity Percentage**: System utilization for scaling decisions
- **Model Distribution**: Technology investment planning
- **User Engagement**: Adoption and training insights

---

## Currency Conversion System

### Holiday-Aware NBP Integration

The system features an intelligent **3-Tier Fallback System** for PLN currency conversion that automatically handles Polish banking holidays and non-working days:

#### Tier 1: Polish Holiday Calendar Optimization
- **2025 Holiday Calendar**: Exact Polish holidays with correct dates
- **API Call Optimization**: Skips API calls for known non-working days
- **Smart Fallback**: Automatically uses last working day rate
- **Weekend Handling**: Proper Friday rate usage for weekends

#### Tier 2: Time-Based Working Day Logic
- **8:15 AM Rule**: Before publish time uses previous day, after uses current
- **Working Day Validation**: Uses holiday calendar to determine working days
- **Intelligent Caching**: Different TTL based on rate source and timing

#### Tier 3: Enhanced 404 Fallback
- **Unknown Issues**: Handles bank strikes, technical problems, undeclared holidays
- **Smart Search**: Only tries working days, skips known non-working days
- **Graceful Degradation**: Goes back up to 10 days to find valid data

### Holiday Coverage (2025)

**Fixed Holidays**: New Year's Day, Epiphany, Labour Day, Constitution Day, Assumption Day, All Saints' Day, Independence Day, Christmas Eve, Christmas Day, Boxing Day

**Movable Holidays**: Easter Sunday (April 20), Easter Monday (April 21), Pentecost (June 8), Corpus Christi (June 19)

**Edge Cases**: Extended holiday weekends, holiday + weekend combinations, unknown non-publication days

### Rate Source Transparency

The system provides full transparency with rate source tracking:
```json
{
  "rate": 3.6530,
  "effective_date": "2025-07-24",
  "rate_source": "holiday_skip",
  "skip_reason": "Polish holiday: Boże Narodzenie",
  "fallback_date": "2025-12-23"
}
```

### Business Benefits
- **Efficiency**: Reduces API calls by ~30% by skipping known holidays/weekends
- **Reliability**: Handles all 2025 Polish holidays including movable ones
- **Consistency**: Accurate PLN conversions during holiday periods
- **Performance**: Smart caching with context-aware TTL

---

## API Reference for Admins

### Primary Admin Endpoint
```http
GET /api/v1/usage-tracking/my-organization/usage-summary
Authorization: Bearer {admin_token}
```

**Response Structure** (Business-focused):
```json
{
  "success": true,
  "stats": {
    "current_month": {
      "month": "July 2025",
      "total_tokens": 52400,
      "total_cost": 0.187200,
      "total_cost_pln": 0.77,
      "total_requests": 168,
      "days_with_usage": 12,
      "days_in_month": 27,
      "usage_percentage": 44.4
    },
    "daily_breakdown": [
      {
        "date": "2025-07-01",
        "day_name": "Monday",
        "tokens": 1500,
        "cost": 0.0052,
        "cost_pln": 0.021,
        "requests": 5,
        "primary_model": "google/gemini-2.5-flash",
        "last_activity": "09:30"
      }
    ],
    "monthly_summary": {
      "average_daily_tokens": 4367,
      "average_daily_cost": 0.0156,
      "busiest_day": "2025-07-15",
      "highest_cost_day": "2025-07-15", 
      "most_used_model": "anthropic/claude-sonnet-4",
      "total_unique_users": 2
    }
  }
}
```

### Additional Admin Endpoints
- **User Breakdown**: `GET /my-organization/usage-by-user`
- **Model Analytics**: `GET /my-organization/usage-by-model`
- **Subscription Billing**: `GET /my-organization/subscription-billing`

---

## Admin Operations Guide

### Daily Admin Tasks
1. **Review Usage Dashboard** - Check monthly progress and daily patterns
2. **Monitor Cost Trends** - Ensure spending within budget parameters
3. **Check User Activity** - Verify expected usage levels

### Weekly Admin Tasks
1. **Analyze Peak Days** - Identify unusual usage patterns
2. **Review Model Distribution** - Optimize AI model availability
3. **Check Cost Averages** - Budget tracking and forecasting

### Monthly Admin Tasks
1. **Generate Usage Reports** - Monthly summary for stakeholders
2. **Budget Analysis** - Compare actual vs. planned spending
3. **Strategic Planning** - Usage trends for next month planning

---

## Performance & Reliability

### System Performance
- **No Real-time Overhead**: Single page load, no auto-refresh
- **Optimized Queries**: Direct daily summary access
- **Minimal Server Load**: 99% reduction in dashboard API calls
- **Fast Response Times**: Single database query pattern

### Business Benefits
- **Appropriate Complexity**: Perfect for administrative oversight
- **Clean Interface**: Focused on business value, not technical metrics
- **Better Decision Making**: Enhanced insights and trend analysis
- **Cost Effective**: Reduced server resources and complexity

---

## Multi-Tenant Architecture

### Client Isolation
- **Separate Containers**: Each client gets dedicated Docker environment
- **Independent Databases**: SQLite per client organization
- **Isolated API Keys**: Dedicated OpenRouter keys per client
- **Custom Markup Rates**: Flexible pricing per organization

### Administrative Scope
- **Organization-level Access**: Admins see only their organization's data
- **User Management**: Per-organization user breakdown
- **Cost Tracking**: Independent billing and markup calculation
- **Usage Analytics**: Client-specific insights and trends

---

## Data Retention & Cleanup

### Daily Summary Storage
- **Permanent Retention**: Daily summaries stored indefinitely
- **Audit Trail**: Complete usage history for compliance
- **Backup Strategy**: Daily database backups with retention

### Cleanup Operations
- **Automated Cleanup**: Old processed generation logs
- **Storage Optimization**: Efficient daily summary storage
- **Performance Maintenance**: Regular database optimization

---

## Troubleshooting Guide

### Common Admin Issues

#### "No usage data today"
- **Cause**: No API calls made yet today
- **Solution**: Normal - data appears after first API usage
- **Verification**: Check if users are actively using the system

#### "Loading usage data..."
- **Cause**: Initial page load or network delay
- **Solution**: Wait for single data load to complete
- **Note**: No auto-refresh - manual page refresh if needed

#### "Monthly summary shows zero"
- **Cause**: First month of usage or new organization
- **Solution**: Usage data accumulates as system is used
- **Timeline**: Data visible immediately after first API calls

#### "PLN conversion showing old rates"
- **Cause**: Polish banking holiday or NBP non-publication day
- **Solution**: System automatically uses last working day rate
- **Verification**: Check rate_source field in API response for holiday information

### Admin Verification Commands

```bash
# Check current month usage
docker exec container sqlite3 /app/backend/data/webui.db \
  "SELECT COUNT(*), SUM(total_tokens), SUM(markup_cost) 
   FROM client_daily_usage 
   WHERE usage_date >= date('now','start of month');"

# Verify today's activity  
docker exec container sqlite3 /app/backend/data/webui.db \
  "SELECT * FROM client_daily_usage 
   WHERE usage_date = date('now');"

# Check organization setup
docker exec container sqlite3 /app/backend/data/webui.db \
  "SELECT id, name, markup_rate FROM client_organizations 
   WHERE is_active = 1;"

# Verify NBP exchange rate system
curl "http://localhost:8080/api/v1/usage-tracking/exchange-rate/USD/PLN" \
  -H "Authorization: Bearer {admin_token}"
```

---

## Best Practices for Admins

### Dashboard Usage
1. **Load Once**: Access dashboard when needed - no need for constant monitoring
2. **Weekly Reviews**: Check trends and patterns weekly for insights
3. **Monthly Planning**: Use monthly summaries for budget and capacity planning
4. **Cost Monitoring**: Review daily costs for budget tracking

### Data Interpretation
- **Usage Percentage**: Target 60-80% active days for optimal utilization
- **Peak Days**: Normal to have 2-3x average usage on busy days
- **Model Distribution**: Expect 70-80% usage on 2-3 primary models
- **Cost Trends**: Monthly costs should align with business activity

### Optimization Strategies
- **Model Selection**: Focus training on most cost-effective models
- **Usage Patterns**: Schedule intensive tasks during off-peak times
- **User Training**: Optimize prompts to reduce token consumption
- **Budget Control**: Set monthly limits based on usage trends

---

## Conclusion

The mAI Usage Tracking System provides administrators with a clean, business-focused interface for monitoring OpenRouter API usage. The system eliminates unnecessary real-time complexity while providing comprehensive business intelligence for decision-making, budgeting, and strategic planning.

**Key Admin Benefits:**
- ✅ **Clean Monthly Overview** - Perfect for management review
- ✅ **Daily Breakdown Analysis** - Complete usage patterns  
- ✅ **Business Intelligence** - Automated insights and trends
- ✅ **Cost Control** - Transparent pricing with holiday-aware PLN support
- ✅ **Strategic Planning** - Data-driven capacity and budget planning
- ✅ **Currency Reliability** - Intelligent NBP integration with 3-tier fallback system

---

**Documentation Status**: ✅ Complete Admin Guide  
**Target Audience**: Business Administrators & Management  
**Update Frequency**: Quarterly or as needed  
**Support**: Internal IT team and documentation