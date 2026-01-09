from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.core.logging_config import setup_logging
# WebSocket disabled for now
# from app.core.websocket import sio, get_socket_app
from app.api.v1.api import api_router
from app.middleware.auth import AuthMiddleware

# Setup logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="Sahelys API",
    description="API pour le système de compte rendu hebdomadaire Sahelys Burkina",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth middleware - Commented out for now, will use dependencies instead
# app.add_middleware(AuthMiddleware)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Health"])
async def health_check():
    """Point de contrôle de santé de l'API"""
    return {"message": "Sahelys API is running!", "version": "1.0.0"}


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Sahelys API",
        version="1.0.0",
        description="API complète pour le système de compte rendu hebdomadaire Sahelys Burkina",
        routes=app.routes,
    )
    
    # Ajouter la sécurité JWT
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Token JWT pour l'authentification"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# WebSocket disabled - uncomment to enable
# socket_app = get_socket_app()
# app.mount("/ws", socket_app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )