from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # [JWT AUTHENTICATION]: JWT configuration for token-based auth
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS Settings
    ALLOWED_ORIGINS: list = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174"
    ]
    
    # [PER-USER STORAGE]: Storage backend selection
    # Options: "local" (filesystem), "huggingface" (HF Spaces), "zenodo" (Zenodo.org), "all" (multi-backend)
    STORAGE_BACKEND: str = "local"
    
    # Local storage path
    LOCAL_STORAGE_PATH: str = "./uploads"
    
    # Zenodo Configuration
    ZENODO_API_TOKEN: str = ""
    ZENODO_SANDBOX_MODE: bool = True  # Use sandbox.zenodo.org for testing
    
    class Config:
        env_file = ".env"

settings = Settings()


