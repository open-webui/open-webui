# Test/Apps/Webui/Storage Directory

This directory contains integration tests for Open WebUI's storage provider abstraction layer. The test file validates all four storage backend implementations (Local, S3, GCS, Azure) using mock cloud services, ensuring the unified storage interface works consistently across providers.

## Purpose

This directory provides:
- **Provider Abstraction Testing**: Validates `StorageProvider` interface implementation
- **Multi-Backend Coverage**: Tests Local, S3, GCS, and Azure storage providers
- **Mock Service Integration**: Uses moto, gcp-storage-emulator, and unittest.mock
- **Hybrid Configuration Testing**: Validates local + cloud hybrid caching
- **Upload/Download Workflows**: Tests file operations across all providers

## Files

### test_provider.py
**Purpose:** Comprehensive test suite for all storage provider implementations.

**File Size:** 18,927 bytes (extensive test coverage)

**Test Coverage:**

#### Import and Instantiation Tests
- `test_imports()` - Verifies all provider classes importable
- `test_get_storage_provider()` - Tests factory function for provider selection
- `test_class_instantiation()` - Validates abstract class cannot be instantiated
- `test_missing_abstract_methods()` - Ensures subclasses implement required methods

#### Local Storage Tests
- `test_local_upload_file()` - Upload file to local filesystem
- `test_local_download_file()` - Download file from local filesystem
- `test_local_delete_file()` - Delete file from local filesystem
- `test_local_list_files()` - List files in local directory
- `test_local_get_file()` - Get file metadata

#### S3 Storage Tests
- `test_s3_upload_file()` - Upload file to mock S3 bucket
- `test_s3_download_file()` - Download file from S3
- `test_s3_delete_file()` - Delete file from S3
- `test_s3_list_files()` - List S3 bucket contents
- `test_s3_get_file()` - Get file from S3 with local cache
- `test_s3_bucket_creation()` - Auto-create bucket if missing
- `test_s3_error_handling()` - Handle S3 API errors

#### GCS Storage Tests
- `test_gcs_upload_file()` - Upload file to mock GCS bucket
- `test_gcs_download_file()` - Download file from GCS
- `test_gcs_delete_file()` - Delete file from GCS
- `test_gcs_list_files()` - List GCS bucket contents
- `test_gcs_get_file()` - Get file from GCS with local cache
- `test_gcs_bucket_creation()` - Auto-create bucket if missing

#### Azure Blob Storage Tests
- `test_azure_upload_file()` - Upload file to mock Azure container
- `test_azure_download_file()` - Download file from Azure
- `test_azure_delete_file()` - Delete file from Azure
- `test_azure_list_files()` - List Azure container contents
- `test_azure_get_file()` - Get file from Azure with local cache
- `test_azure_container_creation()` - Auto-create container if missing

#### Hybrid Storage Tests
- `test_hybrid_cache()` - Local cache with cloud backend
- `test_hybrid_upload()` - Upload to both local and cloud
- `test_hybrid_download()` - Download from cache or cloud
- `test_hybrid_delete()` - Delete from both local and cloud

**Used by:**
- CI/CD pipelines testing storage provider integration
- Developers validating storage backend implementations
- Integration tests for file upload/download flows

**Uses:**
- `open_webui.storage.provider` - Storage provider implementations
- `moto` - AWS S3 mocking (`@mock_aws` decorator)
- `gcp_storage_emulator` - GCS mocking server
- `unittest.mock.MagicMock` - Azure Blob Storage mocking
- `boto3` - AWS SDK for S3 operations
- `google.cloud.storage` - GCS client library
- `azure.storage.blob` - Azure Blob Storage client

## Architecture & Patterns

### Mock Service Pattern
Tests use different mocking strategies for each cloud provider:

#### S3 Mocking (moto)
```python
from moto import mock_aws

@mock_aws
def test_s3_upload_file():
    # moto intercepts boto3 calls
    s3_client = boto3.client("s3")
    s3_client.create_bucket(Bucket="test-bucket")

    provider = S3StorageProvider()
    provider.upload_file(file_path, file_id)
    # File stored in moto's in-memory mock
```

