from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from open_webui.utils.auth import decode_token
from open_webui.config import Config, get_config, get_db


class CompanyConfigMiddleware(BaseHTTPMiddleware):
    """
    Middleware to set company-specific configuration for each request.
    
    This middleware extracts the company_id from the authenticated user
    and sets it in the application state for the duration of the request.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Initialize company_id as None
        company_id = None
        
        # Try to get the token from the request
        token = None
        auth_header = request.headers.get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
        elif "token" in request.cookies:
            token = request.cookies.get("token")
            
        # If we have a token, try to extract the user's company_id
        if token:
            # Skip API keys (they start with sk-)
            if not token.startswith("sk-"):
                token_data = decode_token(token)
                if token_data and "id" in token_data:
                    # Get the user from the database
                    from beyond_the_loop.models.users import Users
                    user = Users.get_user_by_id(token_data["id"])
                    if user and hasattr(user, "company_id"):
                        company_id = user.company_id
        
        # Store the company_id in the request state for easy access in route handlers
        request.state.company_id = company_id

        # Update the app's config with company-specific values
        if hasattr(request.app.state, "config") and hasattr(request.app.state.config, "set_company_id"):
            request.app.state.config.set_company_id(company_id)
        
        # Process the request
        response = await call_next(request)
        
        # Reset to None company after the request is processed
        #if hasattr(request.app.state, "config") and hasattr(request.app.state.config, "set_company_id"):
        #    request.app.state.config.set_company_id(None)
            
        return response
