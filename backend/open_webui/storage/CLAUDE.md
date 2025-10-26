# Storage Directory

This directory provides a unified file storage abstraction layer supporting multiple backend storage providers: local filesystem, AWS S3, Google Cloud Storage (GCS), and Azure Blob Storage. It implements a common interface for uploading, downloading, and deleting files, allowing Open WebUI to be deployed in various infrastructure environments without code changes.

## Files in This Directory

### provider.py
**Purpose:** Storage provider abstraction and implementation for all supported storage backends.

**Key Components:**

#### StorageProvider (Abstract Base Class)
Defines the interface all storage providers must implement:

```python
class StorageProvider(ABC):
    @abstractmethod
    def get_file(self, file_path: str) -> str:
        """Download file and return local path"""
        pass

    @abstractmethod
    def upload_file(
        self, file: BinaryIO, filename: str, tags: Dict[str, str]
    ) -> Tuple[bytes, str]:
        """Upload file, return (contents, remote_path)"""
        pass

    @abstractmethod
    def delete_all_files(self) -> None:
        """Delete all files from storage"""
        pass

    @abstractmethod
    def delete_file(self, file_path: str) -> None:
        """Delete single file"""
        pass
```

#### LocalStorageProvider
**Purpose:** Store files on local filesystem.

**Storage Location:** `UPLOAD_DIR` environment variable (default: `./data/uploads`)

**Key Methods:**
- `upload_file(file, filename, tags)` - Write file to disk
  - Validates non-empty content
  - Returns: `(contents, local_file_path)`
- `get_file(file_path)` - Returns file path (no download needed)
- `delete_file(file_path)` - Delete file from filesystem
- `delete_all_files()` - Recursively delete all files in UPLOAD_DIR

**File Path Format:** `/data/uploads/{filename}`

**Used by:**
- All storage providers (as local cache)
- Single-server deployments

**Pros:**
- Simple, no external dependencies
- Fast access (no network latency)

**Cons:**
- Not scalable (single server only)
- No redundancy
- Limited by disk space

#### S3StorageProvider
**Purpose:** Store files in AWS S3 or S3-compatible storage (MinIO, DigitalOcean Spaces, etc.).

**Configuration (Environment Variables):**
- `S3_BUCKET_NAME` - S3 bucket name
- `S3_REGION_NAME` - AWS region (e.g., `us-east-1`)
- `S3_ENDPOINT_URL` - Custom endpoint (for S3-compatible services)
- `S3_ACCESS_KEY_ID` - AWS access key (optional if using IAM roles)
- `S3_SECRET_ACCESS_KEY` - AWS secret key (optional if using IAM roles)
- `S3_KEY_PREFIX` - Prefix for all keys (e.g., `open-webui/`)
- `S3_USE_ACCELERATE_ENDPOINT` - Enable S3 Transfer Acceleration
- `S3_ADDRESSING_STYLE` - `virtual` or `path` style addressing
- `S3_ENABLE_TAGGING` - Enable object tagging

**Key Methods:**
- `upload_file(file, filename, tags)` - Upload to S3
  - First saves to local filesystem
  - Uploads to S3 via boto3
  - Applies tags if enabled
  - Returns: `(contents, "s3://{bucket}/{key}")`
- `get_file(file_path)` - Download from S3 to local cache
  - Extracts S3 key from path
  - Downloads to UPLOAD_DIR
  - Returns local path
- `delete_file(file_path)` - Delete from S3 and local cache
- `delete_all_files()` - Delete all objects with key prefix

**File Path Format:** `s3://{bucket_name}/{key_prefix}/{filename}`

**Authentication Methods:**
1. **Explicit credentials**: Access key + secret key (environment variables)
2. **IAM roles**: Workload identity on EC2, EKS, ECS (no credentials needed)

**Helper Methods:**
- `sanitize_tag_value(s)` - Remove invalid characters from tags (S3 restrictions)
- `_extract_s3_key(full_file_path)` - Parse S3 key from full path
- `_get_local_file_path(s3_key)` - Convert S3 key to local cache path

**Used by:**
- Distributed deployments
- Cloud-native architectures (AWS, EKS)

**Pros:**
- Scalable storage
- High availability (99.999999999% durability)
- Versioning and lifecycle policies
- Works with S3-compatible services (MinIO, DigitalOcean)

**Cons:**
- Network latency for file access
- Costs for storage and bandwidth
- Requires local cache for performance

#### GCSStorageProvider
**Purpose:** Store files in Google Cloud Storage.

**Configuration (Environment Variables):**
- `GCS_BUCKET_NAME` - GCS bucket name
- `GOOGLE_APPLICATION_CREDENTIALS_JSON` - Service account JSON (optional)

**Key Methods:**
- `upload_file(file, filename, tags)` - Upload to GCS
  - First saves to local filesystem
  - Uploads to GCS via google-cloud-storage
  - Returns: `(contents, "gs://{bucket}/{filename}")`
- `get_file(file_path)` - Download from GCS to local cache
  - Extracts filename from path
  - Downloads blob to UPLOAD_DIR
  - Returns local path
