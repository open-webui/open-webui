import os
from pathlib import Path
from starlette.types import Receive, Scope, Send
from starlette.staticfiles import StaticFiles
from starlette.responses import Response, FileResponse
from starlette.datastructures import Headers
from typing import List, Tuple, Optional


class GzipStaticFiles(StaticFiles):
    """
    A custom StaticFiles class that serves pre-compressed .gz files when available
    and the client supports gzip encoding.
    """
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handle a request to serve a static file, checking for a gzipped version first.
        """
        if scope["type"] != "http":
            await super().__call__(scope, receive, send)
            return

        request_headers = Headers(scope=scope)
        accepts_gzip = "gzip" in request_headers.get("accept-encoding", "").lower()
        
        if not accepts_gzip:
            # Client doesn't accept gzip, use regular file serving
            await super().__call__(scope, receive, send)
            return

        path = self.get_path(scope)
        full_path = self.get_file_path(path)
        gzip_path = Path(f"{full_path}.gz")

        if gzip_path.is_file():  # Just check if the gzip file exists
            # Serve the gzipped file with proper headers
            response = FileResponse(
                gzip_path,
                stat_result=os.stat(gzip_path),
                method=scope["method"],
                headers={"Content-Encoding": "gzip"},
            )
            await response(scope, receive, send)
        else:
            # Fallback to regular file serving
            await super().__call__(scope, receive, send)
    
    def get_file_path(self, path: str) -> Path:
        """Get the file path from the relative URL path."""
        normalized_path = path.lstrip("/")
        return Path(self.directory) / normalized_path
    
    def is_not_modified(self, response_headers, request_headers) -> bool:
        """Check if the file is not modified."""
        # Pass through to parent implementation
        return super().is_not_modified(response_headers, request_headers)


class GzipSPAStaticFiles(GzipStaticFiles):
    """
    Extends GzipStaticFiles to handle SPA routing by falling back to index.html.
    """
    
    async def get_response(self, path: str, scope):
        """
        Try to serve the requested path first, then fall back to index.html if needed.
        """
        try:
            return await super().get_response(path, scope)
        except Exception as ex:
            if getattr(ex, "status_code", None) == 404:
                if path.endswith(".js") or path.endswith(".css") or path.endswith(".woff") or path.endswith(".woff2"):
                    # Return 404 for assets that should exist
                    raise ex
                else:
                    # For SPA routing, serve index.html
                    return await super().get_response("index.html", scope)
            else:
                raise ex 