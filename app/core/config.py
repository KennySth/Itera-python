import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Itera Market Intelligence"
    API_V1_STR: str = "/api/v1"
    
    # MongoDB Configuration
    # Default to localhost if not provided, but Atlas URL should be in .env
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "itera_db"

    model_config = SettingsConfigDict(
        env_file=".env", 
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
