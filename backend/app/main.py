"""
Main FastAPI application (ASYNC with PostgreSQL)
Initializes the API with authentication endpoints and CORS for frontend
"""
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.endpoints import auth, circle_members, circles, posts, users
from app.core.config import settings
from app.core.db import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan event handler for startup and shutdown
    """
    yield  # Application runs here

    # Cleanup on shutdown (if needed)
    await engine.dispose()


# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Social application backend with authentication and circles",
    lifespan=lifespan
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # React/Vite dev servers
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:

        response = await call_next(request)

        # Only apply strict security headers in production to avoid breaking local dev
        if settings.ENVIRONMENT == "production":
            # HSTS: Force browsers to use HTTPS for 1 year
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

            # Bonus AppSec Headers
            response.headers["X-Content-Type-Options"] = "nosniff" # Prevents MIME-sniffing
            response.headers["X-Frame-Options"] = "DENY"           # Prevents Clickjacking
            response.headers["X-XSS-Protection"] = "1; mode=block" # Legacy XSS protection

        return response


app.add_middleware(SecurityHeadersMiddleware)


# Include all routers at /api/v1 (versioned API)
# Frontend expects: http://localhost:8000/api/v1/auth/login
#                 http://localhost:8000/api/v1/circles/my
#                 http://localhost:8000/api/v1/posts/feed
app.include_router(auth.router, prefix=settings.API_V1_STR)           # /api/v1/auth
app.include_router(circles.router, prefix=settings.API_V1_STR)        # /api/v1/circles
app.include_router(posts.router, prefix=settings.API_V1_STR)          # /api/v1/posts
app.include_router(users.router, prefix=settings.API_V1_STR)          # /api/v1/users
app.include_router(circle_members.router, prefix=settings.API_V1_STR) # /api/v1/circles

@app.get("/")
async def root() -> dict[str, Any]:
    """Health check endpoint"""
    return {
        "message": "DevSecOps Social App API",
        "version": settings.VERSION,
        "status": "running",
        "database": "PostgreSQL (Async)",
        "endpoints": {
            "auth": {
                "register": f"POST {settings.API_V1_STR}/auth/register",
                "login": f"POST {settings.API_V1_STR}/auth/login",
                "logout": f"POST {settings.API_V1_STR}/auth/logout",
                "me": f"GET {settings.API_V1_STR}/auth/me"
            },
            "circles": {
                "my_circles": f"GET {settings.API_V1_STR}/circles/my",
                "create": f"POST {settings.API_V1_STR}/circles",
                "get": f"GET {settings.API_V1_STR}/circles/{{id}}",
                "update": f"PUT {settings.API_V1_STR}/circles/{{id}}",
                "delete": f"DELETE {settings.API_V1_STR}/circles/{{id}}"
            },
            "posts": {
                "feed": f"GET {settings.API_V1_STR}/posts/feed",
                "create": f"POST {settings.API_V1_STR}/posts",
                "get": f"GET {settings.API_V1_STR}/posts/{{id}}",
                "delete": f"DELETE {settings.API_V1_STR}/posts/{{id}}"
            }
        }
    }


@app.get("/health")
async def health_check() -> dict[str, str]:
    """
    Health check for monitoring
    Frontend can use this to verify backend is running
    """
    return {"status": "healthy", "database": "PostgreSQL"}


@app.get("/api/health")
async def api_health() -> dict[str, str]:
    """API-specific health check (unversioned, for backward compatibility)"""
    return {"status": "healthy", "api_version": settings.VERSION}


@app.get(f"{settings.API_V1_STR}/health")
async def api_v1_health() -> dict[str, str]:
    """API v1 health check (versioned)"""
    return {"status": "healthy", "api_version": settings.VERSION, "api": "v1"}
