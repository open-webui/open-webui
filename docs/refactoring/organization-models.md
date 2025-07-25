# Organization Models Refactoring

## Overview

The `organization_usage.py` file (1,381 lines) has been refactored into a well-organized package structure following SOLID principles and maintaining 100% backward compatibility.

## New Structure

```
backend/open_webui/models/
├── organization_usage.py          # Legacy file for backward compatibility (20 lines)
└── organization/                  # New package with domain-separated modules
    ├── __init__.py               # Re-exports all classes (103 lines)
    ├── global_settings.py        # Global settings models (72 lines)
    ├── generation_processing.py  # Generation tracking models (161 lines)
    ├── client_organization.py    # Client & user mapping models (232 lines)
    └── usage_tracking.py         # Usage tracking models (354 lines)
```

## Benefits

1. **Better Organization**: Each file now has a single responsibility
2. **Improved Maintainability**: Easier to find and modify specific functionality
3. **Reduced File Size**: Average file size reduced from 1,381 to ~230 lines
4. **100% Backward Compatible**: All existing imports continue to work

## Module Breakdown

### global_settings.py
- `GlobalSettings` - Database model for global settings
- `GlobalSettingsModel` - Pydantic model
- `GlobalSettingsForm` - Form validation
- `GlobalSettingsTable` - Service class

### generation_processing.py
- `ProcessedGeneration` - Track processed OpenRouter generations
- `ProcessedGenerationCleanupLog` - Cleanup audit logs
- `ProcessedGenerationTable` - Service class with cleanup logic

### client_organization.py
- `ClientOrganization` - Client organization model
- `UserClientMapping` - User to client mapping
- Related Pydantic models and service classes

### usage_tracking.py
- `ClientDailyUsage` - Daily usage summaries
- `ClientUserDailyUsage` - Per-user daily usage
- `ClientModelDailyUsage` - Per-model daily usage
- `ClientLiveCounters` - Real-time usage counters
- `ClientUsageTable` - Comprehensive usage tracking service

## Migration

No migration needed! The refactoring maintains 100% backward compatibility:

```python
# Old import (still works)
from open_webui.models.organization_usage import ClientOrganization

# New import (also works)
from open_webui.models.organization import ClientOrganization

# Or import from specific module
from open_webui.models.organization.client_organization import ClientOrganization
```

## Singleton Instances

The following singleton instances are preserved:
- `GlobalSettingsDB`
- `ClientOrganizationDB`
- `UserClientMappingDB`
- `ClientUsageDB`
- `ProcessedGenerationDB`

## Next Steps

1. Consider similar refactoring for other large files
2. Add unit tests for each module
3. Update imports in new code to use the organization package directly