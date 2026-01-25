"""
Langfuse Admin Proxy Router

Provides secure admin-only access to Langfuse UI through the main FastAPI application.
Only users with admin role can access the Langfuse dashboard.

Route: /admin/langfuse/*
Proxies to: LANGFUSE_HOST (default: http://localhost:3001)
"""

import logging
import os
import re
import aiohttp
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse, HTMLResponse, RedirectResponse
from open_webui.utils.auth import get_admin_user
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", logging.INFO))

router = APIRouter()

# Langfuse backend URL - read from environment or use default
LANGFUSE_BACKEND_URL = os.getenv("LANGFUSE_HOST", "http://localhost:3001").rstrip("/")

# Headers to exclude when proxying
EXCLUDED_HEADERS = {
    "host",
    "connection",
    "content-length",
    "content-encoding",
    "transfer-encoding",
}


async def proxy_request(
    request: Request,
    target_url: str,
    method: str = "GET",
) -> Response:
    """
    Proxy an HTTP request to the target URL.

    Args:
        request: Original FastAPI request
        target_url: Target URL to proxy to
        method: HTTP method

    Returns:
        Response from the proxied request
    """
    # Prepare headers (exclude certain headers)
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in EXCLUDED_HEADERS
    }

    # Read request body
    body = await request.body()

    # Create aiohttp session
    timeout = aiohttp.ClientTimeout(total=60)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Make the proxied request
            async with session.request(
                method=method,
                url=target_url,
                headers=headers,
                params=request.query_params,
                data=body if body else None,
                allow_redirects=False,
            ) as response:
                # Prepare response headers
                response_headers = {
                    key: value
                    for key, value in response.headers.items()
                    if key.lower() not in EXCLUDED_HEADERS
                }

                # Handle redirects - rewrite location header
                if response.status in (301, 302, 303, 307, 308):
                    location = response.headers.get("Location", "")
                    # Rewrite location if it points to Langfuse backend
                    if location.startswith(LANGFUSE_BACKEND_URL):
                        location = location.replace(
                            LANGFUSE_BACKEND_URL, "/api/v1/langfuse"
                        )
                        response_headers["Location"] = location
                    # Handle relative redirects
                    elif location.startswith("/"):
                        response_headers["Location"] = f"/api/v1/langfuse{location}"

                # Read response content
                content = await response.read()

                # If HTML/JS/CSS, rewrite URLs to point to our proxy
                content_type = response.headers.get("content-type", "").lower()
                if any(ct in content_type for ct in ["text/html", "application/javascript", "text/javascript", "text/css"]):
                    try:
                        text = content.decode("utf-8")

                        # Rewrite absolute URLs
                        text = text.replace(
                            f'"{LANGFUSE_BACKEND_URL}',
                            '"/api/v1/langfuse',
                        )
                        text = text.replace(
                            f"'{LANGFUSE_BACKEND_URL}",
                            "'/api/v1/langfuse",
                        )

                        # Rewrite /_next/ paths (but NOT /api/v1/langfuse/_next/)
                        # This works for both HTML attributes and JavaScript strings
                        text = re.sub(r'(["|\'])/_next/', r'\1/api/v1/langfuse/_next/', text)

                        # Rewrite /api/ paths (but NOT /api/v1/langfuse/api/)
                        # Negative lookahead to avoid double-rewriting
                        text = re.sub(r'(["|\'])/api/(?!v1/langfuse)', r'\1/api/v1/langfuse/api/', text)

                        content = text.encode("utf-8")
                        response_headers["content-length"] = str(len(content))
                    except Exception as e:
                        log.warning(f"Failed to rewrite URLs in {content_type}: {e}")

                return Response(
                    content=content,
                    status_code=response.status,
                    headers=response_headers,
                    media_type=content_type if content_type else None,
                )

    except aiohttp.ClientError as e:
        log.error(f"Langfuse proxy error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to Langfuse at {LANGFUSE_BACKEND_URL}: {str(e)}",
        )
    except Exception as e:
        log.error(f"Unexpected proxy error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Proxy error: {str(e)}",
        )


############################
# Langfuse Proxy Routes
############################


@router.get("/")
async def langfuse_root(
    request: Request,
    user=Depends(get_admin_user),
):
    """
    Proxy root Langfuse page.
    Only accessible by admin users.
    """
    log.info(f"[LANGFUSE PROXY] Admin user {user.id} ({user.email}) accessing Langfuse dashboard")

    target_url = f"{LANGFUSE_BACKEND_URL}/"
    return await proxy_request(request, target_url, method="GET")


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def langfuse_proxy(
    path: str,
    request: Request,
    user=Depends(get_admin_user),
):
    """
    Proxy all requests to Langfuse.
    Only accessible by admin users.

    Args:
        path: The path to proxy (everything after /admin/langfuse/)
        request: The original request
        user: Authenticated admin user (enforced by dependency)

    Returns:
        Proxied response from Langfuse
    """
    log.debug(f"[LANGFUSE PROXY] {request.method} /{path} (user: {user.email})")

    # Construct target URL
    target_url = f"{LANGFUSE_BACKEND_URL}/{path}"

    # Proxy the request
    return await proxy_request(request, target_url, method=request.method)


############################
# Health & Status
############################


@router.get("/health", dependencies=[Depends(get_admin_user)])
async def langfuse_health():
    """
    Check if Langfuse is accessible.
    Only accessible by admin users.
    """
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{LANGFUSE_BACKEND_URL}/api/public/health") as response:
                if response.status == 200:
                    return {
                        "status": "ok",
                        "langfuse_url": LANGFUSE_BACKEND_URL,
                        "accessible": True,
                        "message": "Langfuse is running and accessible"
                    }
                else:
                    return {
                        "status": "error",
                        "langfuse_url": LANGFUSE_BACKEND_URL,
                        "accessible": False,
                        "http_status": response.status,
                        "message": f"Langfuse returned status {response.status}"
                    }
    except aiohttp.ClientConnectorError as e:
        log.error(f"Langfuse health check failed - connection error: {e}")
        return {
            "status": "error",
            "langfuse_url": LANGFUSE_BACKEND_URL,
            "accessible": False,
            "error": "Cannot connect to Langfuse. Is it running?",
            "detail": str(e),
        }
    except Exception as e:
        log.error(f"Langfuse health check failed: {e}")
        return {
            "status": "error",
            "langfuse_url": LANGFUSE_BACKEND_URL,
            "accessible": False,
            "error": str(e),
        }
