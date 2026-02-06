#!/usr/bin/env python3
"""
Entrypoint script for hardened Docker images (no shell available).
Replaces start.sh functionality for dhi.io hardened images.

This script handles:
- WEBUI_SECRET_KEY generation/loading
- CUDA LD_LIBRARY_PATH configuration
- HuggingFace Space deployment configuration
- Starting uvicorn with proper configuration
"""
import os
import sys
import secrets
import base64
from pathlib import Path


def main():
    # Change to script directory
    script_dir = Path(__file__).parent.resolve()
    os.chdir(script_dir)

    # Handle WEBUI_SECRET_KEY
    key_file = os.environ.get("WEBUI_SECRET_KEY_FILE", ".webui_secret_key")
    webui_secret_key = os.environ.get("WEBUI_SECRET_KEY", "")
    webui_jwt_secret_key = os.environ.get("WEBUI_JWT_SECRET_KEY", "")

    if not webui_secret_key and not webui_jwt_secret_key:
        print("Loading WEBUI_SECRET_KEY from file, not provided as an environment variable.")
        key_path = Path(key_file)
        
        # Ensure parent directory exists and is writable
        try:
            key_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # Fall back to /tmp if we can't write to the current directory
            key_path = Path("/tmp") / ".webui_secret_key"
        
        if not key_path.exists():
            print("Generating WEBUI_SECRET_KEY")
            # Generate a random value
            random_bytes = secrets.token_bytes(12)
            webui_secret_key = base64.b64encode(random_bytes).decode("utf-8")
            try:
                key_path.write_text(webui_secret_key)
            except PermissionError:
                print(f"Warning: Could not write secret key to {key_path}, using in-memory only")
        else:
            print(f"Loading WEBUI_SECRET_KEY from {key_file}")
            webui_secret_key = key_path.read_text().strip()

    if webui_secret_key:
        os.environ["WEBUI_SECRET_KEY"] = webui_secret_key

    # Handle CUDA LD_LIBRARY_PATH
    use_cuda_docker = os.environ.get("USE_CUDA_DOCKER", "").lower()
    if use_cuda_docker == "true":
        print("CUDA is enabled, appending LD_LIBRARY_PATH to include torch/cudnn & cublas libraries.")
        ld_library_path = os.environ.get("LD_LIBRARY_PATH", "")
        cuda_paths = "/app/.venv/lib/python3.11/site-packages/torch/lib:/app/.venv/lib/python3.11/site-packages/nvidia/cudnn/lib"
        os.environ["LD_LIBRARY_PATH"] = f"{ld_library_path}:{cuda_paths}" if ld_library_path else cuda_paths

    # Handle HuggingFace Space deployment
    space_id = os.environ.get("SPACE_ID")
    if space_id:
        print("Configuring for HuggingFace Space deployment")
        space_host = os.environ.get("SPACE_HOST", "")
        if space_host:
            os.environ["WEBUI_URL"] = space_host

    # Get configuration
    port = os.environ.get("PORT", "8080")
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn_workers = os.environ.get("UVICORN_WORKERS", "1")

    # Build uvicorn command arguments
    args = [
        "-m", "uvicorn",
        "open_webui.main:app",
        "--host", host,
        "--port", port,
        "--forwarded-allow-ips", "*",
    ]

    # Add workers if specified (must be > 0)
    try:
        workers = int(uvicorn_workers)
        if workers > 0:
            args.extend(["--workers", str(workers)])
    except ValueError:
        args.extend(["--workers", "1"])

    # Add any extra arguments passed to the script
    if len(sys.argv) > 1:
        args.extend(sys.argv[1:])

    print(f"Starting uvicorn: python {' '.join(args)}")
    
    # Use exec to replace the current process
    os.execvp(sys.executable, [sys.executable] + args)


if __name__ == "__main__":
    main()
