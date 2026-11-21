# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Interactive Learning and Multi-Dimensional Competency Assessment Platform API",
    version="0.1.0-alpha",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Cross-Origin Resource Sharing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "ai_provider": settings.AI_PROVIDER,
        "version": "0.1.0-alpha"
    }
