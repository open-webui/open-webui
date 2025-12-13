# RQ Worker File Processing Tests

This directory contains comprehensive tests for RQ worker file processing, including cleanup verification.

## Test Files

- `test_file_processor.py` - Comprehensive pytest tests for file processing and cleanup verification

## Running Tests

### With Conda Environment (rit4test)

```bash
# Activate conda environment
conda activate rit4test

# Run all worker tests
pytest backend/open_webui/test/apps/webui/workers/test_file_processor.py -v

# Run specific test
pytest backend/open_webui/test/apps/webui/workers/test_file_processor.py::TestFileProcessorCleanup::test_session_cleanup_called_on_success -v

# Run with coverage
pytest backend/open_webui/test/apps/webui/workers/test_file_processor.py --cov=open_webui.workers.file_processor --cov-report=html
```

### With Docker (Optional)

If you have Redis and PostgreSQL running in Docker:

```bash
# Set environment variables
export REDIS_URL=redis://localhost:6379
export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
export ENABLE_JOB_QUEUE=true

# Run tests
pytest backend/open_webui/test/apps/webui/workers/test_file_processor.py -v
```

### Standalone Verification Script

For quick verification without pytest:

```bash
conda activate rit4test
python test_worker_cleanup_verification.py
```

## Test Categories

### 1. Cleanup Verification Tests (`TestFileProcessorCleanup`)

- **test_session_cleanup_called_on_success**: Verifies `Session.remove()` is called on successful job completion
- **test_session_cleanup_called_on_error**: Verifies `Session.remove()` is called even when job fails
- **test_embedding_function_cleanup**: Verifies `EMBEDDING_FUNCTION` is cleaned up after job

### 2. Integration Tests (`TestFileProcessorIntegration`)

- **test_file_processing_job_structure**: Verifies cleanup code exists in source code
- **test_mock_request_cleanup_pattern**: Tests MockRequest/MockState cleanup patterns

### 3. Resource Leak Tests (`TestCleanupResourceLeaks`)

- **test_multiple_jobs_cleanup**: Verifies cleanup happens for each job in multiple job runs

## What is Tested

1. **Database Session Cleanup**
   - Verifies `Session.remove()` is called in finally block
   - Ensures cleanup happens on both success and error paths
   - Tests multiple jobs clean up properly

2. **Embedding Function Cleanup**
   - Verifies `EMBEDDING_FUNCTION` is set to `None` after job
   - Ensures per-job resources are released

3. **Code Structure**
   - Verifies finally block exists
   - Verifies cleanup code is in correct location
   - Verifies proper imports

## Environment Variables

The tests use the following environment variables (if available):

- `REDIS_URL` - Redis connection URL for job queue
- `DATABASE_URL` - PostgreSQL connection URL
- `ENABLE_JOB_QUEUE` - Enable/disable job queue (default: False)
- `RAG_EMBEDDING_ENGINE` - Embedding engine (e.g., "portkey", "openai")
- `RAG_EMBEDDING_MODEL` - Embedding model name

Tests will skip Redis/DB dependent tests if these are not configured.

## Test Output

Tests output detailed logging showing:
- ✅ Cleanup verification success
- ❌ Cleanup verification failure
- Test execution flow
- Resource cleanup confirmation

## Troubleshooting

### Import Errors

If you get import errors, ensure:
1. You're in the project root directory
2. Backend is in Python path
3. Conda environment has all dependencies installed

### Redis Connection Errors

If Redis tests fail:
- These tests are optional and will be skipped if Redis is not available
- Set `REDIS_URL` environment variable if Redis is running
- Or ignore Redis-related test failures (they're marked as integration tests)

### Database Connection Errors

If database tests fail:
- Tests use mocks by default, so DB connection is usually not needed
- Integration tests may require actual database connection
- Set `DATABASE_URL` if running integration tests

