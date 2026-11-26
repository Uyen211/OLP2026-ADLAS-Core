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
)
from sqlalchemy.dialects.postgresql import UUID
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
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    module = relationship("LearningModule", back_populates="materials")