- `delete_file(file_path)` - Delete from GCS and local cache
- `delete_all_files()` - Delete all blobs in bucket

**File Path Format:** `gs://{bucket_name}/{filename}`

**Authentication Methods:**
1. **Service account JSON**: Explicit credentials (environment variable)
2. **Application default credentials**: User credentials (local) or metadata server (GCE, GKE)

**Used by:**
- GCP deployments (GKE, Cloud Run)
- Google Cloud environments

**Pros:**
- Deep integration with GCP services
- Automatic authentication in GCP environments
- High durability and availability

**Cons:**
- Google Cloud vendor lock-in
- Network latency
- Requires local cache

#### AzureStorageProvider
**Purpose:** Store files in Azure Blob Storage.

**Configuration (Environment Variables):**
- `AZURE_STORAGE_ENDPOINT` - Storage account endpoint (e.g., `https://{account}.blob.core.windows.net`)
- `AZURE_STORAGE_CONTAINER_NAME` - Blob container name
- `AZURE_STORAGE_KEY` - Storage account key (optional if using managed identity)

**Key Methods:**
- `upload_file(file, filename, tags)` - Upload to Azure Blob Storage
  - First saves to local filesystem
  - Uploads blob with overwrite=True
  - Returns: `(contents, "{endpoint}/{container}/{filename}")`
- `get_file(file_path)` - Download from Azure to local cache
  - Extracts filename from path
  - Downloads blob to UPLOAD_DIR
  - Returns local path
- `delete_file(file_path)` - Delete from Azure and local cache
- `delete_all_files()` - Delete all blobs in container

**File Path Format:** `{endpoint}/{container}/{filename}`

**Authentication Methods:**
1. **Storage account key**: Explicit credentials (environment variable)
2. **Managed identity**: DefaultAzureCredential (AKS, Azure VMs)

**Used by:**
- Azure deployments (AKS, Azure App Service)
- Microsoft Azure environments

**Pros:**
- Native Azure integration
- Automatic authentication in Azure environments
- High availability and redundancy

**Cons:**
- Azure vendor lock-in
- Network latency
- Requires local cache

#### get_storage_provider(storage_provider)
**Purpose:** Factory function to instantiate correct storage provider based on configuration.

**Parameters:**
- `storage_provider` (str) - Provider name: "local", "s3", "gcs", "azure"

**Returns:** Instantiated StorageProvider object

**Raises:** RuntimeError if unsupported provider

**Usage:**
```python
Storage = get_storage_provider("s3")
contents, path = Storage.upload_file(file, "example.pdf", {"user": "123"})
```

#### Global Storage Instance
```python
Storage = get_storage_provider(STORAGE_PROVIDER)
```

**Purpose:** Singleton storage instance used throughout application

**Configuration:** `STORAGE_PROVIDER` environment variable

**Used by:**
- `routers/files.py` - File upload/download endpoints
- `routers/retrieval.py` - Document processing
- All modules needing file storage

## Architecture & Patterns

### Strategy Pattern
Storage providers implement the same interface, allowing runtime selection:

```python
# Configuration determines provider
STORAGE_PROVIDER = "s3"  # or "local", "gcs", "azure"

# Code remains the same regardless of provider
Storage = get_storage_provider(STORAGE_PROVIDER)
Storage.upload_file(file, filename, tags)
```

### Local Caching Pattern
Cloud storage providers use local filesystem as cache:

```
upload_file():
  1. Write to local filesystem (UPLOAD_DIR)
  2. Upload to cloud storage
  3. Return contents and remote path

get_file():
  1. Download from cloud storage
  2. Save to local filesystem (UPLOAD_DIR)
  3. Return local path for processing
```

This improves performance for subsequent operations on the same file.

### Hybrid Storage Pattern
Cloud providers maintain both local and remote copies:
- **Upload**: Local first, then remote
- **Delete**: Remove from both locations
- **Get**: Download to local cache if not exists

Benefits:
- Fast local access after first download
- Resilient (remote backup)
- Stateless (local cache can be cleared)

### Path Abstraction
Each provider uses its own path format:
- Local: `/data/uploads/{filename}`
- S3: `s3://{bucket}/{key}`
- GCS: `gs://{bucket}/{filename}`
- Azure: `{endpoint}/{container}/{filename}`

Code using Storage doesn't need to know the format.

## Integration Points

### routers/files.py → storage/provider.py
File router uses Storage singleton:

```python
# In routers/files.py
from open_webui.storage.provider import Storage

@app.post("/api/files")
async def upload_file(file: UploadFile):
    contents, file_path = Storage.upload_file(
        file.file,
        filename=generate_filename(),
        tags={"user_id": user.id}
    )

    # Save metadata to database
    Files.insert_new_file(
        user_id=user.id,
        path=file_path,
        filename=file.filename
    )
```

### routers/retrieval.py → storage/provider.py
RAG pipeline retrieves files for processing:

```python
# In routers/retrieval.py
from open_webui.storage.provider import Storage

def process_file(file_id):
    file_meta = Files.get_file_by_id(file_id)
    local_path = Storage.get_file(file_meta.path)

    # Process file (extract text, generate embeddings)
    loader = get_loader_for_file(local_path)
    documents = loader.load()
    # ...
```

