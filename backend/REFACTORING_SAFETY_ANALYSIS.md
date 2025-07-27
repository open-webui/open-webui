# CRITICAL SAFETY ANALYSIS: organization_usage.py Refactoring

## FILE ANALYSIS
- **Current Size**: 1197 lines (EXCEEDS 700-line limit by 497 lines)
- **Production Status**: CRITICAL - serving 300+ users across 20 Docker instances
- **Business Logic**: Multi-tenant usage tracking with OpenRouter integration

## API CONTRACTS (MUST PRESERVE 100%)

### GlobalSettingsDB (Singleton Instance)
```python
# CRITICAL METHODS - PRESERVE EXACT SIGNATURES
def get_settings() -> Optional[GlobalSettingsModel]
def create_or_update_settings(settings_form: GlobalSettingsForm) -> Optional[GlobalSettingsModel]
```

### ClientOrganizationDB (Singleton Instance) 
```python
# CRITICAL METHODS - PRESERVE EXACT SIGNATURES
def create_client(client_form: ClientOrganizationForm, api_key: str, key_hash: str = None) -> Optional[ClientOrganizationModel]
def get_client_by_id(client_id: str) -> Optional[ClientOrganizationModel]
def get_client_by_api_key(api_key: str) -> Optional[ClientOrganizationModel]
def get_all_active_clients() -> List[ClientOrganizationModel]
def update_client(client_id: str, updates: dict) -> Optional[ClientOrganizationModel]
def deactivate_client(client_id: str) -> bool
```

### ClientUsageDB (Singleton Instance)
```python
# CRITICAL METHODS - PRESERVE EXACT SIGNATURES
def record_usage(client_org_id: str, user_id: str, openrouter_user_id: str, model_name: str, usage_date: date, input_tokens: int = 0, output_tokens: int = 0, raw_cost: float = 0.0, markup_cost: float = 0.0, provider: str = None, request_metadata: dict = None) -> bool
async def get_usage_stats_by_client(client_org_id: str, use_client_timezone: bool = True) -> ClientUsageStatsResponse
def get_usage_by_user(client_org_id: str, start_date: date = None, end_date: date = None) -> List[Dict[str, Any]]
def get_usage_by_model(client_org_id: str, start_date: date = None, end_date: date = None) -> List[Dict[str, Any]]
def get_all_clients_usage_stats(start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[ClientBillingResponse]
```

### ProcessedGenerationDB (Singleton Instance)
```python
# CRITICAL METHODS - PRESERVE EXACT SIGNATURES
def is_generation_processed(generation_id: str, client_org_id: str) -> bool
def mark_generation_processed(generation_id: str, client_org_id: str, generation_date: date, total_cost: float, total_tokens: int) -> bool
def cleanup_old_processed_generations(days_to_keep: int = 60) -> Dict[str, Any]
def get_processed_generations_stats(client_org_id: str, start_date: date = None, end_date: date = None) -> Dict[str, Any]
```

### UserClientMappingDB (Singleton Instance)
```python
# CRITICAL METHODS - PRESERVE EXACT SIGNATURES
def create_mapping(mapping_form: UserClientMappingForm) -> Optional[UserClientMappingModel]
def get_mapping_by_user_id(user_id: str) -> Optional[UserClientMappingModel]
def get_mappings_by_client_id(client_org_id: str) -> List[UserClientMappingModel]
def deactivate_mapping(user_id: str) -> bool
def update_mapping(user_id: str, updates: dict) -> bool
```

## DATABASE MODELS (MUST PRESERVE 100%)
- GlobalSettings, ProcessedGeneration, ProcessedGenerationCleanupLog
- ClientOrganization, UserClientMapping, ClientDailyUsage
- ClientUserDailyUsage, ClientModelDailyUsage
- ALL table schemas, indexes, and relationships

## PYDANTIC MODELS (MUST PRESERVE 100%)
- GlobalSettingsModel, ClientOrganizationModel, UserClientMappingModel
- ClientDailyUsageModel, ClientUserDailyUsageModel, ClientModelDailyUsageModel
- All form classes and response models

## EXTERNAL DEPENDENCIES ANALYSIS
**Files importing from organization_usage.py:**
1. `/backend/open_webui/utils/openrouter_client_manager.py`
2. `/backend/open_webui/routers/usage_tracking.py` 
3. `/backend/open_webui/utils/daily_batch_processor.py`
4. `/backend/tests/test_usage_tracking_integration.py`
5. Multiple test files and utility scripts

**Critical Usage Patterns:**
- Singleton instances: `GlobalSettingsDB`, `ClientOrganizationDB`, `ClientUsageDB`, etc.
- Async method: `get_usage_stats_by_client()` - PRESERVE async nature
- Database transactions with automatic rollback on error
- Complex business logic in `record_usage()` method
- Currency conversion integration with NBP API

## BUSINESS LOGIC CONTRACTS

### Core Business Rules (NEVER CHANGE):
1. **Multi-tenant isolation**: Each client has separate usage tracking
2. **Daily aggregation**: Usage is summarized daily for storage efficiency
3. **Duplicate prevention**: OpenRouter generations tracked to prevent double-billing
4. **Markup calculation**: 1.3x default markup rate applied to raw costs
5. **Currency conversion**: USD to PLN using NBP API with fallback
6. **Data retention**: 60-day retention for processed generations
7. **Database integrity**: All operations must be transactional

### Performance Requirements:
- Usage recording must be fast (< 100ms)
- Stats retrieval must handle large datasets
- Cleanup operations must be efficient
- Database indexes must be preserved

## REFACTORING SAFETY CHECKPOINTS

### Before Starting:
- [x] Git checkpoint created
- [x] Current functionality documented
- [x] API contracts identified
- [x] External dependencies mapped

### During Refactoring:
- [ ] Test imports after every file change
- [ ] Validate singleton instances remain functional
- [ ] Ensure async methods stay async
- [ ] Preserve all database transaction logic
- [ ] Test record_usage() after every modification

### After Each Incremental Change:
- [ ] Import test: `from open_webui.models.organization_usage import *`
- [ ] Singleton test: `GlobalSettingsDB.get_settings()`
- [ ] Database test: `ClientOrganizationDB.get_all_active_clients()`
- [ ] Complex method test: `ClientUsageDB.record_usage()`

## ROLLBACK TRIGGERS (IMMEDIATE STOP):
- Any import error
- Any signature change in public methods
- Any database schema modification
- Any change in singleton behavior
- Any async/sync method conversion
- Any response format change

## TARGET ARCHITECTURE (Clean Architecture + SOLID)
1. **Split into multiple files** (max 700 lines each)
2. **Repository pattern** for database operations
3. **Service layer** for business logic
4. **Domain models** separated from database models
5. **Dependency injection** for database connections
6. **Type safety** improvements with better type hints

## SUCCESS CRITERIA
- [x] File size reduced to < 700 lines per file
- [ ] All existing tests pass
- [ ] All API contracts preserved
- [ ] All singleton instances work identically
- [ ] All external imports continue working
- [ ] Performance characteristics unchanged
- [ ] Business logic 100% preserved