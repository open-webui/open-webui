import base64
import os
import random
from pathlib import Path

import typer
import uvicorn
from typing import Optional
from typing_extensions import Annotated

app = typer.Typer()

KEY_FILE = Path.cwd() / ".webui_secret_key"


def version_callback(value: bool):
    if value:
        from open_webui.env import VERSION

        typer.echo(f"Open WebUI version: {VERSION}")
        raise typer.Exit()


@app.command()
def main(
    version: Annotated[
        Optional[bool], typer.Option("--version", callback=version_callback)
    ] = None,
):
    pass


import os
import socket
import base64
import random
import typer
import uvicorn
from pathlib import Path

app = typer.Typer()
KEY_FILE = Path("secret.key")
initialization_done = False
dynamic_port = 8443  # Default port


def initialize_app():
    global initialization_done, dynamic_port

    # Step 1: Get the hostname
    tsi_hostname = socket.gethostname()
    os.environ["TSI_HOSTNAME"] = tsi_hostname

    # Step 2: Set port based on hostname
    fpga_hosts = [
        "fpga1.tsavoritesi.net",
        "fpga2.tsavoritesi.net",
        "fpga3.tsavoritesi.net",
        "fpga4.tsavoritesi.net",
    ]
    dynamic_port = 48443
    if tsi_hostname in fpga_hosts:
        dynamic_port = 8443
    else:
        dynamic_port = 48443

    initialization_done = True


@app.command()
def serve(
    host: str = "0.0.0.0",
    port: int = None,
):
    if not initialization_done:
        initialize_app()

    port = port or dynamic_port  # Use dynamic port if not provided

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
        try:
            import torch

            assert torch.cuda.is_available(), "CUDA not available"
            typer.echo("CUDA seems to be working")
        except Exception as e:
            typer.echo(
                "Error when testing CUDA but USE_CUDA_DOCKER is true. "
                "Resetting USE_CUDA_DOCKER to false and removing "
                f"LD_LIBRARY_PATH modifications: {e}"
            )
            os.environ["USE_CUDA_DOCKER"] = "false"
            os.environ["LD_LIBRARY_PATH"] = ":".join(LD_LIBRARY_PATH)

    import open_webui.main  # we need set environment variables before importing main
    from open_webui.env import UVICORN_WORKERS  # Import the workers setting

    uvicorn.run(
        "open_webui.main:app",
        host=host,
        port=port,
        ssl_keyfile=os.path.join(os.getcwd(), "key.pem"),
        ssl_certfile=os.path.join(os.getcwd(), "cert.pem"),
        forwarded_allow_ips="*",
        proxy_headers=True,
        workers=UVICORN_WORKERS,
    )


@app.command()
def dev(
    host: str = "0.0.0.0",
    port: int = None,
    reload: bool = True,
):
    if not initialization_done:
        initialize_app()

    port = port or dynamic_port  # Use dynamic port if not provided

    uvicorn.run(
        "open_webui.main:app",
        host=host,
        port=port,
        reload=reload,
        proxy_headers=True,
        ssl_keyfile=os.path.join(os.getcwd(), "key.pem"),
        ssl_certfile=os.path.join(os.getcwd(), "cert.pem"),
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    app()
