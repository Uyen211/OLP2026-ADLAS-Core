# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Business logic services for Course, Learning Objectives, Roster, and Groups."""

from collections import defaultdict, deque
from datetime import datetime, timezone
from html import escape
from html.parser import HTMLParser
from typing import Deque, Dict, List, Optional, Tuple
import uuid
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.course.enums import (
    BloomLevel,
    ContextualRole,
    CourseStatus,
    EnrollmentStatus,
    GroupingMode,
)
from app.modules.course.exceptions import (
    CourseForbiddenException,
    CourseNotFoundException,
    CourseValidationException,
    DuplicateResourceException,
    InvalidCourseStateException,
    JoinCodeInvalidException,
    JoinCodeRateLimitException,
    LoInUseException,
    RosterDuplicateException,
)
from app.modules.course.grouping import (
    partition_students_random,
    validate_group_set_members,
)
from app.modules.course.join_code import (
    generate_join_code,
    is_valid_join_code,
    normalize_join_code,
)
from app.modules.course.lifecycle import (
    assert_mutable,
    assert_transition,
    sync_enrollment_open,
)
from app.modules.course.lo_references import (
    LoReferenceRegistry,
    lo_reference_registry,
)
from app.modules.course.models import (
    Course,
    CourseEnrollment,
    LearningObjective,
)
from app.modules.course.repository import CourseRepository
from app.modules.course.roster_ingestion import parse_roster_bytes
from app.modules.course.schemas import (
    CourseCloneRequest,
    CourseCreate,
    CourseDetail,
    CourseSummary,
    GroupItemResponse,
    GroupMemberResponse,
    GroupPartitionPreviewRequest,
    GroupSetResponse,
    GroupSetSaveRequest,
    JoinCodeResponse,
    LOCreate,
    LOResponse,
    LOUpdate,
    RosterImportResult,
    RosterItemResponse,
    RosterPageResponse,
    RosterPreviewResponse,
    RosterPreviewRow,
    RosterRowError,
    RosterStudentCreate,
    SyllabusImportTemplateResponse,
    SyllabusUpdate,
)
from app.modules.identity.public_api import (
    IdentityPublicService,
    StudentAccountInput,
)
from app.modules.system.models import User

_ALLOWED_HTML_TAGS = {
    "p", "br", "strong", "b", "em", "i", "u", "s",
    "ul", "ol", "li", "h1", "h2", "h3", "h4",
    "table", "thead", "tbody", "tr", "th", "td",
    "blockquote", "code", "pre", "a",
}
_VOID_HTML_TAGS = {"br"}
_SAFE_URL_SCHEMES = ("http://", "https://", "mailto:")