**Benefits:**
- No AWS credentials required
- Fast (in-memory operations)
- Deterministic behavior
- Full S3 API coverage

#### GCS Mocking (gcp-storage-emulator)
```python
from gcp_storage_emulator.server import create_server

def setup_gcs_emulator():
    server = create_server(
        host="localhost",
        port=9023,
        in_memory=True
    )
    server.start()
    # Server intercepts GCS API calls

@pytest.fixture
def gcs_storage():
    setup_gcs_emulator()
    yield
    # Server automatically stops
```

**Benefits:**
- HTTP server emulation
- Close to real GCS behavior
- No Google Cloud credentials
- Supports bucket operations

#### Azure Mocking (unittest.mock)
```python
from unittest.mock import MagicMock

def test_azure_upload_file(monkeypatch):
    mock_blob_client = MagicMock()
    mock_blob_client.upload_blob.return_value = None

    monkeypatch.setattr(
        "azure.storage.blob.BlobServiceClient",
        lambda *args, **kwargs: mock_blob_client
    )

    provider = AzureStorageProvider()
    provider.upload_file(file_path, file_id)
    # Calls recorded on mock_blob_client
```

**Benefits:**
- Simplest approach (no external service)
- Full control over mock behavior
- Easy to test error conditions
- No network operations

### Fixture Pattern
Tests use pytest fixtures for test data setup:

```python
def mock_upload_dir(monkeypatch, tmp_path):
    """Fixture to monkey-patch UPLOAD_DIR and create temporary directory."""
    directory = tmp_path / "uploads"
    directory.mkdir()
    monkeypatch.setattr(provider, "UPLOAD_DIR", str(directory))
    return directory
```

**Benefits:**
- Isolated test environment
- Automatic cleanup (pytest temp directories)
- Repeatable test conditions
- No pollution of system directories

### Provider Factory Testing
Validates runtime provider selection:

```python
def test_get_storage_provider():
    Storage = provider.get_storage_provider("local")
    assert isinstance(Storage, provider.LocalStorageProvider)

    Storage = provider.get_storage_provider("s3")
    assert isinstance(Storage, provider.S3StorageProvider)

    with pytest.raises(RuntimeError):
        provider.get_storage_provider("invalid")
```

### Abstract Class Enforcement Testing
Ensures proper OOP design:

```python
def test_class_instantiation():
    # Cannot instantiate abstract class
    with pytest.raises(TypeError):
        provider.StorageProvider()

    # Cannot instantiate incomplete subclass
    with pytest.raises(TypeError):
        class IncompleteProvider(provider.StorageProvider):
            pass  # Missing abstract methods

        IncompleteProvider()
```

## Integration Points

### test/apps/webui/storage/ → storage/provider.py
**Primary Integration:** Tests validate storage provider implementations.

```python
# In test_provider.py
from open_webui.storage import provider

Storage = provider.get_storage_provider("s3")
Storage.upload_file(file_path, file_id)
# Calls storage/provider.py S3StorageProvider.upload_file()
```

### test/apps/webui/storage/ → Mock Services
**External Service Mocking:**

**S3 → moto:**
```
Test calls boto3.client("s3")
  ↓
@mock_aws intercepts
  ↓
moto returns mock S3 client
  ↓
Operations stored in memory
```

**GCS → gcp-storage-emulator:**
```
Test calls google.cloud.storage.Client()
  ↓
Emulator server intercepts HTTP requests
  ↓
Operations handled by emulator
  ↓
Returns mock responses
```

**Azure → unittest.mock:**
```
Test imports azure.storage.blob
  ↓
monkeypatch replaces with MagicMock
  ↓
All method calls recorded on mock
  ↓
Test verifies mock interactions
```

### test/apps/webui/storage/ → pytest
**Test Framework Integration:**

```python
# Fixtures
def test_something(tmp_path, monkeypatch):
    # tmp_path: Temporary directory (auto-cleanup)
    # monkeypatch: Attribute patching (auto-restore)
    pass

# Assertions
assert response.status_code == 200
assert file_content == expected_content
with pytest.raises(Exception):
    provider.invalid_operation()
```

