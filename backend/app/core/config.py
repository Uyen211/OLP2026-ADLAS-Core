# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "ADLAS Core"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "adlas-default-development-secret-key-32bytes-min"

    # API Configuration
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://adlas_admin:adlas_secure_password@localhost:5432/adlas_db"

    # Storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ROOT_USER: str = "minio_admin"
    MINIO_ROOT_PASSWORD: str = "minio_secure_password"
    MINIO_BUCKET_MATERIALS: str = "adlas-materials"
    MINIO_BUCKET_SUBMISSIONS: str = "adlas-submissions"

    # JWT Authentication
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # AI Configuration (Dual-Mode)
    AI_PROVIDER: str = "gemini"  # "gemini" or "ollama"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL_CODE: str = "qwen2.5-coder:7b"
    OLLAMA_MODEL_TEXT: str = "llama3.2:3b"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
