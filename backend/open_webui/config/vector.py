import logging
import os
from open_webui.env import DATA_DIR, DATABASE_URL, SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["CONFIG"])

####################################
# Vector Database
####################################

VECTOR_DB = os.environ.get("VECTOR_DB", "chroma")
log.info(f"VECTOR_DB: {VECTOR_DB}")

# Chroma
CHROMA_DATA_PATH = f"{DATA_DIR}/vector_db"

if VECTOR_DB == "chroma":
    import chromadb

    CHROMA_TENANT = os.environ.get("CHROMA_TENANT", chromadb.DEFAULT_TENANT)
    CHROMA_DATABASE = os.environ.get("CHROMA_DATABASE", chromadb.DEFAULT_DATABASE)
    CHROMA_HTTP_HOST = os.environ.get("CHROMA_HTTP_HOST", "")
    CHROMA_HTTP_PORT = int(os.environ.get("CHROMA_HTTP_PORT", "8000"))
    CHROMA_CLIENT_AUTH_PROVIDER = os.environ.get("CHROMA_CLIENT_AUTH_PROVIDER", "")
    CHROMA_CLIENT_AUTH_CREDENTIALS = os.environ.get(
        "CHROMA_CLIENT_AUTH_CREDENTIALS", ""
    )
    # Comma-separated list of header=value pairs
    CHROMA_HTTP_HEADERS = os.environ.get("CHROMA_HTTP_HEADERS", "")
    if CHROMA_HTTP_HEADERS:
        CHROMA_HTTP_HEADERS = dict(
            [pair.split("=") for pair in CHROMA_HTTP_HEADERS.split(",")]
        )
    else:
        CHROMA_HTTP_HEADERS = None
    CHROMA_HTTP_SSL = os.environ.get("CHROMA_HTTP_SSL", "false").lower() == "true"

# Milvus
MILVUS_URI = os.environ.get("MILVUS_URI", f"{DATA_DIR}/vector_db/milvus.db")
MILVUS_DB = os.environ.get("MILVUS_DB", "default")
MILVUS_TOKEN = os.environ.get("MILVUS_TOKEN", None)

MILVUS_INDEX_TYPE = os.environ.get("MILVUS_INDEX_TYPE", "HNSW")
MILVUS_METRIC_TYPE = os.environ.get("MILVUS_METRIC_TYPE", "COSINE")
MILVUS_HNSW_M = int(os.environ.get("MILVUS_HNSW_M", "16"))
MILVUS_HNSW_EFCONSTRUCTION = int(os.environ.get("MILVUS_HNSW_EFCONSTRUCTION", "100"))
MILVUS_IVF_FLAT_NLIST = int(os.environ.get("MILVUS_IVF_FLAT_NLIST", "128"))

# Qdrant
QDRANT_URI = os.environ.get("QDRANT_URI", None)
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", None)
QDRANT_ON_DISK = os.environ.get("QDRANT_ON_DISK", "false").lower() == "true"
QDRANT_PREFER_GRPC = os.environ.get("QDRANT_PREFER_GRPC", "false").lower() == "true"
QDRANT_GRPC_PORT = int(os.environ.get("QDRANT_GRPC_PORT", "6334"))
QDRANT_TIMEOUT = int(os.environ.get("QDRANT_TIMEOUT", "5"))
QDRANT_HNSW_M = int(os.environ.get("QDRANT_HNSW_M", "16"))
ENABLE_QDRANT_MULTITENANCY_MODE = (
    os.environ.get("ENABLE_QDRANT_MULTITENANCY_MODE", "true").lower() == "true"
)
QDRANT_COLLECTION_PREFIX = os.environ.get("QDRANT_COLLECTION_PREFIX", "open-webui")

# OpenSearch
OPENSEARCH_URI = os.environ.get("OPENSEARCH_URI", "https://localhost:9200")
OPENSEARCH_SSL = os.environ.get("OPENSEARCH_SSL", "true").lower() == "true"
OPENSEARCH_CERT_VERIFY = (
    os.environ.get("OPENSEARCH_CERT_VERIFY", "false").lower() == "true"
)
OPENSEARCH_USERNAME = os.environ.get("OPENSEARCH_USERNAME", None)
OPENSEARCH_PASSWORD = os.environ.get("OPENSEARCH_PASSWORD", None)

# ElasticSearch
ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL", "https://localhost:9200")
ELASTICSEARCH_CA_CERTS = os.environ.get("ELASTICSEARCH_CA_CERTS", None)
ELASTICSEARCH_API_KEY = os.environ.get("ELASTICSEARCH_API_KEY", None)
ELASTICSEARCH_USERNAME = os.environ.get("ELASTICSEARCH_USERNAME", None)
ELASTICSEARCH_PASSWORD = os.environ.get("ELASTICSEARCH_PASSWORD", None)
ELASTICSEARCH_CLOUD_ID = os.environ.get("ELASTICSEARCH_CLOUD_ID", None)
SSL_ASSERT_FINGERPRINT = os.environ.get("SSL_ASSERT_FINGERPRINT", None)
ELASTICSEARCH_INDEX_PREFIX = os.environ.get(
    "ELASTICSEARCH_INDEX_PREFIX", "open_webui_collections"
)

