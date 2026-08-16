import os
import requests
import zipfile
from huggingface_hub import snapshot_download
from faster_whisper import WhisperModel

# Base directory for offline assets
BASE_DIR = os.path.abspath("./offline_assets")
TIKTOKEN_DIR = os.path.join(BASE_DIR, "tiktoken")
MODELS_DIR = os.path.join(BASE_DIR, "embedding_models")
WHISPER_DIR = os.path.join(BASE_DIR, "whisper_models")
NLTK_DIR = os.path.join(BASE_DIR, "nltk_data", "tokenizers")

# Create directories
for directory in [TIKTOKEN_DIR, MODELS_DIR, WHISPER_DIR, NLTK_DIR]:
    os.makedirs(directory, exist_ok=True)

print("==================================================")
print("1. Downloading Tiktoken cl100k_base Encoding")
print("==================================================")
tiktoken_url = "https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken"
# SHA256 of the URL string itself (used by tiktoken caching mechanism)
tiktoken_filename = "9b54673d56e7303b1666486777223657af14d400477771ba576103fe2801feea"
tiktoken_path = os.path.join(TIKTOKEN_DIR, tiktoken_filename)

if not os.path.exists(tiktoken_path):
    response = requests.get(tiktoken_url, stream=True)
    response.raise_for_status()
    with open(tiktoken_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print("✓ Tiktoken file downloaded successfully.")
else:
    print("✓ Tiktoken file already exists, skipping.")

print("\n==================================================")
print("2. Downloading HuggingFace Models")
print("==================================================")
models_to_download = [
    "sentence-transformers/all-MiniLM-L6-v2",
    "TaylorAI/bge-micro-v2",
    "BAAI/bge-reranker-base"
]

for repo_id in models_to_download:
    print(f"Downloading {repo_id}...")
    snapshot_download(repo_id=repo_id, cache_dir=MODELS_DIR)
    print(f"✓ {repo_id} downloaded.")

print("\n==================================================")
print("3. Downloading Whisper Audio Model (base)")
print("==================================================")
WhisperModel("base", device="cpu", compute_type="int8", download_root=WHISPER_DIR)
print("✓ Whisper model downloaded.")

print("\n==================================================")
print("4. Downloading NLTK Tokenizers (punkt & punkt_tab)")
print("==================================================")
nltk_files = {
    "punkt.zip": "https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/tokenizers/punkt.zip",
    "punkt_tab.zip": "https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/tokenizers/punkt_tab.zip",
}

for filename, url in nltk_files.items():
    zip_path = os.path.join(NLTK_DIR, filename)
    res = requests.get(url, stream=True)
    res.raise_for_status()
    with open(zip_path, "wb") as f:
        for chunk in res.iter_content(chunk_size=8192):
            f.write(chunk)
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(NLTK_DIR)
    os.remove(zip_path)
    print(f"✓ Extracted {filename} successfully.")

print("\n==================================================")
print("🎉 ALL ASSETS DOWNLOADED SUCCESSFULLY!")
print("==================================================")