## Key Workflows

### Local Storage Test Workflow
```
test_local_upload_file()
  ↓
Setup:
  1. Create temporary upload directory (tmp_path)
  2. Monkey-patch UPLOAD_DIR to tmp_path
  3. Get LocalStorageProvider instance
  ↓
Execute:
  1. Create test file with content
  2. Call provider.upload_file(file_path, file_id)
  3. LocalStorageProvider copies file to UPLOAD_DIR
  ↓
Assert:
  1. Verify file exists at UPLOAD_DIR / file_id
  2. Read file content
  3. Verify content matches original
  ↓
Cleanup:
  - pytest automatically removes tmp_path
```

### S3 Storage Test Workflow
```
test_s3_upload_file()
  ↓
Setup:
  1. @mock_aws decorator activates moto mocking
  2. Create mock S3 bucket
  3. Get S3StorageProvider instance
  ↓
Execute:
  1. Create test file
  2. Call provider.upload_file(file_path, file_id)
  3. S3StorageProvider calls boto3.client.upload_fileobj()
  4. moto intercepts and stores in memory
  ↓
Assert:
  1. Query mock S3 for object
  2. Download object content
  3. Verify content matches original
  ↓
Cleanup:
  - @mock_aws automatically clears moto state
```

### GCS Storage Test Workflow
```
test_gcs_upload_file()
  ↓
Setup:
  1. Start gcp-storage-emulator server
  2. Create mock GCS bucket
  3. Get GCSStorageProvider instance
  ↓
Execute:
  1. Create test file
  2. Call provider.upload_file(file_path, file_id)
  3. GCSStorageProvider calls storage.Bucket.blob.upload_from_file()
  4. Emulator server intercepts HTTP request
  5. Stores blob in memory
  ↓
Assert:
  1. Query emulator for blob
  2. Download blob content
  3. Verify content matches original
  ↓
Cleanup:
  - Emulator server stops automatically
```

### Azure Storage Test Workflow
```
test_azure_upload_file()
  ↓
Setup:
  1. Create MagicMock for BlobServiceClient
  2. Monkey-patch azure.storage.blob module
  3. Get AzureStorageProvider instance
  ↓
Execute:
  1. Create test file
  2. Call provider.upload_file(file_path, file_id)
  3. AzureStorageProvider calls blob_client.upload_blob()
  4. Mock records method call
  ↓
Assert:
  1. Verify upload_blob() called with correct args
  2. Verify blob name matches file_id
  3. Verify data stream provided
  ↓
Cleanup:
  - monkeypatch automatically restores original module
```

### Hybrid Storage Test Workflow
```
test_hybrid_cache()
  ↓
Setup:
  1. Configure S3StorageProvider with USE_LOCAL_CACHE=True
  2. Create temporary local cache directory
  3. Start mock S3 service
  ↓
Execute:
  1. Upload file via provider (goes to S3 + local cache)
  2. Call provider.get_file(file_id)
  3. Provider checks local cache first
  4. If cache hit: Return local path (fast)
  5. If cache miss: Download from S3, cache locally, return path
  ↓
Assert:
  1. First get_file(): Cache miss, downloads from S3
  2. Second get_file(): Cache hit, no S3 call
  3. Verify both return same file content
  4. Verify local cache file exists
```

## Important Notes

### Critical Dependencies
- **moto**: AWS service mocking (S3, IAM, etc.)
- **gcp-storage-emulator**: GCS HTTP emulator
- **unittest.mock**: Python standard library mocking
- **pytest**: Test framework with fixtures
- **boto3**: AWS SDK (mocked by moto)
- **google-cloud-storage**: GCS client (intercepted by emulator)
- **azure-storage-blob**: Azure client (mocked by unittest.mock)

