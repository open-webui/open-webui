# Root Files Reorganization Plan

## Current Analysis

### Files with Dependencies (CRITICAL - Cannot Move)
- `generate_client_env.py` - Referenced in multiple docs and imported by `generate_client_env_dev.py`
- `generate_client_env_dev.py` - Imports from `generate_client_env.py`

### Proposed Folder Structure

#### `/tools/` - Utility and Management Scripts
- `setup_usage_tracking.py` - Initial system setup
- `set_model_filtering.py` - Model configuration
- `compare_pricing_data.py` - Data analysis utility
- `hatch_build.py` - Build utility

#### `/tools/database/` - Database Management
- `database_cleanup_analysis.py` - Database analysis
- `database_cleanup_script.py` - Database cleanup operations
- `database_cleanup_analysis.json` - Analysis results
- `database_cleanup_report.json` - Cleanup reports

#### `/tools/verification/` - System Verification Scripts
- `verify_docker_database_schema.py` - Schema verification
- `verify_model_pricing.py` - Pricing verification  
- `verify_recent_usage.py` - Usage verification
- `verify_subscription.py` - Subscription verification
- `debug_client_org_lookup.py` - Debug utility

#### `/testing/` - Test Scripts
- `test_business_focused_usage.py` - Business usage tests
- `test_holiday_scenarios.py` - Holiday testing
- `test_nbp_integration.py` - NBP API tests
- `test_simplified_usage.py` - Simplified usage tests
- `test_subscription_billing_calendar.py` - Billing tests

#### `/docs/analysis/` - Analysis Documentation
- `DATABASE_ARCHITECTURE_ANALYSIS.md` - Database analysis
- `AUTOMATIC_INITIALIZATION_IMPLEMENTATION.md` - Implementation docs
- `PRODUCTION_READY_SOLUTION.md` - Production documentation
- `NBP Web API.md` - API documentation
- `user_mapping_deployment_report.md` - Deployment report
- `test_ui_simplified.md` - UI testing documentation

#### Keep in Root (Referenced or Critical)
- `generate_client_env.py` - Heavily referenced in documentation
- `generate_client_env_dev.py` - Imports from generate_client_env.py
- `claude.md` - Project instructions
- `README.md` - Main project documentation
- Configuration files (package.json, tsconfig.json, etc.)
- `cleanup_backup_scripts.sh` - Recent utility script

## Safety Measures
1. Move files gradually, testing each category
2. Update any import statements if needed
3. Update documentation references if necessary
4. Test system functionality after each move

## Implementation Strategy
1. Create folder structure first
2. Move non-critical files (tools, testing, docs)
3. Verify no functionality is broken
4. Update any broken references