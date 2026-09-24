"""
SIF Sentinel — Backend Application Entry Point (Phase 8 Production Ready)
========================================================================

Initializes the FastAPI application, registers v1 API routers and legacy endpoints,
configures CORS, structured error handling, and request tracing middleware.
"""

import logging
import time
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import health, reports
from app.api.v1 import router as api_v1_router
from app.api.v1.import_api import router as import_api_router
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sif_sentinel")

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Production AI/NLP Decision Engine to prioritize Serious Injury & Fatality (SIF) "
        "precursors in industrial and energy safety observation reports."
    ),
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ---------------------------------------------------------------------------
# Middleware: CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    """Initialize database tables on application launch."""
    try:
        from app.db.session import init_db
        init_db()
    except Exception as e:
        logger.warning("DB initialization on startup notice: %s", e)


# ---------------------------------------------------------------------------
# Middleware: Request Timing & Logging
# ---------------------------------------------------------------------------

@app.middleware("http")
async def log_and_time_requests(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000.0

    response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
    logger.info(
        "%s %s -> %d (%.2f ms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# ---------------------------------------------------------------------------
# Structured Error Handlers
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Return standardized JSON envelope for HTTP exceptions."""
    error_code = "HTTP_ERROR"
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        error_code = "RESOURCE_NOT_FOUND"
    elif exc.status_code == status.HTTP_400_BAD_REQUEST:
        error_code = "BAD_REQUEST"
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        error_code = "FORBIDDEN"

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": error_code,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": request.url.path,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return structured validation errors with field-level details."""
    errors = []
    for err in exc.errors():
        field_name = " -> ".join(str(loc) for loc in err.get("loc", []))
        errors.append(f"{field_name}: {err.get('msg', 'invalid')}")

    detail_message = "; ".join(errors) if errors else "Validation failed for request parameters."

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": detail_message,
            "error_code": "VALIDATION_ERROR",
            "errors": exc.errors(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": request.url.path,
        },
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

# Legacy / Base routes (preserved for Phase 1 & 2 tests)
app.include_router(health.router, tags=["Health"])
app.include_router(reports.router, prefix="/reports", tags=["Reports"])

# Production API v1
app.include_router(api_v1_router, prefix="/api/v1", tags=["SIF Sentinel API v1"])
app.include_router(import_api_router, prefix="/api/v1/import", tags=["Import & Extraction"])

from app.api.v1.download_api import router as download_api_router
app.include_router(download_api_router, prefix="/api/v1/reports", tags=["Downloads"])

from app.api.routes.actions import router as actions_router
app.include_router(actions_router, prefix="/api/v1/actions", tags=["Action Center"])
