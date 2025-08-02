# E2E Usage Processing Tests

## Overview

This comprehensive end-to-end test suite verifies the complete usage processing cycle in the mAI system, from webhook registration through batch processing to final PLN conversion.

## Test Scenario

The main E2E test simulates the following business workflow:

1. **Environment Setup**: Configure mock time (July 31, 2025) and NBP exchange rate (4.50 PLN/USD)
2. **Usage Registration**: Send webhooks totaling 100,000 tokens costing $0.15 USD
3. **Real-time Verification**: Confirm data appears correctly in real-time APIs
4. **Time Advancement**: Simulate time change to August 1, 2025
5. **Batch Processing**: Run daily batch processor for July 31 data
6. **Final Verification**: Confirm PLN conversion (0.675 PLN) and zero usage for August 1

## Directory Structure

```
tests/
├── README.md                      # This file
├── requirements-test.txt          # Test dependencies
├── pytest.ini                     # Pytest configuration
├── conftest.py                    # Test fixtures and setup
├── run_e2e_tests.py              # Test runner script
├── test_usage_processing_e2e.py  # Main E2E test
├── utils/
│   └── test_helpers.py           # Test utilities
└── mocks/
    └── nbp_mock.py               # NBP service mock
```

## Prerequisites

### System Requirements
- Python 3.12+ (3.13+ preferred)
- SQLite database support
- Network access for HTTP requests

### Python Dependencies
Install test dependencies:
```bash
pip install -r requirements-test.txt
```

### Environment Setup
The tests automatically configure the test environment, but you can override settings:

```bash
export ENVIRONMENT=test
export DATABASE_URL=sqlite:///test_usage_processing.db
export INFLUXDB_ENABLED=true
export INFLUXDB_URL=http://localhost:8086
export NBP_SERVICE_URL=http://localhost:8001
export OPENROUTER_WEBHOOK_SECRET=test-webhook-secret
```

## Running Tests

### Quick Start
```bash
# Run all E2E tests
python3 run_e2e_tests.py

# Run with verbose output
python3 run_e2e_tests.py --verbose

# Run fast tests only (signature validation, duplicates)
python3 run_e2e_tests.py --fast
```

### Using pytest directly
```bash
# Run all E2E tests
pytest -v test_usage_processing_e2e.py

# Run specific test method
pytest -v test_usage_processing_e2e.py::TestUsageProcessingE2E::test_complete_usage_processing_cycle

# Run with detailed output
pytest -vv --tb=long test_usage_processing_e2e.py
```

### Test Categories

Tests are categorized with pytest markers:

```bash
# Run only E2E tests
pytest -m e2e

# Run only webhook tests
pytest -m webhook

# Run only batch processing tests  
pytest -m batch

# Run only database tests
pytest -m database
```

### Advanced Options

```bash
# Run specific test
python3 run_e2e_tests.py --test "test_complete_usage_processing_cycle"

# Skip prerequisite checks (for CI/CD)
python3 run_e2e_tests.py --no-prereq-check

# Cleanup test data only
python3 run_e2e_tests.py --cleanup-only
```

## Test Components

### Main E2E Test (`test_usage_processing_e2e.py`)

**TestUsageProcessingE2E** class contains:

- `test_complete_usage_processing_cycle()` - The main E2E test covering the full workflow
- `test_webhook_signature_validation()` - Tests webhook signature security
- `test_duplicate_webhook_handling()` - Tests duplicate request detection

### Test Utilities (`utils/test_helpers.py`)

**WebhookTestGenerator**: Creates realistic webhook payloads
- `generate_usage_payload()` - Single webhook
- `generate_batch_for_total()` - Multiple webhooks summing to specific totals
- `generate_signature()` - HMAC-SHA256 signatures

**DatabaseVerifier**: Verifies database state
- `verify_sqlite_usage_data()` - Check usage records
- `verify_exchange_rate_stored()` - Check exchange rates
- `clean_test_data()` - Cleanup after tests

**APITestClient**: HTTP client for API testing
- `send_webhook()` - Send webhook to API
- `get_usage_summary()` - Get usage data
- `trigger_manual_batch()` - Trigger batch processing

**TestDatabaseSetup**: Database setup and cleanup
- `setup_test_client()` - Create test organization
- `cleanup_test_client()` - Remove test data

### NBP Mock Service (`mocks/nbp_mock.py`)

**NBPMockService**: Controlled exchange rate responses
- `set_mock_rate()` - Configure rate for specific date
- `get_usd_pln_rate()` - Mock NBP API response
- Context manager support for easy setup/teardown

## Test Assertions

The E2E test includes three critical assertions:

### Assertion 1: Real-time Data Verification
- ✅ Tokens: 100,000
- ✅ Cost USD: ~$0.15 (with markup)
- ✅ Data available in SQLite
- ✅ Data available in InfluxDB (if enabled)

### Assertion 2: PLN Conversion After Batch Processing
- ✅ Cost PLN: 0.675 PLN ($0.15 × 4.50 rate with markup)
- ✅ Exchange rate stored in database
- ✅ Source marked as "influxdb_batch"

