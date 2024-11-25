import logging
import os
import tempfile
import git
import shutil
import mimetypes
import base64
from pathlib import Path
from typing import Optional, List

from langchain.vectorstores import FAISS
from langchain.docstore.document import Document
from backend.open_webui.config import PersistentConfig
from backend.open_webui.apps.ollama.main import generate_ollama_embeddings
from pydantic import BaseModel

from PyPDF2 import PdfReader
from PIL import Image
import pytesseract
from dotenv import load_dotenv

load_dotenv()

# Load environment variables from .env file
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

log = logging.getLogger(__name__)

class GenerateEmbeddingsForm(BaseModel):
    model: str
    input: list[str]


# Helper functions for encoding/decoding
def encode_content(content: str) -> str:
    """
    Encode content to Base64 for safe transfer.
    """
    return base64.b64encode(content.encode("utf-8")).decode("utf-8")


def decode_content(encoded_content: str) -> str:
    """
    Decode Base64 content back to original.
    """
    return base64.b64decode(encoded_content.encode("utf-8")).decode("utf-8")


def is_text_file(file_path: str) -> bool:
    """
    Helper function to determine if a file is text-based or binary.
    """
    text_extensions = {".txt", ".md", ".py", ".js", ".json", ".html", ".css", ".scss"}
    binary_extensions = {".png", ".jpg", ".jpeg", ".pdf", ".docx"}
    file_extension = Path(file_path).suffix.lower()

    if file_extension in text_extensions or file_extension in binary_extensions:
        return True
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type is not None and mime_type.startswith("text")


def process_file_content(file_path: str) -> Optional[str]:
    """
    Process content of a file based on its type (text, PDF, image, or other).
    Encode content to Base64 for safe transfer.
    """
    try:
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and mime_type.startswith("text"):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                return encode_content(content)
        elif mime_type == "application/pdf":
            reader = PdfReader(file_path)
            content = " ".join([page.extract_text() or '' for page in reader.pages])
            return encode_content(content)
        elif mime_type and mime_type.startswith("image"):
            image = Image.open(file_path)
            content = pytesseract.image_to_string(image)
            return encode_content(content)
        else:
            return None  # Skip unsupported files
    except Exception as e:
        log.error(f"Error processing file {file_path}: {e}")
        return None  # Skip files with errors


def add_context_to_code(file_path: str, raw_content: str) -> str:
    """
    Add context to the raw content for better understanding by Ollama.
    """
    language = Path(file_path).suffix.lower().lstrip(".")
    context = (
        f"This is a {language} code file named {file_path}. Below is the content of the file:\n\n"
    )
    return context + raw_content



def load_docs_from_files(file_paths: List[str]) -> List[Document]:
    """
    Load and process files from various formats into documents with context.
    """
    docs = []
    for path in file_paths:
        try:
            content = process_file_content(path)
            if content:
                contextualized_content = add_context_to_code(path, content)
                docs.append(Document(page_content=contextualized_content, metadata={"path": path}))
        except Exception as e:
            log.error(f"Error reading file {path}: {e}")
    log.info(f"Loaded {len(docs)} documents from {len(file_paths)} files.")
    return docs


def get_embeddings_from_ollama(documents, model="qwen2.5-coder:7b", retries=3):
    """
    Generate embeddings using Ollama's API with retry logic.
    """
    for attempt in range(retries):
        try:
            valid_docs = [doc for doc in documents if doc.page_content.strip()]
            if not valid_docs:
                raise ValueError("No valid documents with content to process.")

            log.info(f"Sending {len(valid_docs)} documents to Ollama for embeddings.")
            form_data = GenerateEmbeddingsForm(
                model=model,
                input=[doc.page_content for doc in valid_docs],
            )

            response = generate_ollama_embeddings(form_data=form_data)
            if "embedding" in response and response["embedding"]:
                embeddings = response["embedding"]
                return list(zip(valid_docs, embeddings))
        except Exception as e:
            log.error(f"Attempt {attempt+1} failed: {e}")
    raise ValueError("Failed to fetch embeddings from Ollama after retries.")


# Core functions
async def setup_github_rag_loader(repo_url: str):
    """
    RAG setup function for GitHub repository.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        # Clone GitHub repository to a temporary directory
        log.info(f"Cloning repository: {repo_url}")
        git.Repo.clone_from(
            f"https://{GITHUB_TOKEN}@github.com/{repo_url}.git", temp_dir, branch=GITHUB_BRANCH
        )
        log.info(f"Repository cloned to {temp_dir}")

        # Load documents from all files in the repository
        file_paths = [str(f) for f in Path(temp_dir).rglob("*") if f.is_file()]
        log.info(f"Found {len(file_paths)} files in the repository.")

        docs = load_docs_from_files(file_paths)

        # Generate embeddings using Ollama
        embedded_docs = get_embeddings_from_ollama(docs)
        if not embedded_docs:
            raise ValueError("No embeddings generated.")

        docs, embeddings = zip(*embedded_docs)

        # Set up vector database
        vector_db = FAISS()
        vector_db.add_texts([doc.page_content for doc in docs], embeddings)
        log.info("Vector database created successfully.")
        return vector_db
    finally:
        shutil.rmtree(temp_dir)
        log.info(f"Temporary directory {temp_dir} removed.")


async def ask_github_rag(query: str, vector_db):
    """
    Query function for RAG approach.
    """
    docs = vector_db.similarity_search(query)
    response = "\n".join([decode_content(doc.page_content) for doc in docs])
    return response


async def load_data(data_type: str, approach: str, query: Optional[str] = None, repo_url: Optional[str] = None) -> str:
    """
    Main function to load data based on type and approach.
    """
    if data_type == "GitHub":
        if approach == "rag":
            # Use RAG approach
            vector_db = await setup_github_rag_loader(repo_url)
            response = await ask_github_rag(query, vector_db)
            return response
        else:
            raise ValueError("Invalid approach for GitHub")
    else:
        raise ValueError("Unsupported data type")