from contextvars import ContextVar
import os
from fastapi import Request
from open_webui.utils.auth import get_current_user, get_http_authorization_cred

current_user_context = ContextVar("current_user_context", default=None)


def _get_user_from_request() -> dict:
    """Try to get user from current request context"""
    try:
        # This is a creative approach - we'll try to get the request from the call stack
        import inspect

        # Look through the call stack for a request object
        for frame_info in inspect.stack():
            frame = frame_info.frame
            local_vars = frame.f_locals

            # Check if there's a 'request' variable in the current frame
            if "request" in local_vars and hasattr(local_vars["request"], "headers"):
                request = local_vars["request"]
                try:
                    # Try to get the user using the same method as the audit middleware
                    auth_header = request.headers.get("Authorization")
                    if auth_header:
                        user = get_current_user(
                            request,
                            None,
                            None,
                            get_http_authorization_cred(auth_header),
                        )
                        if user:
                            return {
                                "id": user.id,
                                "email": user.email,
                                "name": user.name,
                                "role": user.role,
                            }
                except Exception:
                    continue

        return None
    except Exception:
        return None


def inject_user_headers(headers: dict, user: dict = None) -> dict:
    """Inject user headers if enabled and context exists"""
    headers.update(
        {
            "X-OpenWebUI-is-enabled": "true",
        }
    )
    if os.getenv("ENABLE_FORWARD_USER_INFO_HEADERS", "").lower() == "true":
        headers.update(
            {
                "X-OpenWebUI-is-forwarded": "true",
            }
        )
        # Try multiple ways to get user information
        if user is None:
            user = current_user_context.get()
        if user is None:
            user = _get_user_from_request()

        if user:
            headers.update(
                {
                    "X-OpenWebUI-User-Id": user.get("id", ""),
                    "X-OpenWebUI-User-Email": user.get("email", ""),
                    "X-OpenWebUI-User-Name": user.get("name", ""),
                    "X-OpenWebUI-User-Role": user.get("role", ""),
                }
            )
    return headers