### Assertion 3: Current Day Zero Usage
- ✅ August 1, 2025 shows zero usage
- ✅ No unexpected data leakage

## Mocking Strategy

### Time Manipulation
Tests use `freezegun` and `unittest.mock` to control system time:
- Mock `datetime.datetime.now()` and `datetime.date.today()`
- Simulate time progression from July 31 to August 1, 2025

### NBP Service Mocking
The NBP service is mocked to return controlled exchange rates:
- 4.50 PLN/USD for test dates
- Predictable responses for reliable testing

### Database Isolation
Each test uses isolated database state:
- Test-specific SQLite database
- Automatic cleanup after tests
- No impact on production data

## Troubleshooting

### Common Issues

**Import Errors**
```
ModuleNotFoundError: No module named 'open_webui'
```
Solution: Ensure you're running from the backend directory and PYTHONPATH is set correctly.

**Database Connection Errors**
```
sqlite3.OperationalError: database is locked
```
Solution: Run cleanup and ensure no other processes are using the test database.

**Webhook Signature Failures**
```
401 Unauthorized: Invalid signature
```
Solution: Check that the webhook secret matches between generator and API.

**Time Mock Issues**
```
Assertion failed: Expected date 2025-07-31, got 2025-01-31
```
Solution: Ensure time mocks are properly configured in fixtures.

### Debug Mode

For detailed debugging, enable verbose logging:

```bash
pytest -v -s --log-cli-level=DEBUG test_usage_processing_e2e.py
```

### Test Data Inspection

After test failures, inspect the database:

```bash
sqlite3 test_usage_processing.db
.tables
SELECT * FROM client_daily_usage;
SELECT * FROM daily_exchange_rates;
```

## Performance Considerations

### Test Duration
- Complete E2E test: ~30-60 seconds
- Fast tests only: ~5-10 seconds
- Webhook validation tests: ~2-5 seconds

### Resource Usage
- Memory: ~100-200 MB during test execution
- Disk: ~10-50 MB for test databases and logs
- Network: Minimal (mocked external services)

### Parallel Execution

For faster execution with multiple test files:

```bash
pytest -n auto  # Requires pytest-xdist
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Usage Processing Tests

on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        cd backend/tests
        pip install -r requirements-test.txt
    
    - name: Run E2E tests
      run: |
        cd backend/tests
        python3 run_e2e_tests.py --no-prereq-check
```

### Docker Testing

Run tests in isolated Docker environment:

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY backend/ ./backend/
COPY backend/tests/requirements-test.txt ./

RUN pip install -r requirements-test.txt

CMD ["python3", "backend/tests/run_e2e_tests.py"]
```

## Contributing

### Adding New Tests

1. Create test methods in `TestUsageProcessingE2E` class
2. Use provided fixtures for setup (`mock_time_july_31`, `mock_nbp_service`, etc.)
3. Follow the naming convention: `test_<feature>_<scenario>`
4. Add appropriate pytest markers (`@pytest.mark.slow`, `@pytest.mark.webhook`, etc.)

### Extending Test Utilities

Add new helper functions to `utils/test_helpers.py`:
- Database verification methods
- API testing utilities
- Data generation functions

### Mock Service Enhancements

Extend `mocks/nbp_mock.py` for additional scenarios:
- Weekend rate handling
- Holiday schedules
- Error conditions

## Best Practices

### Test Design
- ✅ Each test should be independent and isolated
- ✅ Use descriptive test names that explain the scenario
- ✅ Include both positive and negative test cases
- ✅ Verify both happy path and error conditions

### Data Management
- ✅ Clean up test data after each test
- ✅ Use predictable test data for reliable assertions
- ✅ Avoid hardcoded dates that will become stale

### Mocking
- ✅ Mock external dependencies (NBP service, time)
- ✅ Use realistic mock data that matches production
- ✅ Test both mocked and error scenarios

### Assertions
- ✅ Use precise assertions with clear error messages
- ✅ Verify multiple aspects of the expected outcome
- ✅ Include negative assertions (what should NOT happen)

## Reporting and Monitoring

### Test Reports

HTML reports are generated automatically:

```bash
pytest --html=reports/e2e_report.html test_usage_processing_e2e.py
```

### Coverage Analysis

Generate code coverage reports:

```bash
pytest --cov=open_webui.usage_tracking --cov-report=html test_usage_processing_e2e.py
```

### Performance Profiling

Profile test performance:

```bash
pytest --profile test_usage_processing_e2e.py
```

## Support

For issues with the E2E test suite:

1. Check this README for troubleshooting steps
2. Review test logs for specific error messages
3. Ensure all prerequisites are installed and configured
4. Run individual test components to isolate issues
5. Use debug mode for detailed execution traces

The E2E test suite is designed to be robust and maintainable. It provides comprehensive coverage of the usage processing workflow while remaining fast enough for regular execution during development.