# Pgvector
PGVECTOR_DB_URL = os.environ.get("PGVECTOR_DB_URL", DATABASE_URL)
if VECTOR_DB == "pgvector" and not PGVECTOR_DB_URL.startswith("postgres"):
    raise ValueError(
        "Pgvector requires setting PGVECTOR_DB_URL or using Postgres with vector extension as the primary database."
    )
PGVECTOR_INITIALIZE_MAX_VECTOR_LENGTH = int(
    os.environ.get("PGVECTOR_INITIALIZE_MAX_VECTOR_LENGTH", "1536")
)

PGVECTOR_CREATE_EXTENSION = (
    os.getenv("PGVECTOR_CREATE_EXTENSION", "true").lower() == "true"
)
PGVECTOR_PGCRYPTO = os.getenv("PGVECTOR_PGCRYPTO", "false").lower() == "true"
PGVECTOR_PGCRYPTO_KEY = os.getenv("PGVECTOR_PGCRYPTO_KEY", None)
if PGVECTOR_PGCRYPTO and not PGVECTOR_PGCRYPTO_KEY:
    raise ValueError(
        "PGVECTOR_PGCRYPTO is enabled but PGVECTOR_PGCRYPTO_KEY is not set. Please provide a valid key."
    )


PGVECTOR_POOL_SIZE = os.environ.get("PGVECTOR_POOL_SIZE", None)

if PGVECTOR_POOL_SIZE != None:
    try:
        PGVECTOR_POOL_SIZE = int(PGVECTOR_POOL_SIZE)
    except Exception:
        PGVECTOR_POOL_SIZE = None

PGVECTOR_POOL_MAX_OVERFLOW = os.environ.get("PGVECTOR_POOL_MAX_OVERFLOW", 0)

if PGVECTOR_POOL_MAX_OVERFLOW == "":
    PGVECTOR_POOL_MAX_OVERFLOW = 0
else:
    try:
        PGVECTOR_POOL_MAX_OVERFLOW = int(PGVECTOR_POOL_MAX_OVERFLOW)
    except Exception:
        PGVECTOR_POOL_MAX_OVERFLOW = 0

PGVECTOR_POOL_TIMEOUT = os.environ.get("PGVECTOR_POOL_TIMEOUT", 30)

if PGVECTOR_POOL_TIMEOUT == "":
    PGVECTOR_POOL_TIMEOUT = 30
else:
    try:
        PGVECTOR_POOL_TIMEOUT = int(PGVECTOR_POOL_TIMEOUT)
    except Exception:
        PGVECTOR_POOL_TIMEOUT = 30

PGVECTOR_POOL_RECYCLE = os.environ.get("PGVECTOR_POOL_RECYCLE", 3600)

if PGVECTOR_POOL_RECYCLE == "":
    PGVECTOR_POOL_RECYCLE = 3600
else:
    try:
        PGVECTOR_POOL_RECYCLE = int(PGVECTOR_POOL_RECYCLE)
    except Exception:
        PGVECTOR_POOL_RECYCLE = 3600

# Pinecone
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY", None)
PINECONE_ENVIRONMENT = os.environ.get("PINECONE_ENVIRONMENT", None)
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "open-webui-index")
PINECONE_DIMENSION = int(os.getenv("PINECONE_DIMENSION", 1536))  # or 3072, 1024, 768
PINECONE_METRIC = os.getenv("PINECONE_METRIC", "cosine")
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")  # or "gcp" or "azure"

# ORACLE23AI (Oracle23ai Vector Search)
ORACLE_DB_USE_WALLET = os.environ.get("ORACLE_DB_USE_WALLET", "false").lower() == "true"
ORACLE_DB_USER = os.environ.get("ORACLE_DB_USER", None)  #
ORACLE_DB_PASSWORD = os.environ.get("ORACLE_DB_PASSWORD", None)  #
ORACLE_DB_DSN = os.environ.get("ORACLE_DB_DSN", None)  #
ORACLE_WALLET_DIR = os.environ.get("ORACLE_WALLET_DIR", None)
ORACLE_WALLET_PASSWORD = os.environ.get("ORACLE_WALLET_PASSWORD", None)
ORACLE_VECTOR_LENGTH = os.environ.get("ORACLE_VECTOR_LENGTH", 768)

ORACLE_DB_POOL_MIN = int(os.environ.get("ORACLE_DB_POOL_MIN", 2))
ORACLE_DB_POOL_MAX = int(os.environ.get("ORACLE_DB_POOL_MAX", 10))
ORACLE_DB_POOL_INCREMENT = int(os.environ.get("ORACLE_DB_POOL_INCREMENT", 1))


if VECTOR_DB == "oracle23ai":
    if not ORACLE_DB_USER or not ORACLE_DB_PASSWORD or not ORACLE_DB_DSN:
        raise ValueError(
            "Oracle23ai requires setting ORACLE_DB_USER, ORACLE_DB_PASSWORD, and ORACLE_DB_DSN."
        )
    if ORACLE_DB_USE_WALLET and (not ORACLE_WALLET_DIR or not ORACLE_WALLET_PASSWORD):
        raise ValueError(
            "Oracle23ai requires setting ORACLE_WALLET_DIR and ORACLE_WALLET_PASSWORD when using wallet authentication."
        )


S3_VECTOR_BUCKET_NAME = os.environ.get("S3_VECTOR_BUCKET_NAME", None)
S3_VECTOR_REGION = os.environ.get("S3_VECTOR_REGION", None)
