from datetime import datetime, timezone
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.routes.sensor_routes import router as sensor_router
from app.routes.dashboard_routes import router as dashboard_router
from app.routes.control_routes import router as control_router
from app.routes.database_routes import router as database_router
from app.routes.auth_routes import router as auth_router

app = FastAPI(
    title="AgroGuard API",
    description="Intelligent Agronomic Decision Support Backend API (FastAPI Framework)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(auth_router)
app.include_router(sensor_router)
app.include_router(dashboard_router)
app.include_router(control_router)
app.include_router(database_router)

# Health Check Root Endpoint
@app.get('/health', summary="System health check", tags=["System Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "AgroGuard Backend API",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# Global Error Handlers matching frontend expectations
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return JSONResponse(
            status_code=404,
            content={"error": "Not Found", "message": "The requested API endpoint does not exist."}
        )
    if exc.status_code == 405:
        return JSONResponse(
            status_code=405,
            content={"error": "Method Not Allowed", "message": "The HTTP method is not allowed for this endpoint."}
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "HTTP Error", "message": exc.detail, "detail": exc.detail},
        headers=exc.headers
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": "Unprocessable Entity", "message": "Request validation failed", "details": exc.errors()}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    if exc.__class__.__name__ == "ModelValidationError":
        return JSONResponse(
            status_code=400,
            content={"error": "Validation Error", "message": str(exc)}
        )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "message": "An unexpected server error occurred."}
    )