class _AllowlistHtmlSanitizer(HTMLParser):
    """Minimal allowlist HTML sanitizer for TipTap syllabus content."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._parts: List[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        lower = tag.lower()
        if lower in ("script", "style"):
            self._skip_depth += 1
            return
        if self._skip_depth > 0 or lower not in _ALLOWED_HTML_TAGS:
            return
        if lower == "a":
            href = next((v for k, v in attrs if k.lower() == "href" and v), None)
            if href and href.strip().lower().startswith(_SAFE_URL_SCHEMES):
                safe_href = escape(href.strip(), quote=True)
                self._parts.append(f'<a href="{safe_href}" rel="noopener noreferrer">')
            else:
                self._parts.append("<a>")
        else:
            self._parts.append(f"<{lower}>")

    def handle_endtag(self, tag: str) -> None:
        lower = tag.lower()
        if lower in ("script", "style") and self._skip_depth > 0:
            self._skip_depth -= 1
            return
        if self._skip_depth > 0 or lower not in _ALLOWED_HTML_TAGS or lower in _VOID_HTML_TAGS:
            return
        self._parts.append(f"</{lower}>")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(escape(data))

    def get_html(self) -> str:
        return "".join(self._parts)


def sanitize_syllabus_html(raw_html: Optional[str]) -> Optional[str]:
    """Sanitize rich-text syllabus HTML using a strict tag allowlist."""
    if raw_html is None:
        return None
    sanitizer = _AllowlistHtmlSanitizer()
    sanitizer.feed(raw_html)
    sanitizer.close()
    return sanitizer.get_html()


class JoinCodeRateLimiter:
    """In-process per-user rate limiter (5 attempts/minute) for POST /courses/join."""

    def __init__(self, max_attempts: int = 5, window_seconds: int = 60):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: Dict[str, Deque[float]] = defaultdict(deque)

    def check_and_record(self, key: str) -> None:
        now = datetime.now(timezone.utc).timestamp()
        bucket = self._attempts[key]
        cutoff = now - self.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self.max_attempts:
            retry_after = int(self.window_seconds - (now - bucket[0]))
            raise JoinCodeRateLimitException(retry_after_seconds=max(1, retry_after))
        bucket.append(now)

    def reset_all(self) -> None:
        self._attempts.clear()


default_join_rate_limiter = JoinCodeRateLimiter()


def _to_lo_response(lo: LearningObjective) -> LOResponse:
    return LOResponse(
        id=lo.id,
        course_id=lo.course_id,
        code=lo.code,
        description=lo.description,
        bloom_level=BloomLevel(lo.bloom_level),
        order_index=lo.order_index,
        created_at=lo.created_at,
        updated_at=lo.updated_at,
    )


def _to_course_summary(
    course: Course,
    my_role: Optional[str] = None,
    student_count: int = 0,
    lo_count: int = 0,
) -> CourseSummary:
    return CourseSummary(
        id=course.id,
        course_code=course.course_code,
        section_code=course.section_code,
        name=course.name,
        semester=course.semester,
        credits=course.credits,
        start_date=course.start_date,
        end_date=course.end_date,
        is_template=course.is_template,
        is_enrollment_open=course.is_enrollment_open,
        status=CourseStatus(course.status),
        my_role=ContextualRole(my_role) if my_role else None,
        student_count=student_count,
        lo_count=lo_count,
    )


def _to_course_detail(
    course: Course,
    los: List[LearningObjective],
    my_role: Optional[str] = None,
    student_count: int = 0,
) -> CourseDetail:
    return CourseDetail(
        id=course.id,
        course_code=course.course_code,
        section_code=course.section_code,
        name=course.name,
        semester=course.semester,
        credits=course.credits,
        grading_scheme=course.grading_scheme,
        start_date=course.start_date,
        end_date=course.end_date,
        syllabus_text=course.syllabus_text,
        join_code=course.join_code,
        is_template=course.is_template,
        is_enrollment_open=course.is_enrollment_open,
        status=CourseStatus(course.status),
        my_role=ContextualRole(my_role) if my_role else None,
        student_count=student_count,
        lo_count=len(los),
        created_by=course.created_by,
        created_at=course.created_at,
        updated_at=course.updated_at,
        learning_objectives=[_to_lo_response(lo) for lo in los],
    )


class CourseService:
    """Course lifecycle, syllabus management, and BR-03 clean template cloning."""

    def __init__(self, db: AsyncSession, repo: Optional[CourseRepository] = None):
        self.db = db
        self.repo = repo or CourseRepository(db)

    async def _generate_unique_join_code(self, max_retries: int = 10) -> str:
        for _ in range(max_retries):
            candidate = generate_join_code()
            if not await self.repo.join_code_exists(candidate):
                return candidate
        raise InvalidCourseStateException("Khong the sinh ma vao lop duy nhat, vui long thu lai.")

    async def _assert_can_create_course(self, actor: User) -> None:
        """Plan Q3: System ADMIN or user who is an active INSTRUCTOR in at least one course."""
        if actor.system_role.upper() == "ADMIN":
            return
        if not await self.repo.is_user_instructor_anywhere(actor.id):
            raise CourseForbiddenException(
                "Chi giang vien hoac quan tri vien moi co quyen tao mon hoc moi."
            )

    async def _assert_instructor(self, course_id: uuid.UUID, actor: User) -> Course:
        course = await self.repo.get_course_by_id(course_id)
        if course is None:
            raise CourseNotFoundException()
        if actor.system_role.upper() == "ADMIN":
            return course
        enrollment = await self.repo.get_enrollment(course_id, actor.id)
        if (
            enrollment is None
            or enrollment.enrollment_status != EnrollmentStatus.ACTIVE.value
            or enrollment.contextual_role != ContextualRole.INSTRUCTOR.value
        ):
            raise CourseForbiddenException()
        return course

    async def _assert_member(self, course_id: uuid.UUID, actor: User) -> Tuple[Course, Optional[str]]:
        course = await self.repo.get_course_by_id(course_id)
        if course is None:
            raise CourseNotFoundException()
        if actor.system_role.upper() == "ADMIN":
            return course, ContextualRole.INSTRUCTOR.value
        enrollment = await self.repo.get_enrollment(course_id, actor.id)
        if enrollment is None or enrollment.enrollment_status != EnrollmentStatus.ACTIVE.value:
            raise CourseForbiddenException()
        return course, enrollment.contextual_role

    async def list_courses(
        self,
        actor: User,
        role_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> List[CourseSummary]:
        rows = await self.repo.list_courses_for_user(
            user_id=actor.id,
            is_admin=actor.system_role.upper() == "ADMIN",
            role_filter=role_filter,
            status_filter=status_filter,
            search_query=search_query,
        )
        course_ids = [course.id for course, _ in rows]
        student_counts, lo_counts = await self.repo.count_course_metrics(course_ids)
        return [
            _to_course_summary(
                course,
                my_role=role or (ContextualRole.INSTRUCTOR.value if actor.system_role.upper() == "ADMIN" else None),
                student_count=student_counts.get(course.id, 0),
                lo_count=lo_counts.get(course.id, 0),
            )
            for course, role in rows
        ]

    async def create_course(self, payload: CourseCreate, actor: User) -> CourseDetail:
        await self._assert_can_create_course(actor)
        join_code = None if payload.is_template else await self._generate_unique_join_code()
        course = Course(
            course_code=payload.course_code,
            section_code=payload.section_code,
            name=payload.name,
            semester=payload.semester,
            credits=payload.credits,
            grading_scheme=payload.grading_scheme,
            start_date=payload.start_date,
            end_date=payload.end_date,
            syllabus_text=sanitize_syllabus_html(payload.syllabus_text),
            join_code=join_code,
            is_enrollment_open=not payload.is_template,
            is_template=payload.is_template,
            status=CourseStatus.UNPUBLISHED.value,
            created_by=actor.id,
        )
        try:
            await self.repo.create_course(course)
        except IntegrityError as exc:
            raise DuplicateResourceException(
                detail="Ma hoc phan va ma lop nay da ton tai trong hoc ky hien tai.",
                field="section_code",
            ) from exc

        await self.repo.create_enrollment(
            CourseEnrollment(
                course_id=course.id,
                user_id=actor.id,
                contextual_role=ContextualRole.INSTRUCTOR.value,
                enrollment_status=EnrollmentStatus.ACTIVE.value,
            )
        )
        return _to_course_detail(course, los=[], my_role=ContextualRole.INSTRUCTOR.value, student_count=0)

    async def list_templates(self, actor: User) -> List[CourseSummary]:
        await self._assert_can_create_course(actor)
        templates = await self.repo.list_templates()
        course_ids = [c.id for c in templates]
        _, lo_counts = await self.repo.count_course_metrics(course_ids)
        return [
            _to_course_summary(
                c,
                my_role=ContextualRole.INSTRUCTOR.value,
                student_count=0,
                lo_count=lo_counts.get(c.id, 0),
            )
            for c in templates
        ]

    async def clone_from_template(self, payload: CourseCloneRequest, actor: User) -> CourseDetail:
        """
        BR-03: Deep-copy ONLY syllabus metadata and Learning Objectives from template.
        NEVER copy course_enrollments, course_groups, grades, or submissions.
        """
        await self._assert_can_create_course(actor)
        template = await self.repo.get_course_by_id(payload.template_id)
        if template is None or not template.is_template:
            raise CourseNotFoundException("Khong tim thay mon hoc mau yeu cau.")

        new_join_code = await self._generate_unique_join_code()
        cloned = Course(
            course_code=template.course_code,
            section_code=payload.section_code.strip(),
            name=template.name,
            semester=payload.semester.strip(),
            credits=template.credits,
            grading_scheme=template.grading_scheme,
            start_date=payload.start_date,
            end_date=payload.end_date,
            syllabus_text=template.syllabus_text,
            join_code=new_join_code,
            is_enrollment_open=True,
            is_template=False,
            status=CourseStatus.UNPUBLISHED.value,
            created_by=actor.id,
        )
        try:
            await self.repo.create_course(cloned)
        except IntegrityError as exc:
            raise DuplicateResourceException(
                detail="Lop hoc phan nay da ton tai trong hoc ky hien tai.",
                field="section_code",
            ) from exc

        # Enroll only the cloning instructor (zero students carried over per BR-03)
        await self.repo.create_enrollment(
            CourseEnrollment(
                course_id=cloned.id,
                user_id=actor.id,
                contextual_role=ContextualRole.INSTRUCTOR.value,
                enrollment_status=EnrollmentStatus.ACTIVE.value,
            )
        )

        template_los = await self.repo.list_los(template.id)
        copied_los: List[LearningObjective] = []
        for lo in template_los:
            new_lo = LearningObjective(
                course_id=cloned.id,
                code=lo.code,
                description=lo.description,
                bloom_level=lo.bloom_level,
                order_index=lo.order_index,
            )
            await self.repo.create_lo(new_lo)
            copied_los.append(new_lo)

        return _to_course_detail(
            cloned,
            los=copied_los,
            my_role=ContextualRole.INSTRUCTOR.value,
            student_count=0,
        )

    async def get_course_detail(self, course_id: uuid.UUID, actor: User) -> CourseDetail:
        course, my_role = await self._assert_member(course_id, actor)
        los = await self.repo.list_los(course.id)
        student_counts, _ = await self.repo.count_course_metrics([course.id])
        return _to_course_detail(
            course,
            los=los,
            my_role=my_role,
            student_count=student_counts.get(course.id, 0),
        )

    async def update_syllabus(
        self,
        course_id: uuid.UUID,
        payload: SyllabusUpdate,
        actor: User,
    ) -> CourseDetail:
        course = await self._assert_instructor(course_id, actor)
        assert_mutable(CourseStatus(course.status))

        course.name = payload.name.strip()
        course.credits = payload.credits
        course.syllabus_text = sanitize_syllabus_html(payload.syllabus_text)
        course.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        los = await self.repo.list_los(course.id)
        student_counts, _ = await self.repo.count_course_metrics([course.id])
        return _to_course_detail(
            course,
            los=los,
            my_role=ContextualRole.INSTRUCTOR.value,
            student_count=student_counts.get(course.id, 0),
        )

    async def import_syllabus_from_template(
        self,
        course_id: uuid.UUID,
        template_id: uuid.UUID,
        actor: User,
    ) -> SyllabusImportTemplateResponse:
        """BR-03 Subflow A-1: Copy syllabus_text and non-duplicate LOs into an existing course."""
        course = await self._assert_instructor(course_id, actor)
        assert_mutable(CourseStatus(course.status))

        template = await self.repo.get_course_by_id(template_id)
        if template is None or not template.is_template:
            raise CourseNotFoundException("Khong tim thay mon hoc mau yeu cau.")

        course.syllabus_text = template.syllabus_text
        course.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        existing_los = await self.repo.list_los(course.id)
        existing_codes = {lo.code.upper() for lo in existing_los}
        next_order = max((lo.order_index for lo in existing_los), default=0)

        template_los = await self.repo.list_los(template.id)
        copied_count = 0
        skipped: List[str] = []
        for t_lo in template_los:
            if t_lo.code.upper() in existing_codes:
                skipped.append(t_lo.code)
                continue
            next_order += 1
            await self.repo.create_lo(
                LearningObjective(
                    course_id=course.id,
                    code=t_lo.code,
                    description=t_lo.description,
                    bloom_level=t_lo.bloom_level,
                    order_index=next_order,
                )
            )
            existing_codes.add(t_lo.code.upper())
            copied_count += 1

        return SyllabusImportTemplateResponse(
            copied_los=copied_count,
            skipped_duplicate_codes=skipped,
        )

    async def transition_status(
        self,
        course_id: uuid.UUID,
        target_status: CourseStatus,
        actor: User,
    ) -> CourseDetail:
        course = await self._assert_instructor(course_id, actor)
        current_status = CourseStatus(course.status)
        assert_transition(current_status, target_status)

        if target_status == CourseStatus.PUBLISHED:
            lo_count = await self.repo.count_los(course.id)
            if lo_count < 1:
                raise InvalidCourseStateException(
                    "Can co it nhat 1 chuan dau ra (LO) truoc khi xuat ban mon hoc."
                )

        course.status = target_status.value
        course.is_enrollment_open = (
            False if course.is_template else sync_enrollment_open(target_status)
        )
        course.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        los = await self.repo.list_los(course.id)
        student_counts, _ = await self.repo.count_course_metrics([course.id])
        return _to_course_detail(
            course,
            los=los,
            my_role=ContextualRole.INSTRUCTOR.value,
            student_count=student_counts.get(course.id, 0),
        )


class LearningObjectiveService:
    """Learning Objective CRUD and BR-LO-01 deletion guard."""

    def __init__(
        self,
        db: AsyncSession,
        repo: Optional[CourseRepository] = None,
        ref_registry: Optional[LoReferenceRegistry] = None,
    ):
        self.db = db
        self.repo = repo or CourseRepository(db)
        self.course_svc = CourseService(db, self.repo)
        self.ref_registry = ref_registry or lo_reference_registry

    async def list_los(self, course_id: uuid.UUID, actor: User) -> List[LOResponse]:
        await self.course_svc._assert_member(course_id, actor)
        los = await self.repo.list_los(course_id)
        return [_to_lo_response(lo) for lo in los]

    async def create_lo(
        self,
        course_id: uuid.UUID,
        payload: LOCreate,
        actor: User,
    ) -> LOResponse:
        course = await self.course_svc._assert_instructor(course_id, actor)
        assert_mutable(CourseStatus(course.status))

        existing = await self.repo.list_los(course_id)
        next_order = max((lo.order_index for lo in existing), default=0) + 1
        lo = LearningObjective(
            course_id=course_id,
            code=payload.code,
            description=payload.description.strip(),
            bloom_level=payload.bloom_level.value,
            order_index=next_order,
        )
        try:
            await self.repo.create_lo(lo)
        except IntegrityError as exc:
            raise DuplicateResourceException(
                detail=f"Ma chuan dau ra '{payload.code}' da ton tai trong mon hoc.",
                field="code",
            ) from exc
        return _to_lo_response(lo)

    async def update_lo(
        self,
        course_id: uuid.UUID,
        lo_id: uuid.UUID,
        payload: LOUpdate,
        actor: User,
    ) -> LOResponse:
        course = await self.course_svc._assert_instructor(course_id, actor)
        assert_mutable(CourseStatus(course.status))

        lo = await self.repo.get_lo_by_id(course_id, lo_id)
        if lo is None:
            raise CourseNotFoundException("Khong tim thay chuan dau ra yeu cau.")

        if payload.code is not None:
            lo.code = payload.code
        if payload.description is not None:
            lo.description = payload.description.strip()
        if payload.bloom_level is not None:
            lo.bloom_level = payload.bloom_level.value
        lo.updated_at = datetime.now(timezone.utc)

        try:
            await self.db.flush()
        except IntegrityError as exc:
            raise DuplicateResourceException(
                detail=f"Ma chuan dau ra '{payload.code}' da ton tai trong mon hoc.",
                field="code",
            ) from exc
        return _to_lo_response(lo)

    async def delete_lo(self, course_id: uuid.UUID, lo_id: uuid.UUID, actor: User) -> None:
        course = await self.course_svc._assert_instructor(course_id, actor)
        assert_mutable(CourseStatus(course.status))

        lo = await self.repo.get_lo_by_id(course_id, lo_id)
        if lo is None:
            raise CourseNotFoundException("Khong tim thay chuan dau ra yeu cau.")

        if await self.ref_registry.is_lo_referenced(self.db, lo.id):
            raise LoInUseException(lo_code=lo.code)

        await self.repo.delete_lo(lo)

    async def reorder_los(
        self,
        course_id: uuid.UUID,
        ordered_ids: List[uuid.UUID],
        actor: User,
    ) -> None:
        course = await self.course_svc._assert_instructor(course_id, actor)
        assert_mutable(CourseStatus(course.status))

        los = await self.repo.list_los(course_id)
        by_id = {lo.id: lo for lo in los}
        now = datetime.now(timezone.utc)
        for idx, lo_id in enumerate(ordered_ids, start=1):
            if lo_id in by_id:
                by_id[lo_id].order_index = idx
                by_id[lo_id].updated_at = now
        await self.db.flush()


class RosterService:
    """Join Code lifecycle, student self-enrollment, and Excel/CSV roster ingestion."""

    def __init__(
        self,
        db: AsyncSession,
        repo: Optional[CourseRepository] = None,
        identity_public: Optional[IdentityPublicService] = None,
        join_limiter: Optional[JoinCodeRateLimiter] = None,
    ):
        self.db = db
        self.repo = repo or CourseRepository(db)
        self.course_svc = CourseService(db, self.repo)
        self.identity_public = identity_public or IdentityPublicService(db)
        self.join_limiter = join_limiter or default_join_rate_limiter

    async def get_join_code(self, course_id: uuid.UUID, actor: User) -> JoinCodeResponse:
        course = await self.course_svc._assert_instructor(course_id, actor)
        return JoinCodeResponse(
            join_code=course.join_code,
            is_enrollment_open=course.is_enrollment_open,
        )

    async def regenerate_join_code(self, course_id: uuid.UUID, actor: User) -> JoinCodeResponse:
        course = await self.course_svc._assert_instructor(course_id, actor)
        assert_mutable(CourseStatus(course.status))
        if course.is_template:
            raise InvalidCourseStateException("Mon hoc mau khong ho tro cap ma vao lop.")

        course.join_code = await self.course_svc._generate_unique_join_code()
        course.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return JoinCodeResponse(
            join_code=course.join_code,
            is_enrollment_open=course.is_enrollment_open,
        )

    async def update_join_code_settings(
        self,
        course_id: uuid.UUID,
        is_enrollment_open: bool,
        actor: User,
    ) -> CourseDetail:
        course = await self.course_svc._assert_instructor(course_id, actor)
        current_status = CourseStatus(course.status)
        assert_mutable(current_status)
        if course.is_template:
            raise InvalidCourseStateException("Mon hoc mau khong ho tro tu ghi danh.")

        course.is_enrollment_open = is_enrollment_open
        if current_status == CourseStatus.PUBLISHED and not is_enrollment_open:
            course.status = CourseStatus.ENROLLMENT_CLOSED.value
        elif current_status == CourseStatus.ENROLLMENT_CLOSED and is_enrollment_open:
            course.status = CourseStatus.PUBLISHED.value
        course.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        los = await self.repo.list_los(course.id)
        student_counts, _ = await self.repo.count_course_metrics([course.id])
        return _to_course_detail(
            course,
            los=los,
            my_role=ContextualRole.INSTRUCTOR.value,
            student_count=student_counts.get(course.id, 0),
        )

    async def join_by_code(self, raw_code: str, actor: User) -> CourseSummary:
        """Student self-enrollment via 6-character join code (BR-ROSTER-02)."""
        self.join_limiter.check_and_record(str(actor.id))

        code = normalize_join_code(raw_code)
        if not is_valid_join_code(code):
            raise JoinCodeInvalidException(
                detail="Ma tham gia lop khong ton tai hoac khong dung dinh dang.",
                status_code=404,
            )

        course = await self.repo.get_course_by_join_code(code)
        if course is None:
            raise JoinCodeInvalidException(
                detail="Ma tham gia lop khong ton tai trong he thong.",
                status_code=404,
            )

        if (
            course.is_template
            or course.status != CourseStatus.PUBLISHED.value
            or not course.is_enrollment_open
        ):
            raise JoinCodeInvalidException(
                detail="Lop hoc hien da dong cong tu ghi danh bang ma.",
                status_code=403,
            )

        existing = await self.repo.get_enrollment(course.id, actor.id)
        if existing is not None:
            if existing.enrollment_status == EnrollmentStatus.DROPPED.value:
                existing.enrollment_status = EnrollmentStatus.ACTIVE.value
                await self.db.flush()
            my_role = existing.contextual_role
        else:
            await self.repo.create_enrollment(
                CourseEnrollment(
                    course_id=course.id,
                    user_id=actor.id,
                    contextual_role=ContextualRole.STUDENT.value,
                    enrollment_status=EnrollmentStatus.ACTIVE.value,
                )
            )
            my_role = ContextualRole.STUDENT.value

        student_counts, lo_counts = await self.repo.count_course_metrics([course.id])
        return _to_course_summary(
            course,
            my_role=my_role,
            student_count=student_counts.get(course.id, 0),
            lo_count=lo_counts.get(course.id, 0),
        )

    async def list_roster(
        self,
        course_id: uuid.UUID,
        actor: User,
        search_query: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> RosterPageResponse:
        await self.course_svc._assert_instructor(course_id, actor)
        rows, total = await self.repo.list_active_students_with_users(
            course_id=course_id,
            search_query=search_query,
            page=page,
            page_size=page_size,
        )
        user_ids = [user.id for _, user in rows]
        group_names = await self.repo.get_student_group_names(course_id, user_ids)

        items = [
            RosterItemResponse(
                user_id=user.id,
                user_code=user.user_code,
                full_name=user.full_name,
                email=user.email,
                group_name=group_names.get(user.id),
                status=EnrollmentStatus(enrollment.enrollment_status),
                enrolled_at=enrollment.enrolled_at,
            )
            for enrollment, user in rows
        ]
        return RosterPageResponse(total=total, page=page, page_size=page_size, items=items)

    async def add_single_student(
        self,
        course_id: uuid.UUID,
        payload: RosterStudentCreate,
        actor: User,
    ) -> RosterItemResponse:
        course = await self.course_svc._assert_instructor(course_id, actor)
        assert_mutable(CourseStatus(course.status))
        if course.is_template:
            raise InvalidCourseStateException("Khong the them sinh vien vao mon hoc mau.")

        provisioned = await self.identity_public.get_or_create_students(
            [
                StudentAccountInput(
                    user_code=payload.user_code,
                    full_name=payload.full_name,
                    email=payload.email,
                )
            ]
        )
        student = provisioned[0]
        existing = await self.repo.get_enrollment(course_id, student.user_id)
        if existing is not None:
            if existing.enrollment_status == EnrollmentStatus.ACTIVE.value:
                raise RosterDuplicateException()
            existing.enrollment_status = EnrollmentStatus.ACTIVE.value
            existing.contextual_role = ContextualRole.STUDENT.value
            await self.db.flush()
            enrolled_at = existing.enrolled_at
        else:
            enrollment = await self.repo.create_enrollment(
                CourseEnrollment(
                    course_id=course_id,
                    user_id=student.user_id,
                    contextual_role=ContextualRole.STUDENT.value,
                    enrollment_status=EnrollmentStatus.ACTIVE.value,
                )
            )
            enrolled_at = enrollment.enrolled_at

        return RosterItemResponse(
            user_id=student.user_id,
            user_code=student.user_code,
            full_name=student.full_name,
            email=student.email,
            group_name=None,
            status=EnrollmentStatus.ACTIVE,
            enrolled_at=enrolled_at,
        )

    async def remove_student(
        self,
        course_id: uuid.UUID,
        student_user_id: uuid.UUID,
        actor: User,
    ) -> None:
        course = await self.course_svc._assert_instructor(course_id, actor)
        assert_mutable(CourseStatus(course.status))

        enrollment = await self.repo.get_enrollment(course_id, student_user_id)
        if enrollment is None:
            raise CourseNotFoundException("Sinh vien khong co trong danh sach lop.")
        await self.repo.update_enrollment_status(
            course_id,
            student_user_id,
            EnrollmentStatus.DROPPED,
        )

    async def preview_roster_file(
        self,
        course_id: uuid.UUID,
        filename: str,
        content: bytes,
        actor: User,
    ) -> RosterPreviewResponse:
        await self.course_svc._assert_instructor(course_id, actor)
        active_students = await self.repo.list_all_active_students(course_id)
        existing_emails = {u.email.lower() for u in active_students}
        existing_codes = {u.user_code.upper() for u in active_students if u.user_code}

        parsed = parse_roster_bytes(
            filename=filename,
            content=content,
            existing_course_emails=existing_emails,
            existing_course_codes=existing_codes,
        )
        return RosterPreviewResponse(
            total_rows=parsed.total_rows,
            valid_count=parsed.valid_count,
            duplicate_count=parsed.duplicate_count,
            error_count=parsed.error_count,
            preview_rows=[
                RosterPreviewRow(
                    row_number=r.row_number,
                    user_code=r.user_code,
                    full_name=r.full_name,
                    email=r.email,
                    status=r.status,
                    reason=r.reason,
                )
                for r in parsed.preview_rows
            ],
            errors=[RosterRowError(row_number=rn, reason=msg) for rn, msg in parsed.errors],
        )

    async def confirm_roster_file(
        self,
        course_id: uuid.UUID,
        filename: str,
        content: bytes,
        send_notification: bool,
        actor: User,
    ) -> RosterImportResult:
        course = await self.course_svc._assert_instructor(course_id, actor)
        assert_mutable(CourseStatus(course.status))
        if course.is_template:
            raise InvalidCourseStateException("Khong the nhap danh sach sinh vien vao mon hoc mau.")

        active_students = await self.repo.list_all_active_students(course_id)
        existing_emails = {u.email.lower() for u in active_students}
        existing_codes = {u.user_code.upper() for u in active_students if u.user_code}

        parsed = parse_roster_bytes(
            filename=filename,
            content=content,
            existing_course_emails=existing_emails,
            existing_course_codes=existing_codes,
        )

        provisioned = await self.identity_public.get_or_create_students(
            [
                StudentAccountInput(
                    user_code=r.user_code,
                    full_name=r.full_name,
                    email=r.email,
                )
                for r in parsed.valid_rows
            ]
        )
        user_ids = [item.user_id for item in provisioned]
        created_user_ids = [str(item.user_id) for item in provisioned if item.created]

        added = await self.repo.bulk_insert_student_enrollments(course_id, user_ids)
        skipped_duplicates = parsed.duplicate_count + max(0, len(user_ids) - added)

        if send_notification and created_user_ids:
            await self.repo.enqueue_outbox_event(
                event_type="course.roster_imported",
                aggregate_type="COURSE",
                aggregate_id=course_id,
                payload={
                    "course_id": str(course_id),
                    "course_code": course.course_code,
                    "created_user_ids": created_user_ids,
                    "notify": True,
                },
            )

        return RosterImportResult(
            added=added,
            skipped_duplicates=skipped_duplicates,
            created_accounts=len(created_user_ids),
            errors=[RosterRowError(row_number=rn, reason=msg) for rn, msg in parsed.errors],
        )


class GroupService:
    """Project group partitioning and manual/self-signup group management."""

    def __init__(self, db: AsyncSession, repo: Optional[CourseRepository] = None):
        self.db = db
        self.repo = repo or CourseRepository(db)
        self.course_svc = CourseService(db, self.repo)

    async def list_group_sets(self, course_id: uuid.UUID, actor: User) -> List[GroupSetResponse]:
        await self.course_svc._assert_member(course_id, actor)
        rows = await self.repo.list_groups_with_members(course_id)
        by_set: Dict[str, List[GroupItemResponse]] = defaultdict(list)
        for group, members in rows:
            by_set[group.group_set_name].append(
                GroupItemResponse(
                    id=group.id,
                    name=group.name,
                    members=[
                        GroupMemberResponse(
                            user_id=u.id,
                            user_code=u.user_code,
                            full_name=u.full_name,
                            email=u.email,
                        )
                        for u in members
                    ],
                )
            )
        return [
            GroupSetResponse(group_set_name=set_name, groups=groups)
            for set_name, groups in by_set.items()
        ]

    async def preview_partition(
        self,
        course_id: uuid.UUID,
        payload: GroupPartitionPreviewRequest,
        actor: User,
    ) -> GroupSetResponse:
        await self.course_svc._assert_instructor(course_id, actor)
        students = await self.repo.list_all_active_students(course_id)
        by_id = {u.id: u for u in students}

        if payload.mode == GroupingMode.RANDOM:
            partitioned = partition_students_random(
                student_ids=[u.id for u in students],
                group_size=payload.group_size,
            )
            groups = [
                GroupItemResponse(
                    id=None,
                    name=group_name,
                    members=[
                        GroupMemberResponse(
                            user_id=uid,
                            user_code=by_id[uid].user_code,
                            full_name=by_id[uid].full_name,
                            email=by_id[uid].email,
                        )
                        for uid in member_ids
                    ],
                )
                for group_name, member_ids in partitioned
            ]
        else:
            num_groups = max(1, (len(students) + payload.group_size - 1) // payload.group_size)
            groups = [
                GroupItemResponse(id=None, name=f"Nhom {i + 1}", members=[])
                for i in range(num_groups)
            ]

        return GroupSetResponse(
            group_set_name=payload.group_set_name.strip(),
            groups=groups,
        )

    async def save_group_set(
        self,
        course_id: uuid.UUID,
        group_set_name: str,
        payload: GroupSetSaveRequest,
        actor: User,
    ) -> GroupSetResponse:
        course = await self.course_svc._assert_instructor(course_id, actor)
        assert_mutable(CourseStatus(course.status))

        students = await self.repo.list_all_active_students(course_id)
        active_ids = {u.id for u in students}

        pairs = [(item.name, item.member_ids) for item in payload.groups]
        validate_group_set_members(pairs, active_ids)

        clean_set_name = group_set_name.strip()
        if not clean_set_name:
            raise CourseValidationException("Ten bo nhom khong duoc de trong.", field="group_set_name")

        await self.repo.replace_group_set(course_id, clean_set_name, pairs)
        all_sets = await self.list_group_sets(course_id, actor)
        for item in all_sets:
            if item.group_set_name == clean_set_name:
                return item
        return GroupSetResponse(group_set_name=clean_set_name, groups=[])

    async def student_join_group(
        self,
        course_id: uuid.UUID,
        group_id: uuid.UUID,
        actor: User,
    ) -> None:
        course, role = await self.course_svc._assert_member(course_id, actor)
        assert_mutable(CourseStatus(course.status))
        if role != ContextualRole.STUDENT.value:
            raise CourseForbiddenException("Chi sinh vien trong lop moi co the tu tham gia nhom.")

        group = await self.repo.get_group_by_id(course_id, group_id)
        if group is None:
            raise CourseNotFoundException("Khong tim thay nhom do an yeu cau.")

        if await self.repo.user_in_group_set(course_id, group.group_set_name, actor.id):
            raise DuplicateResourceException(
                detail="Ban da tham gia mot nhom khac trong cung bo nhom nay."
            )

        await self.repo.add_group_member(group.id, actor.id)
