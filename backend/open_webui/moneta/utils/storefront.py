import os
import json
import base64
from datetime import datetime, timedelta, timezone

from jwcrypto import jwk, jwe
from jwcrypto.common import json_encode, json_decode

# Load environment variables
HAS_STOREFRONT = os.getenv('HAS_STOREFRONT', 'false').lower() == 'true'
STOREFRONT_URL = os.getenv('STOREFRONT_URL')
STOREFRONT_SECRET = os.getenv('STOREFRONT_SECRET') # Expecting Base64 URL Safe encoded 32-byte key
STOREFRONT_TOKEN_KEY = os.getenv('STOREFRONT_TOKEN_KEY', 'storefront_token')


def get_daily_pass_expired_time() -> datetime:
    """Returns the expiration time for a daily pass (24 hours from now)."""
    return datetime.now(timezone.utc) + timedelta(hours=24)

def get_in_game_subscription_codes() -> list[str]:
    """Returns a list of subscription codes considered in-game."""
    # Example codes, adjust as needed
    return ['vampire_run_3_upgrades', 'vampire_run_5_upgrades', 'vampire_pay_per_item', 'fish_pay_per_item']

def should_use_storefront() -> bool:
    """Checks if the storefront integration is enabled via environment variable."""
    return HAS_STOREFRONT

def storefront_redirect_url() -> str:
    """Determines the redirect URL for the storefront."""
    if not STOREFRONT_URL:
        # Adjust the default path if needed
        return '/subscriptions'
    return f"{STOREFRONT_URL}/plan"


def _encode_jwe(payload: dict, secret_key_b64: str) -> str:
    """Encodes the payload into a JWE token using A256KW and A256CBC-HS512."""
    if not secret_key_b64:
        raise ValueError("STOREFRONT_SECRET environment variable is not set or empty.")

    try:
        # Decode the Base64 URL Safe key
        decoded_key = base64.urlsafe_b64decode(secret_key_b64 + '=' * (4 - len(secret_key_b64) % 4))
        if len(decoded_key) != 32:
            raise ValueError("Invalid key length: STOREFRONT_SECRET must decode to 32 bytes for A256KW.")
        
        # Create JWK from the raw key bytes
        jwk_key = jwk.JWK(kty='oct', k=base64.urlsafe_b64encode(decoded_key).decode('utf-8'))

    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid STOREFRONT_SECRET format or length: {e}") from e


    protected_header = {
        "alg": "A256KW",      # Key encryption algorithm: AES Key Wrap with 256-bit key
        "enc": "A256CBC-HS512", # Content encryption algorithm: AES CBC using 256-bit key with HMAC SHA-512
        "typ": "JWE"
    }

    jwe_token = jwe.JWE(json.dumps(payload).encode('utf-8'),
                        recipient=jwk_key,
                        protected=protected_header)

    return jwe_token.serialize(compact=True)


def _get_storefront_cookie_domain(request) -> str:
    """
    Constructs the cookie domain based on the request host.
    Assumes 'request' has a 'host' attribute (e.g., request.url.hostname in FastAPI/Starlette).
    Adapt this function based on your web framework.
    """
    # Example for FastAPI/Starlette: request.url.hostname
    # Example for Flask: request.host.split(':')[0]
    current_host = getattr(request.url, 'hostname', getattr(request, 'host', 'localhost'))
    
    # Handle potential port in host for Flask
    if ':' in current_host:
      current_host = current_host.split(':')[0]

    domain_parts = current_host.split('.')

    # Handle cases like 'localhost' or single-part domains
    if len(domain_parts) < 2:
      return current_host # Cannot set a leading dot for localhost or TLDs

    # For domains like 'example.com', return 'example.com'
    # For domains like 'sub.example.com', return '.example.com' to cover subdomains
    if len(domain_parts) > 2 and not current_host.replace('.', '').isdigit(): # Avoid IP addresses
        # Return with leading dot for parent domain coverage
        return '.' + '.'.join(domain_parts[1:])
    else:
        # Return the full host for two-part domains or IPs
        return current_host


def save_storefront_token_to_cookies(response, user_data: dict, request):
    """
    Generates a JWE token and saves it to cookies in the response.
    Assumes 'response' has a 'set_cookie' method (e.g., FastAPI/Starlette/Flask).
    Assumes 'request' is available to determine the cookie domain.
    'user_data' should be a dictionary containing user info like uid, name, region, etc.
    """
    if not STOREFRONT_SECRET:
        print("Warning: STOREFRONT_SECRET is not set. Cannot create storefront cookie.")
        return

    try:
        storefront_jwe = _encode_jwe(user_data, STOREFRONT_SECRET)
    except ValueError as e:
        print(f"Error encoding JWE token: {e}")
        # Handle error appropriately, maybe log it
        return

    cookie_domain = _get_storefront_cookie_domain(request)
    expires_time = get_daily_pass_expired_time()

    # Use the response object's method to set the cookie
    # Arguments might vary slightly based on the framework (e.g., max_age vs expires)
    response.set_cookie(
        key=STOREFRONT_TOKEN_KEY,
        value=storefront_jwe,
        expires=expires_time.timestamp(), # Or use max_age=24*60*60
        domain=cookie_domain,
        path='/',
        secure=True,      # Recommended for sensitive cookies
        httponly=False,
        samesite='lax'
    )
    print(f"Storefront cookie set for domain {cookie_domain}")
    
    # I also want to set cookies['_medusa_callback_url'] to the current url
    response.set_cookie(
        key='_medusa_callback_url',
        # I want to to set value to the root domain of the current url without double quotes
        value=request.url.netloc.strip('"'),
        domain=cookie_domain,
        samesite='lax',
        path='/'
    )


def delete_storefront_token_from_cookies(response, request):
    """
    Deletes the storefront token cookie.
    Assumes 'response' has a 'delete_cookie' method.
    Assumes 'request' is available to determine the cookie domain.
    """
    cookie_domain = _get_storefront_cookie_domain(request)
    response.delete_cookie(
        key=STOREFRONT_TOKEN_KEY,
        domain=cookie_domain,
        path='/'
    )
    print(f"Storefront cookie deleted for domain {cookie_domain}")


# You might want to keep or adapt the original function name if it's used elsewhere
# def setup_storefront_cookies(user_id, user_data):
#     pass # Original function is now replaced/integrated into save_storefront_token_to_cookies

# Example usage (within a FastAPI route, adapt as needed):
# from fastapi import FastAPI, Request, Response
# from fastapi.responses import JSONResponse
#
# app = FastAPI()
#
# @app.post("/login")
# async def login_user(request: Request):
#     # ... authenticate user ...
#     user_info = {"id": "user123", "name": "Test User", "region": "EU", "currency": "EUR"} # Example user data
#     response = JSONResponse(content={"message": "Login successful"})
#     if should_use_storefront():
#          save_storefront_token_to_cookies(response, user_info, request)
#     return response
#
# @app.post("/logout")
# async def logout_user(request: Request):
#     response = JSONResponse(content={"message": "Logout successful"})
#     if should_use_storefront():
#         delete_storefront_token_from_cookies(response, request)
#     # ... other logout logic ...
#     return response

