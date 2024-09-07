import base64
import os
import random
from pathlib import Path

import typer
import uvicorn

app = typer.Typer()

KEY_FILE = Path.cwd() / ".webui_secret_key"


@app.command()
def serve(
    host: str = "0.0.0.0",
    port: int = 8080,
):
    os.environ["FROM_INIT_PY"] = "true"
    if os.getenv("WEBUI_SECRET_KEY") is None:
        typer.echo(
            "Loading WEBUI_SECRET_KEY from file, not provided as an environment variable."
        )
        if not KEY_FILE.exists():
            typer.echo(f"Generating a new secret key and saving it to {KEY_FILE}")
            KEY_FILE.write_bytes(base64.b64encode(random.randbytes(12)))
        typer.echo(f"Loading WEBUI_SECRET_KEY from {KEY_FILE}")
        os.environ["WEBUI_SECRET_KEY"] = KEY_FILE.read_text()

    if os.getenv("USE_CUDA_DOCKER", "false") == "true":
        typer.echo(
            "CUDA is enabled, appending LD_LIBRARY_PATH to include torch/cudnn & cublas libraries."
        )
        LD_LIBRARY_PATH = os.getenv("LD_LIBRARY_PATH", "").split(":")
        os.environ["LD_LIBRARY_PATH"] = ":".join(
            LD_LIBRARY_PATH
            + [
                "/usr/local/lib/python3.11/site-packages/torch/lib",
                "/usr/local/lib/python3.11/site-packages/nvidia/cudnn/lib",
            ]
        )
    import open_webui.main  # we need set environment variables before importing main

    uvicorn.run(open_webui.main.app, host=host, port=port, forwarded_allow_ips="*")


@app.command()
def dev(
    host: str = "0.0.0.0",
    port: int = 8080,
    reload: bool = True,
):
    uvicorn.run(
        "open_webui.main:app",
        host=host,
        port=port,
        reload=reload,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    app()
