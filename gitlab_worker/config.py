import os


REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://ollama:11434')
OLLAMA_EMBEDDING_MODEL = os.environ.get('OLLAMA_EMBEDDING_MODEL', 'nomic-embed-text')

VECTOR_DB_PROVIDER = os.environ.get('VECTOR_DB_PROVIDER', 'chroma').lower()
VECTOR_DB_URL = os.environ.get('VECTOR_DB_URL', 'http://chroma:8000')

QDRANT_URL = os.environ.get('QDRANT_URL', 'http://qdrant:6333')
QDRANT_API_KEY = os.environ.get('QDRANT_API_KEY', '')
QDRANT_COLLECTION_PREFIX = os.environ.get('QDRANT_COLLECTION_PREFIX', 'gitlab')
QDRANT_ON_DISK = os.environ.get('QDRANT_ON_DISK', 'true').lower() == 'true'

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///./open-webui.db')
GITLAB_WORKER_ENABLED = os.environ.get('GITLAB_WORKER_ENABLED', 'true').lower() == 'true'
GITLAB_WORKER_LOG_LEVEL = os.environ.get('GITLAB_WORKER_LOG_LEVEL', 'INFO')

LOCAL_STORAGE_ENABLED = os.environ.get('LOCAL_STORAGE_ENABLED', 'true').lower() == 'true'
LOCAL_STORAGE_PATH = os.environ.get('LOCAL_STORAGE_PATH', '/app/data/repos')

CHUNK_SIZE = int(os.environ.get('CHUNK_SIZE', '1000'))
CHUNK_OVERLAP = int(os.environ.get('CHUNK_OVERLAP', '100'))

QUEUE_NAME = 'gitlab_sync_queue'