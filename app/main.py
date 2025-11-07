"""Main FastAPI application."""

from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.types import ASGIApp
from app.routes import sharepoint, auth
from app.utils.logger import setup_logger
from app.config import settings
import os

logger = setup_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Sindbad.Tech SharePoint Doc Indexer",
    description="Web application to index and search SharePoint documents",
    version="1.0.0",
)

# Session middleware (must be before other middleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    max_age=86400,  # 24 hours
    same_site="lax",
    https_only=False,  # Allow HTTP for local development
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add cache control headers for static files
class NoCacheStaticFiles(StaticFiles):
    """Static files with no-cache headers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    message.setdefault("headers", [])
                    headers = dict(message["headers"])
                    headers[b"cache-control"] = b"no-cache, no-store, must-revalidate"
                    headers[b"pragma"] = b"no-cache"
                    headers[b"expires"] = b"0"
                    message["headers"] = list(headers.items())
                await send(message)
            await super().__call__(scope, receive, send_wrapper)
        else:
            await super().__call__(scope, receive, send)

# Include routers
app.include_router(auth.router)
app.include_router(sharepoint.router)

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/static", NoCacheStaticFiles(directory=static_dir), name="static")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    logger.error(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    logger.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"error": "Validation failed", "details": exc.errors()}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main application page (protected by authentication)."""
    # Check if user is authenticated
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    static_file = os.path.join(static_dir, "index.html")
    if os.path.exists(static_file):
        return FileResponse(static_file)
        return HTMLResponse(
            content="<h1>Sindbad.Tech SharePoint Doc Indexer</h1><p>Frontend not found. Please check static files.</p>"
        )


@app.get("/api/user")
async def get_current_user(request: Request) -> Dict[str, Any]:
    """Get current authenticated user info.
    
    Returns:
        User information or 401 if not authenticated
    """
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return request.session.get("user", {})


@app.get("/api/health")
async def health_check():
    """Health check endpoint for Cloud Run and monitoring."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "Sindbad.Tech SharePoint Doc Indexer",
            "version": "1.0.0"
        }
    )


@app.get("/.well-known/{path:path}")
async def well_known_handler(path: str):
    """Handle .well-known requests (Chrome DevTools, etc.)."""
    return JSONResponse(status_code=404, content={"status": "not_found"})


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("Sindbad.Tech SharePoint Doc Indexer starting up...")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Sindbad.Tech SharePoint Doc Indexer shutting down...")

