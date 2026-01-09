#!/usr/bin/env python3
"""
Script de démarrage pour l'API Sahelys
"""
import asyncio
import uvicorn
from app.core.config import settings
from app.core.logging_config import setup_logging

def start_server():
    """Démarrer le serveur FastAPI"""
    # Setup logging
    logger = setup_logging()
    
    logger.info(f"Démarrage de l'API Sahelys en mode {settings.environment}")
    logger.info(f"MongoDB URI: {settings.mongo_uri}")
    logger.info(f"Debug mode: {settings.debug}")
    
    # Configuration uvicorn
    config = {
        "app": "main:app",
        "host": "0.0.0.0",
        "port": 8000,
        "reload": settings.debug,
        "access_log": settings.debug,
        "log_level": "debug" if settings.debug else "info"
    }
    
    if settings.environment == "production":
        config.update({
            "workers": 4,
            "reload": False
        })
    
    uvicorn.run(**config)

if __name__ == "__main__":
    start_server()