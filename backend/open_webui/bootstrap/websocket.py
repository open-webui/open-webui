from fastapi import FastAPI

from open_webui.socket.main import app as socket_app


def mount_websocket_app(app: FastAPI) -> None:
    """Mount the websocket/socket.io sub-application."""
    app.mount("/ws", socket_app)
