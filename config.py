from pydantic_settings import BaseSettings
from pathlib import Path
import os
from typing import Optional, List


class Settings(BaseSettings):
    # Base
    BASE_DIR: Path = Path(__file__).resolve().parent
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True
    PROJECT_NAME: str = "Wazir Недвижимость"

    # Database
    DATABASE_URL: str = "mysql+pymysql://root:c:ICx9Pr{48y>6BmBc3r@localhost/wazir_db"
    
    # JWT Auth
    SECRET_KEY: str = "your_super_secret_key_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Media
    MEDIA_DIR: str = "media"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # Email
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_FROM: Optional[str] = None
    MAIL_PORT: Optional[int] = 587
    MAIL_SERVER: Optional[str] = None
    MAIL_TLS: bool = True
    MAIL_SSL: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings() 