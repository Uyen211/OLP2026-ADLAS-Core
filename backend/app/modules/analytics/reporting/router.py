# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""REST router for academic grade report export (T2-P-M6-03)."""

import io
import uuid
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.analytics.reporting.schemas import ExportFormat, ExportPreviewResponse
from app.modules.analytics.reporting.service import ReportingService
from app.modules.identity.dependencies import CurrentUser, get_current_user

router = APIRouter(prefix="/api/v1/analytics/reports", tags=["Academic Reports"])


async def _export(
    course_id: uuid.UUID,
    fmt: ExportFormat,
    confirm_draft: bool,
    db: AsyncSession,
    current_user: CurrentUser,
) -> StreamingResponse:
    result = await ReportingService(db).export(course_id, current_user.user, fmt, confirm_draft)
    return StreamingResponse(
        io.BytesIO(result.content),
        media_type=result.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
            "Content-Length": str(len(result.content)),
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.get("/courses/{course_id}/export-preview", response_model=ExportPreviewResponse)
async def export_preview(
    course_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await ReportingService(db).preview(course_id, current_user.user)


@router.get("/courses/{course_id}/export/excel")
async def export_excel(
    course_id: uuid.UUID,
    confirm_draft: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await _export(course_id, ExportFormat.EXCEL, confirm_draft, db, current_user)


@router.get("/courses/{course_id}/export/csv")
async def export_csv(
    course_id: uuid.UUID,
    confirm_draft: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await _export(course_id, ExportFormat.CSV, confirm_draft, db, current_user)


@router.get("/courses/{course_id}/export/pdf")
async def export_pdf(
    course_id: uuid.UUID,
    confirm_draft: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await _export(course_id, ExportFormat.PDF, confirm_draft, db, current_user)
