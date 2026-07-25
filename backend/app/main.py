"""
Enterprise AI Data Assistant — FastAPI Application Entry Point.
(No authentication — open access)
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import os

from .config import get_settings
from .database import init_app_db, init_data_db
from .core.rate_limiter import limiter
from .core.exceptions import AppException

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # --- Startup ---
    print("[START] Starting Enterprise AI Data Assistant...")

    # Create required directories
    os.makedirs("data", exist_ok=True)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)

    # Initialize databases
    await init_app_db()
    await init_data_db()
    print("[OK] Databases initialized")

    print(f"[OK] Server ready | Environment: {settings.APP_ENV}")

    configured = settings.get_available_llm_providers()
    print(f"[OK] Configured LLM providers: {configured}")
    if configured == ["ollama"]:
        print(
            "[WARN] No cloud LLM API key found in backend/.env - natural language "
            "queries will fail unless Ollama is running locally (ollama serve). "
            "Add GEMINI_API_KEY (aistudio.google.com/apikey) or GROQ_API_KEY "
            "(console.groq.com/keys) and restart."
        )

    yield

    # --- Shutdown ---
    print("[STOP] Shutting down...")


# ============================================
# App Instance
# ============================================
app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise-grade AI-powered Text-to-SQL platform with Multi-LLM Consensus Engine",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# Custom exception handler
# ============================================
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "type": type(exc).__name__},
    )


# ============================================
# Register Routers (no auth router)
# ============================================
from .routers import upload, query, admin, export

app.include_router(upload.router)
app.include_router(query.router)
app.include_router(admin.router)
app.include_router(export.router)


# ============================================
# Health Check
# ============================================
@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.APP_ENV,
        "llm_providers": settings.get_available_llm_providers(),
    }


@app.get("/api", tags=["Root"])
async def api_root():
    """API info endpoint."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "docs": "/docs",
        "health": "/api/health",
    }


# ============================================
# Frontend (serves frontend/dist when built)
# ============================================
PROJECT_ROOT = os.path.dirname(settings.BASE_DIR)
FRONTEND_DIST = os.path.join(PROJECT_ROOT, "frontend", "dist")
FRONTEND_INDEX = os.path.join(FRONTEND_DIST, "index.html")

if os.path.isfile(FRONTEND_INDEX):
    assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        """Serve the built React app, falling back to index.html for client routes."""
        # Unmatched API paths must 404, not return the SPA shell
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")

        candidate = os.path.normpath(os.path.join(FRONTEND_DIST, full_path))
        if (
            full_path
            and candidate.startswith(FRONTEND_DIST)
            and os.path.isfile(candidate)
        ):
            return FileResponse(candidate)
        return FileResponse(FRONTEND_INDEX)

else:

    @app.get("/", include_in_schema=False)
    async def frontend_not_built():
        return {
            "message": f"{settings.APP_NAME} API is running",
            "docs": "/docs",
            "health": "/api/health",
            "note": "Frontend not built. Run: cd frontend && npm install && npm run build",
        }
