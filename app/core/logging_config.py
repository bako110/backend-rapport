import logging
import sys
from app.core.config import settings

def setup_logging():
    """Configure logging for the application"""
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO if not settings.debug else logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific loggers
    logger = logging.getLogger(__name__)
    
    # Reduce noisy loggers in production
    if not settings.debug:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("passlib").setLevel(logging.WARNING)
    
    logger.info(f"Logging configured for {settings.environment} environment")
    
    return logger