### models/files.py → storage/provider.py
File model uses Storage for deletion:

```python
# In models/files.py
from open_webui.storage.provider import Storage

class Files:
    @staticmethod
    def delete_file_by_id(file_id):
        file = Files.get_file_by_id(file_id)

        # Delete from storage
        Storage.delete_file(file.path)

        # Delete from database
        session.query(File).filter_by(id=file_id).delete()
```

### Environment Configuration → storage/provider.py
Provider selection via environment:

```bash
# Local storage
export STORAGE_PROVIDER=local
export UPLOAD_DIR=/var/open-webui/uploads

# S3 storage
export STORAGE_PROVIDER=s3
export S3_BUCKET_NAME=my-bucket
export S3_REGION_NAME=us-east-1
export S3_ACCESS_KEY_ID=AKIA...
export S3_SECRET_ACCESS_KEY=secret...

# GCS storage
export STORAGE_PROVIDER=gcs
export GCS_BUCKET_NAME=my-bucket
export GOOGLE_APPLICATION_CREDENTIALS_JSON='{"type": "service_account", ...}'

# Azure storage
export STORAGE_PROVIDER=azure
export AZURE_STORAGE_ENDPOINT=https://myaccount.blob.core.windows.net
export AZURE_STORAGE_CONTAINER_NAME=my-container
export AZURE_STORAGE_KEY=key...
```

## Key Workflows

### File Upload Workflow
```
1. User uploads file via frontend
2. POST /api/files with multipart/form-data
3. Router: Storage.upload_file(file, filename, tags)
4. Provider: Write to local filesystem
5. Provider: Upload to cloud storage (if configured)
6. Provider: Return (contents, remote_path)
7. Router: Save metadata to database (Files table)
8. Router: Return file metadata to frontend
9. Frontend: Display upload success
```

### File Download Workflow
```
1. User requests file download
2. GET /api/files/{id}/content
3. Router: Get file metadata from database
4. Router: Storage.get_file(file.path)
5. Provider: Check if file in local cache
6. Provider: Download from cloud storage if not cached
7. Provider: Return local file path
8. Router: Stream file contents to frontend
9. Frontend: Browser downloads file
```

### File Deletion Workflow
```
1. User deletes file
2. DELETE /api/files/{id}
3. Router: Get file metadata
4. Router: Storage.delete_file(file.path)
5. Provider: Delete from cloud storage
6. Provider: Delete from local cache
7. Router: Delete from database
8. Router: Return success
9. Frontend: Remove file from UI
```

### RAG Document Processing Workflow
```
1. User uploads document for RAG
2. Upload workflow executes (see above)
3. POST /api/retrieval/process/file
4. Router: Storage.get_file(file.path)
5. Provider: Return local file path (from cache or download)
6. Router: Load document (PDF, Word, etc.)
7. Router: Extract text content
8. Router: Chunk text
9. Router: Generate embeddings
10. Router: Insert into vector database
11. File ready for semantic search
```

## Important Notes

### Critical Dependencies
- **Local**: No dependencies (built-in)
- **S3**: `boto3` Python library, AWS credentials or IAM role
- **GCS**: `google-cloud-storage` library, service account or workload identity
- **Azure**: `azure-storage-blob` library, storage key or managed identity

### Configuration
- `STORAGE_PROVIDER` determines which provider is used (default: "local")
- Each provider has its own configuration environment variables
- Invalid provider name raises RuntimeError at startup

### Performance Considerations
- **Local**: Fast, but limited scalability
- **Cloud**: Network latency (50-200ms per operation)
- **Local cache**: Reduces latency for repeated access
- **Batch operations**: Not yet implemented (consider for bulk uploads)

### Security Considerations
- **Local**: File permissions (ensure UPLOAD_DIR not publicly accessible)
- **S3**: Bucket policies, IAM roles, encryption at rest
- **GCS**: IAM policies, service account permissions
- **Azure**: RBAC, SAS tokens, encryption
- **Tags**: Sanitize user input (tag injection risk for S3)

### Scalability
- **Local**: Single-server only, no redundancy
- **S3/GCS/Azure**: Unlimited storage, high availability
- **Cache Management**: Local cache grows unbounded (consider cleanup job)

### Error Handling
- All providers raise RuntimeError on failures
- Network errors not retried (consider adding retry logic)
- Partial failures (upload succeeds, tagging fails) not handled
- No cleanup of orphaned files (local cache or cloud)

### Migration Between Providers
Changing storage providers requires data migration:
1. Set up new storage provider
2. Copy all files from old to new provider
3. Update database file paths
4. Switch STORAGE_PROVIDER environment variable
5. Verify all files accessible
6. Clean up old storage

No automated migration tool currently exists.

### Testing Considerations
- Mock Storage singleton for unit tests
- Use local provider for integration tests
- Test each provider separately (requires cloud accounts)
- Consider MinIO for S3 testing (S3-compatible, runs locally)