### Configuration
**Environment Variables (for real providers, not tests):**
- `STORAGE_PROVIDER` - "local", "s3", "gcs", or "azure"
- `S3_BUCKET_NAME`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`
- `GCS_BUCKET_NAME`, `GCS_CREDENTIALS_PATH`
- `AZURE_STORAGE_ACCOUNT_NAME`, `AZURE_STORAGE_ACCOUNT_KEY`
- `USE_LOCAL_CACHE` - Enable hybrid mode (cloud + local cache)

**Test Configuration:**
- Tests override UPLOAD_DIR via monkeypatch
- Mock services use hardcoded test buckets/containers
- No real cloud credentials required

### Mock Service Behavior

**Moto (S3):**
- In-memory storage (no persistent state)
- Supports most S3 operations (PUT, GET, DELETE, LIST)
- Bucket creation automatic or manual
- No authentication required
- Fast (milliseconds)

**GCP Storage Emulator:**
- HTTP server (localhost:9023)
- Supports basic GCS operations
- Requires server start/stop
- In-memory storage option
- Slower than moto (~10-50ms per operation)

**Unittest.mock (Azure):**
- No actual storage (just method recording)
- Cannot verify actual file operations
- Fast (microseconds)
- Requires manual mock setup for each test
- Best for testing error handling

### Testing Strategies

**Unit Tests (Current):**
- Test each provider in isolation
- Mock external services
- Fast execution (<1 second per test)
- No cloud costs

**Integration Tests (Future):**
- Test against real cloud services
- Requires credentials
- Slower execution (network latency)
- Incurs cloud costs
- More realistic validation

### Performance Considerations
- **Local tests:** ~1-10ms per operation
- **S3 mock tests:** ~10-50ms per operation
- **GCS emulator tests:** ~50-100ms per operation
- **Azure mock tests:** ~1-5ms per operation

**Total test suite:** ~1-2 seconds for all storage tests

### Troubleshooting

**Moto Tests Fail:**
- Check moto version (4.0+ recommended)
- Verify @mock_aws decorator applied
- Ensure boto3 imported after decorator activation
- Check bucket name format (no underscores)

**GCS Emulator Tests Fail:**
- Verify gcp-storage-emulator installed
- Check port 9023 not in use
- Ensure STORAGE_EMULATOR_HOST environment set
- Verify emulator server started before test

**Azure Mock Tests Fail:**
- Check monkeypatch correctly applied
- Verify mock method signatures match real API
- Ensure mock return values realistic
- Validate mock call assertions

**File Not Found Errors:**
- Check tmp_path fixture used correctly
- Verify UPLOAD_DIR monkey-patched
- Ensure file created before upload test
- Check file_id path construction

### Security Considerations
- **Test isolation:** Each test uses fresh temporary directory
- **No credentials:** Mocks don't require real cloud credentials
- **No network access:** Tests don't make external calls
- **Cleanup:** pytest removes temporary files automatically

**Production vs. Test:**
- Tests use mock services (no security risk)
- Production uses real credentials (stored in environment)
- Never commit real credentials to test files

### Coverage

**Well Covered:**
- ✅ Provider factory selection
- ✅ Basic CRUD operations (upload, download, delete)
- ✅ Bucket/container auto-creation
- ✅ Local storage operations
- ✅ S3 operations (with moto)
- ✅ GCS operations (with emulator)
- ✅ Azure operations (with mocks)

**Not Covered:**
- ❌ Real cloud provider integration
- ❌ Network error handling (timeouts, retries)
- ❌ Large file uploads (>100MB)
- ❌ Concurrent operations (race conditions)
- ❌ Permission errors (IAM, access control)
- ❌ Cloud service outages (fallback behavior)
- ❌ Hybrid cache invalidation
- ❌ Storage quota limits

### Future Improvements
Potential enhancements:
- **Real cloud integration tests:** Optional CI stage with real credentials
- **Performance benchmarks:** Track upload/download speeds
- **Concurrent operation tests:** Thread-safe validation
- **Large file tests:** Multi-part upload handling
- **Error injection tests:** Simulate network failures
- **Cache invalidation tests:** Hybrid mode edge cases
- **Quota limit tests:** Handle storage limits gracefully
- **Encryption tests:** Validate encrypted storage providers
- **Compression tests:** Test compressed file handling
- **Metadata tests:** Validate file metadata storage/retrieval
