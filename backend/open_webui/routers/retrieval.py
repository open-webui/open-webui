import os
from pinecone import Pinecone

# Load your Pinecone environment variables
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
#NAMESPACE = os.getenv("PINECONE_NAMESPACE")
NAMESPACE = os.getenv("default")

# Initialize Pinecone client
pc = Pinecone(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
index = pc.Index(INDEX_NAME)

# Delete all vectors from the specified namespace
print(f"🔄 Deleting all records from namespace '{NAMESPACE}' in index '{INDEX_NAME}'...")
index.delete(delete_all=True, namespace=NAMESPACE)
print("✅ Namespace wipe complete.")

find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +

find . -name "*.py" -exec grep -l "def process_file" {} \;

find . -name "retrieval.py" -exec ls -la {} \;

python3 -c "
import sys
import importlib

# All packages your refactored retrieval.py needs
required_packages = {
    'fastapi': 'FastAPI web framework',
    'pydantic': 'Data validation',
    'langchain_core': 'Document class',
    'langchain_text_splitters': 'Text splitting',
    'tiktoken': 'Token counting',
    'nltk': 'Natural language processing',
    'beautifulsoup4': 'HTML parsing',
    'unstructured': 'Document parsing',
    'openai': 'OpenAI API',
    'pinecone': 'Vector database (if using)',
    'chromadb': 'Vector database (if using)',
    'sentence_transformers': 'Embeddings',
    'python_pptx': 'PowerPoint processing',
    'python_docx': 'Word document processing (alternative)',
    'pypdf': 'PDF processing',
    'openpyxl': 'Excel processing',
    'requests': 'HTTP requests',
    'aiohttp': 'Async HTTP',
    'aiofiles': 'Async file operations'
}

print('=== DEPENDENCY CHECK ===')
missing = []
installed = []

for package, description in required_packages.items():
    try:
        # Handle special import names
        import_name = package
        if package == 'beautifulsoup4':
            import_name = 'bs4'
        elif package == 'python_pptx':
            import_name = 'pptx'
        elif package == 'python_docx':
            import_name = 'docx'
        
        mod = importlib.import_module(import_name)
        version = getattr(mod, '__version__', 'unknown')
        print(f'✅ {package}: {version} - {description}')
        installed.append(package)
    except ImportError as e:
        print(f'❌ {package}: MISSING - {description}')
        missing.append(package)

print(f'\n=== SUMMARY ===')
print(f'✅ Installed: {len(installed)}')
print(f'❌ Missing: {len(missing)}')

if missing:
    print(f'\nMissing packages: {missing}')
"
