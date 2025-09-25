"""
ComfyUI Microservice - Main Entry Point
Supports text-to-image, image-to-image, image size control and multimodal generation
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import uvicorn
import logging
import time
from typing import Dict
from api.routes import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Simple rate limiting storage
request_counts: Dict[str, Dict] = {}
MAX_REQUESTS_PER_MINUTE = 15
MAX_CONCURRENT_REQUESTS = 5
current_requests = 0

# Create FastAPI application with file upload limits
app = FastAPI(
    title="ComfyUI Microservice",
    description="AI Image Generation Service for CerebraUI",
    version="1.0.0",
    docs_url="/docs",  # API documentation
    redoc_url="/redoc"
)

# Set file upload limits
app.max_request_size = 50 * 1024 * 1024  # 50MB max request size
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file
ALLOWED_IMAGE_TYPES = {
    "image/jpeg", "image/jpg", 
    "image/png", 
    "image/webp", 
    "image/bmp",
    "image/tiff", "image/tif",
    "image/gif"  # For reference, though will be converted to static
}

# Configure CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors gracefully"""
    logger.warning(f"Validation error for {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Invalid request format",
            "message": "Please check your request parameters",
            "details": "Ensure all required fields are provided correctly"
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions without exposing internal details"""
    logger.error(f"Unexpected error for {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": "Something went wrong. Please try again later.",
            "request_id": f"{int(time.time())}"
        }
    )

# File upload validation middleware
@app.middleware("http")
async def validate_file_uploads(request: Request, call_next):
    """Validate file uploads before processing"""
    
    # Skip validation for non-upload endpoints
    if request.url.path in ["/", "/health", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)
    
    # Check if this is a file upload request
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        # Get content length
        content_length = request.headers.get("content-length")
        if content_length:
            content_length = int(content_length)
            if content_length > app.max_request_size:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={
                        "error": "File too large",
                        "message": f"Maximum upload size is {app.max_request_size // (1024*1024)}MB",
                        "max_size_mb": app.max_request_size // (1024*1024)
                    }
                )
    
    return await call_next(request)

# Simple rate limiting and overload protection
@app.middleware("http")
async def rate_limit_and_overload_protection(request: Request, call_next):
    """Protect against overload and excessive requests"""
    global current_requests
    
    client_ip = request.client.host
    current_time = time.time()
    
    # Skip rate limiting for health checks and docs
    if request.url.path in ["/", "/health", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)
    
    # Clean old request records
    if client_ip in request_counts:
        request_counts[client_ip] = {
            k: v for k, v in request_counts[client_ip].items() 
            if current_time - v < 60  # Keep requests from last minute
        }
    
    # Initialize client record if not exists
    if client_ip not in request_counts:
        request_counts[client_ip] = {}
    
    # Check rate limit
    recent_requests = len(request_counts[client_ip])
    if recent_requests >= MAX_REQUESTS_PER_MINUTE:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Too many requests",
                "message": f"Maximum {MAX_REQUESTS_PER_MINUTE} requests per minute allowed",
                "retry_after": 60
            }
        )
    
    # Check server overload
    if current_requests >= MAX_CONCURRENT_REQUESTS:
        logger.warning(f"Server overloaded. Current requests: {current_requests}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": "Server temporarily overloaded",
                "message": "Too many requests being processed. Please try again in a few moments.",
                "current_load": f"{current_requests}/{MAX_CONCURRENT_REQUESTS}"
            }
        )
    
    # Process request
    current_requests += 1
    request_counts[client_ip][current_time] = current_time
    logger.info(f"Processing request from {client_ip} to {request.url.path}")
    
    try:
        response = await call_next(request)
        logger.info(f"Request completed successfully for {client_ip}")
        return response
    except Exception as e:
        logger.error(f"Request failed for {client_ip}: {str(e)}")
        raise
    finally:
        current_requests -= 1

# Register API routes
app.include_router(router, prefix="/api/v1")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "ComfyUI Microservice is running normally",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Detailed health check with server status"""
    return {
        "status": "healthy",
        "service": "comfyui-service",
        "server_load": {
            "current_requests": current_requests,
            "max_concurrent": MAX_CONCURRENT_REQUESTS,
            "load_percentage": f"{(current_requests/MAX_CONCURRENT_REQUESTS)*100:.1f}%"
        },
        "rate_limits": {
            "requests_per_minute": MAX_REQUESTS_PER_MINUTE,
            "max_concurrent": MAX_CONCURRENT_REQUESTS
        },
        "endpoints": {
            "text_to_image": "/api/v1/generate/text-to-image",
            "image_to_image": "/api/v1/generate/image-to-image",
            "multimodal": "/api/v1/generate/multimodal"
        }
    }

@app.get("/status")
async def get_status():
    """Simple status endpoint for monitoring"""
    return {
        "active_requests": current_requests,
        "total_active_clients": len(request_counts),
        "service_status": "operational"
    }

if __name__ == "__main__":
    logger.info("Starting ComfyUI Microservice...")
    # Development environment configuration
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,  # Auto-restart when code changes
        log_level="info"
    )