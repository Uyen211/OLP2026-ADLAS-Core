# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from app.core.database import Base


class User(Base):
    """Identity User Entity representing all system actors."""
    __tablename__ = "users"
    __table_args__ = {"schema": "identity"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(150), unique=True, nullable=False, index=True)
    user_code = Column(String(50), unique=True, nullable=True, index=True)
    full_name = Column(String(150), nullable=False)
    password_hash = Column(String(255), nullable=False)
    avatar_url = Column(String(255), nullable=True)
    system_role = Column(String(30), nullable=False, default="USER")
    is_active = Column(Boolean, nullable=False, default=True)
    failed_login_count = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class SystemQuota(Base):
    """System Quotas configuration for global storage limits."""
    __tablename__ = "system_quotas"
    __table_args__ = {"schema": "system"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    max_slide_mb = Column(Integer, nullable=False, default=50)
    max_video_mb = Column(Integer, nullable=False, default=500)
    max_submission_mb = Column(Integer, nullable=False, default=25)
    max_course_storage_gb = Column(Integer, nullable=False, default=10)
    warning_threshold_pct = Column(Integer, nullable=False, default=85)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class SystemAuditLog(Base):
    """Append-only audit log for system administrator actions."""
    __tablename__ = "system_audit_logs"
    __table_args__ = {"schema": "system"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="SET NULL"), nullable=True)
    actor_email = Column(String(150), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    module = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default="INFO")
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    details = Column(JSONB, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)


class OutboxEvent(Base):
    """Transactional Outbox table ensuring at-least-once message delivery."""
    __tablename__ = "outbox_events"
    __table_args__ = {"schema": "system"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(100), nullable=False, index=True)
    aggregate_type = Column(String(50), nullable=False)
    aggregate_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    payload = Column(JSONB, nullable=False)
    status = Column(String(30), nullable=False, default="PENDING", index=True)
    retry_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime(timezone=True), nullable=True)


class DeadLetterQueue(Base):
    """Dead-Letter Queue storing failed events for manual or automatic retry."""
    __tablename__ = "dead_letter_queue"
    __table_args__ = {"schema": "system"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    outbox_event_id = Column(UUID(as_uuid=True), ForeignKey("system.outbox_events.id", ondelete="CASCADE"), nullable=True)
    event_type = Column(String(100), nullable=False, index=True)
    payload = Column(JSONB, nullable=False)
    error_message = Column(Text, nullable=False)
    stack_trace = Column(Text, nullable=True)
    retry_attempts = Column(Integer, nullable=False, default=3)
    status = Column(String(30), nullable=False, default="DEAD_LETTER", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class BackupHistory(Base):
    """Record of manual and scheduled academic data backups."""
    __tablename__ = "backup_history"
    __table_args__ = {"schema": "system"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backup_name = Column(String(200), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False, default=0)
    storage_path = Column(String(500), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    status = Column(String(30), nullable=False, default="COMPLETED")
