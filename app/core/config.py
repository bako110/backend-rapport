from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # Database
    mongo_uri: str = Field(default="mongodb://localhost:27017/sahelys", env="MONGO_URI")
    database_name: str = Field(default="sahelys", env="DATABASE_NAME")
    
    # JWT
    jwt_secret: str = Field(default="your-secret-key", env="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # CORS
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:19006",
        env="CORS_ORIGINS"
    )
    
    def get_cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    # Admin
    admin_email: str = Field(default="admin@sahelys.bf", env="ADMIN_EMAIL")
    admin_password: str = Field(default="admin123", env="ADMIN_PASSWORD")
    admin_name: str = Field(default="Administrateur", env="ADMIN_NAME")
    
    # Timezone
    timezone: str = Field(default="Africa/Ouagadougou", env="TIMEZONE")
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()