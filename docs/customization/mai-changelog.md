# mAI Changelog

## 2025-01-26

### Fixed
- **Subscription Billing**: Updated pricing tiers to match business requirements
  - 1-3 users: 79 PLN per user/month
  - 4-9 users: 69 PLN per user/month
  - 10-19 users: 59 PLN per user/month
  - 20+ users: 54 PLN per user/month
- **Calendar Calculations**: Verified proportional billing correctly handles all month lengths (28, 29, 30, 31 days)
- **User Data Retrieval**: Fixed Users.get_users() integration to properly access user list from response object

### Technical Details
- Calendar-aware billing uses `calendar.monthrange()` for accurate day counts
- Proportional billing formula: `(days_remaining_in_month / total_days_in_month) * tier_price`
- Users added mid-month are billed only for remaining days
- Leap year February (29 days) handled automatically