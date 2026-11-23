# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.modules.assessment.router import router as assessment_router
from app.modules.course.router import router as course_router
from app.modules.identity.router import router as identity_router
from app.modules.system.gateway_router import router as gateway_router
from app.modules.system.router import router as system_router
from app.modules.system.storage_router import router as storage_router
from app.modules.system.workflow_router import router as workflow_router

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

# Include Bounded Context Routers
app.include_router(identity_router)
app.include_router(course_router)
app.include_router(assessment_router)
app.include_router(system_router)
app.include_router(gateway_router)
app.include_router(storage_router)
app.include_router(workflow_router)


@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "ai_provider": settings.AI_PROVIDER,
        "version": "0.1.0-alpha"
    }
