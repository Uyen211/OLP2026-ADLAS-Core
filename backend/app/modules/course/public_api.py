# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Public read-only service interface exposed by Course Context for TV1, TV2, and Identity."""

from dataclasses import dataclass
from typing import Iterable, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.course.enums import BloomLevel, ContextualRole, EnrollmentStatus
from app.modules.course.exceptions import CourseForbiddenException
from app.modules.course.lo_references import (
    LoReferenceChecker,
    register_lo_reference_checker,
)
from app.modules.course.repository import CourseRepository
from app.modules.identity.schemas import CourseRoleClaim


@dataclass(frozen=True)
class LODTO:
    """Immutable Learning Objective DTO shared across bounded contexts."""

    id: uuid.UUID
    course_id: uuid.UUID
    code: str
    description: str
    bloom_level: BloomLevel
    order_index: int


@dataclass(frozen=True)
class CourseInfoDTO:
    """Immutable course header information (used by academic report export)."""

    id: uuid.UUID
    course_code: str
    section_code: str
    name: str
    semester: str
    credits: int


@dataclass(frozen=True)
class StudentEnrollmentDTO:
    """Immutable active student enrollment DTO."""

    user_id: uuid.UUID
    user_code: Optional[str]
    full_name: str
    email: str


class CoursePublicService:
    """Public contract for cross-context reads without exposing course.* ORM internals."""

    def __init__(self, db: AsyncSession, repo: Optional[CourseRepository] = None):
        self.db = db
        self.repo = repo or CourseRepository(db)

    async def get_learning_objectives(self, course_id: uuid.UUID) -> List[LODTO]:
        los = await self.repo.list_los(course_id)
        return [
            LODTO(
                id=lo.id,
                course_id=lo.course_id,
                code=lo.code,
                description=lo.description,
                bloom_level=BloomLevel(lo.bloom_level),
                order_index=lo.order_index,
            )
            for lo in los
        ]

    async def get_user_course_roles(self, user_id: uuid.UUID) -> List[CourseRoleClaim]:
        rows = await self.repo.list_user_active_roles(user_id)
        return [
            CourseRoleClaim(
                course_id=cid,
                role=role,
                course_code=code,
                course_name=name,
            )
            for cid, role, code, name in rows
        ]

    async def assert_course_role(
        self,
        course_id: uuid.UUID,
        user_id: uuid.UUID,
        allowed_roles: Iterable[ContextualRole],
        is_admin: bool = False,
    ) -> Optional[ContextualRole]:
        """Verify that user holds one of `allowed_roles` in the course (or is system ADMIN)."""
        if is_admin:
            return ContextualRole.INSTRUCTOR
        enrollment = await self.repo.get_enrollment(course_id, user_id)
        if (
            enrollment is None
            or enrollment.enrollment_status != EnrollmentStatus.ACTIVE.value
        ):
            raise CourseForbiddenException()
        role = ContextualRole(enrollment.contextual_role)
        if role not in set(allowed_roles):
            raise CourseForbiddenException()
        return role

    async def get_course_info(self, course_id: uuid.UUID) -> Optional[CourseInfoDTO]:
        course = await self.repo.get_course_by_id(course_id)
        if course is None:
            return None
        return CourseInfoDTO(
            id=course.id,
            course_code=course.course_code,
            section_code=course.section_code,
            name=course.name,
            semester=course.semester,
            credits=course.credits,
        )

    async def list_active_students(self, course_id: uuid.UUID) -> List[StudentEnrollmentDTO]:
        users = await self.repo.list_all_active_students(course_id)
        return [
            StudentEnrollmentDTO(
                user_id=u.id,
                user_code=u.user_code,
                full_name=u.full_name,
                email=u.email,
            )
            for u in users
        ]

    @staticmethod
    def register_lo_reference_checker(name: str, checker: LoReferenceChecker) -> None:
        register_lo_reference_checker(name, checker)


async def provide_course_roles_for_identity(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> List[CourseRoleClaim]:
    """Callback registered with identity.service to embed course_roles in JWT & /me."""
    return await CoursePublicService(db).get_user_course_roles(user_id)
