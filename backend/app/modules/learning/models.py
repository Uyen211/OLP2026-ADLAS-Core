# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""SQLAlchemy 2.0 ORM models for learning.modules and learning.learning_materials."""

from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
import app.modules.course.models  # noqa: F401 - ensure course.courses and course.learning_objectives are in metadata


class LearningModule(Base):
    """Hierarchical course chapter/topic module in learning.modules."""

    __tablename__ = "modules"
    __table_args__ = {"schema": "learning"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(
        UUID(as_uuid=True),
        ForeignKey("course.courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(200), nullable=False)
    order_index = Column(Integer, nullable=False, default=1)
    unlock_at = Column(DateTime(timezone=True), nullable=True)
    prerequisite_module_id = Column(
        UUID(as_uuid=True),
        ForeignKey("learning.modules.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_published = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    materials = relationship(
        "LearningMaterial",
        back_populates="module",
        cascade="all, delete-orphan",
        order_by="LearningMaterial.created_at",
    )


class LearningMaterial(Base):
    """Digital learning resource (Slide, PDF, Video, Document) in learning.learning_materials."""

    __tablename__ = "learning_materials"
    __table_args__ = {"schema": "learning"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_id = Column(
        UUID(as_uuid=True),
        ForeignKey("learning.modules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lo_id = Column(
        UUID(as_uuid=True),
        ForeignKey("course.learning_objectives.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title = Column(String(200), nullable=False)
    material_type = Column(String(30), nullable=False)
    file_url = Column(String(500), nullable=True)
    is_mandatory = Column(Boolean, nullable=False, default=True)
    est_duration_minutes = Column(Integer, default=30)
    is_published = Column(Boolean, nullable=False, default=False)
    sections_cache = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    module = relationship("LearningModule", back_populates="materials")
    checkpoints = relationship(
        "MaterialCheckpoint",
        back_populates="material",
        cascade="all, delete-orphan",
        order_by="MaterialCheckpoint.stop_time_seconds, MaterialCheckpoint.section_index",
    )


class MaterialCheckpoint(Base):
    """Interactive quiz checkpoint on video timeline or document section in learning.material_checkpoints."""

    __tablename__ = "material_checkpoints"
    __table_args__ = {"schema": "learning"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_id = Column(
        UUID(as_uuid=True),
        ForeignKey("learning.learning_materials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lo_id = Column(
        UUID(as_uuid=True),
        ForeignKey("course.learning_objectives.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    stop_time_seconds = Column(Integer, nullable=True)
    section_index = Column(Integer, nullable=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(30), nullable=False, default="MULTIPLE_CHOICE")
    options = Column(JSONB, nullable=True)
    correct_option = Column(String(10), nullable=True)
    expected_concept = Column(Text, nullable=True)
    bloom_level = Column(String(20), nullable=True)
    source_citation = Column(Text, nullable=True)
    is_blocking = Column(Boolean, nullable=False, default=True)
    time_limit_seconds = Column(Integer, nullable=False, default=10)
    rewind_seconds = Column(Integer, nullable=False, default=15)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    material = relationship("LearningMaterial", back_populates="checkpoints")
    attempts = relationship(
        "StudentCheckpointAttempt",
        back_populates="checkpoint",
        cascade="all, delete-orphan",
    )


class StudentCheckpointAttempt(Base):
    """Student answer attempt and pass status per checkpoint in learning.student_checkpoint_attempts."""

    __tablename__ = "student_checkpoint_attempts"
    __table_args__ = {"schema": "learning"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    checkpoint_id = Column(
        UUID(as_uuid=True),
        ForeignKey("learning.material_checkpoints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    selected_option = Column(String(10), nullable=True)
    is_correct = Column(Boolean, nullable=False, default=False)
    attempt_count = Column(Integer, nullable=False, default=1)
    passed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    checkpoint = relationship("MaterialCheckpoint", back_populates="attempts")
