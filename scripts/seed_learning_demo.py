# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Unified idempotent seed generator for 3 consistent courses covering TV1, TV2, and TV3."""

import asyncio
import os
import subprocess
import sys
import uuid
from datetime import UTC, date, datetime, timedelta

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv

env_path = os.path.join(REPO_ROOT, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

db_url = os.getenv("DATABASE_URL", "")
if "@postgres:" in db_url and not os.path.exists("/.dockerenv"):
    os.environ["DATABASE_URL"] = db_url.replace("@postgres:", "@localhost:")

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.modules.assessment.models import (
    Assignment,
    AssignmentSubmission,
    Rubric,
    RubricCriteria,
    VivaTranscript,
)
from app.modules.course.enums import (
    BloomLevel,
    ContextualRole,
    CourseStatus,
    EnrollmentStatus,
)
from app.modules.course.join_code import generate_join_code
from app.modules.course.models import Course, CourseEnrollment, LearningObjective
from app.modules.identity.repository import IdentityRepository
from app.modules.learning.enums import MaterialType
from app.modules.learning.models import LearningMaterial, LearningModule
from sqlalchemy import delete, select

SEED_NS = uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d")


def _det_uuid(key: str) -> uuid.UUID:
    """Generate a deterministic UUIDv5 so repeated runs never duplicate records."""
    return uuid.uuid5(SEED_NS, key)


def _generate_real_pdf(filepath: str, title: str, subtitle: str, sections: list[tuple[str, str]]) -> None:
    """Generate a valid multi-page academic PDF using PyMuPDF (fitz)."""
    try:
        import fitz

        doc = fitz.open()
        page = doc.new_page(width=595, height=842)  # A4

        # Header banner
        page.draw_rect(fitz.Rect(0, 0, 595, 110), color=(0.12, 0.25, 0.52), fill=(0.12, 0.25, 0.52))
        page.insert_text((40, 48), title, fontsize=18, fontname="helv", color=(1, 1, 1))
        page.insert_text((40, 76), subtitle, fontsize=11, fontname="helv", color=(0.85, 0.90, 1.0))

        y = 145
        for sec_title, sec_body in sections:
            if y > 740:
                page = doc.new_page(width=595, height=842)
                y = 60
            page.insert_text((40, y), sec_title, fontsize=13, fontname="helv", color=(0.12, 0.25, 0.52))
            y += 20
            rect = fitz.Rect(40, y, 555, y + 140)
            page.insert_textbox(rect, sec_body, fontsize=10.5, fontname="helv", color=(0.15, 0.15, 0.15), lineheight=1.4)
            y += 120

        # Footer
        for idx, p in enumerate(doc, start=1):
            p.insert_text((40, 815), f"ADLAS Learning Material | Page {idx}/{len(doc)}", fontsize=9, color=(0.45, 0.45, 0.45))

        doc.save(filepath)
        doc.close()
        return
    except ImportError:
        pass

    # Fallback valid minimal PDF if fitz is absent
    pdf_bytes = (
        b"%PDF-1.4\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj\n"
        b"4 0 obj << /Length 44 >> stream\nBT /F1 14 Tf 72 720 Td (ADLAS Academic Document) Tj ET\nendstream\nendobj\n"
        b"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
        b"0000000115 00000 n \n0000000201 00000 n \n"
        b"trailer << /Size 5 /Root 1 0 R >>\nstartxref\n295\n%%EOF\n"
    )
    with open(filepath, "wb") as f:
        f.write(pdf_bytes)


def _generate_real_pptx(filepath: str, title: str, subtitle: str, slides_data: list[tuple[str, list[str]]]) -> None:
    """Generate a valid PowerPoint presentation (.pptx) using python-pptx."""
    try:
        from pptx import Presentation

        prs = Presentation()
        # Title slide
        slide0 = prs.slides.add_slide(prs.slide_layouts[0])
        slide0.shapes.title.text = title
        slide0.placeholders[1].text = subtitle

        for s_title, bullets in slides_data:
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = s_title
            tf = slide.placeholders[1].text_frame
            for idx, b in enumerate(bullets):
                p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
                p.text = b
        prs.save(filepath)
        return
    except ImportError:
        with open(filepath, "wb") as f:
            f.write(b"PK\x03\x04ADLAS Slide Deck Placeholder - Run inside Docker to generate full PPTX")


def _generate_real_docx(filepath: str, title: str, intro: str, steps: list[str]) -> None:
    """Generate a valid Word document (.docx) using python-docx."""
    try:
        from docx import Document

        doc = Document()
        doc.add_heading(title, level=1)
        doc.add_paragraph(intro)
        doc.add_heading("Huong dan thuc hanh chi tiet", level=2)
        for step in steps:
            doc.add_paragraph(step, style="List Bullet")
        doc.save(filepath)
        return
    except ImportError:
        with open(filepath, "wb") as f:
            f.write(b"PK\x03\x04ADLAS Docx Placeholder - Run inside Docker to generate full DOCX")


def _sync_to_docker_volume(materials_dir: str) -> None:
    """Sync generated material files into running adlas-backend container volume if running on host."""
    if os.path.exists("/app"):
        return
    try:
        check = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", "adlas-backend"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if check.returncode == 0 and check.stdout.strip() == "true":
            subprocess.run(["docker", "exec", "adlas-backend", "mkdir", "-p", "/app/uploads/materials"], check=True, timeout=5)
            subprocess.run(["docker", "cp", f"{materials_dir}/.", "adlas-backend:/app/uploads/materials/"], check=True, timeout=15)
            print("[SEED] Synced real material files to adlas-backend:/app/uploads/materials/")
    except Exception as exc:
        print(f"[SEED] Note: Could not auto-sync to Docker container ({exc}).")


def _ensure_demo_files() -> dict[str, str]:
    """Create real academic demo files on disk and return relative storage paths ('materials/<filename>')."""
    base_upload_dir = os.getenv("UPLOAD_DIR")
    if not base_upload_dir:
        if os.path.exists("/app"):
            base_upload_dir = "/app/uploads"
        else:
            base_upload_dir = os.path.join(os.path.expanduser("~"), ".adlas", "uploads")
    materials_dir = os.path.join(base_upload_dir, "materials")
    os.makedirs(materials_dir, exist_ok=True)

    pdf_specs = {
        "it4409_ch1_rag_guide.pdf": (
            "IT4409 - Huong Dan Kien Truc RAG & Vector DB",
            "Chuong 1: Tong quan Retrieval-Augmented Generation (LO-01)",
            [
                ("1. Kien truc RAG Co ban", "RAG ket hop giua mo hinh ngon ngu lon (LLM) va he thong truy xuat thong tin (Retriever) tu co so du lieu vector nham giam thieu ao giac (hallucination) va cap nhat tri thuc chuyen nganh."),
                ("2. Quy trinh Chunking & Embedding", "Tai lieu hoc tap duoc chia nho thanh cac doan (chunks) 512 tokens voi overlap 64 tokens. Moi chunk duoc ma hoa thanh vector 1536 chieu va luu vao pgvector voi chi muc HNSW."),
                ("3. Truy van ngu nghia (Semantic Search)", "Su dung do do Cosine Similarity de tim Top-K doan van ban lien quan nhat truoc khi dua vao prompt cua gia su Socratic."),
            ],
        ),
        "it3080_ch1_rfc_notes.pdf": (
            "IT3080 - Tong Hop RFC Giao Thuc Mang",
            "Chuong 1: Mo hinh OSI & TCP/IP Protocol Suite (LO-01)",
            [
                ("1. TCP Three-Way Handshake (RFC 793)", "Ket noi TCP duoc thiet lap qua 3 buoc SYN, SYN-ACK, ACK nham dong bo so thu tu goi tin (Sequence Number) va dam bao truyen tin tin cay."),
                ("2. Kiem soat tac nghen (Congestion Control)", "Cac thuat toan Slow Start, Congestion Avoidance va Fast Recovery giup toi uu bang thong mang va tranh mat goi tin."),
            ],
        ),
        "it4010_ch1_clean_arch.pdf": (
            "IT4010 - Clean Architecture & Dependency Rule",
            "Chuong 1: Kien truc phan mem ben vung (LO-01)",
            [
                ("1. Nguyen tac Dependency Rule", "Cac tang nghiep vu cot loi (Domain Entities, Use Cases) khong duoc phep phu thuoc vao tang ha tang ben ngoai nhu Database, Framework hay UI."),
                ("2. Modular Monolith trong ADLAS", "Moi phan he (identity, course, learning, assessment) duoc to chuc doc lap voi ranh gioi giao tiep ro rang qua Service Layer."),
            ],
        ),
    }

    pptx_specs = {
        "it4409_ch1_architecture.pptx": (
            "IT4409: Kien truc He thong DX-OS",
            "Chuong 1 - Tong quan kien truc 4 tang ADLAS",
            [
                ("Muc tieu Bai giang (LO-01)", ["Nam vung kien truc 4-Tier: Gateway, Core API, Knowledge Engine, Infrastructure", "Hieu vai tro Kong API Gateway va Supabase Auth"]),
                ("Tich hop pgvector & Repomix", ["Phan tich ma nguon tu dong qua Repomix sidecar", "Luu tru embedding tren PostgreSQL 16 pgvector"]),
            ],
        ),
        "it4409_ch3_socratic.pptx": (
            "IT4409: Phuong phap Socratic Scaffolding",
            "Chuong 3 - Thiet ke Agent Ho tro Hoc tap (LO-03)",
            [
                ("Nguyen tac Socratic", ["Khong dua ngay dap an cuoi cung cho sinh vien", "Dat cau hoi goi mo tung buoc dua tren ngu canh bai hoc"]),
                ("Kiem soat ao giac", ["Neo cau tra loi vao tai lieu da duoc giang vien phe duyet"]),
            ],
        ),
        "it3080_ch1_osi_tcpip.pptx": (
            "IT3080: Mo hinh Phan tang OSI & TCP/IP",
            "Chuong 1 - Dong goi du lieu & Dinh tuyen",
            [
                ("7 Tang OSI vs 4 Tang TCP/IP", ["Application, Transport, Network, Data Link, Physical", "Encapsulation & Decapsulation qua tung tang"]),
            ],
        ),
        "it3080_ch3_firewall_rules.pptx": (
            "IT3080: Bao mat Mang & Tuong lua",
            "Chuong 3 - Stateless vs Stateful Firewall",
            [
                ("Co che loc goi tin", ["Kiem tra IP nguon/dich, Port va trang thai ket noi TCP", "Thiet ke luat ACL phong chong tan cong DDoS"]),
            ],
        ),
        "it4010_ch1_solid_gof.pptx": (
            "IT4010: Nguyen ly SOLID & Design Patterns",
            "Chuong 1 - Thiet ke Huong doi tuong nang cao",
            [
                ("5 Nguyen ly SOLID", ["Single Responsibility & Open/Closed Principle", "Dependency Inversion voi FastAPI Depends"]),
            ],
        ),
        "it4010_ch3_reliability.pptx": (
            "IT4010: High Availability & Scalability",
            "Chuong 3 - Kien truc he thong chiu tai cao",
            [
                ("Chien luoc mo rong", ["Horizontal Scaling voi Docker & Load Balancer", "Circuit Breaker va Retry Policy"]),
            ],
        ),
    }

    docx_specs = {
        "it4409_ch4_lab.docx": (
            "IT4409 - Bai Thuc Hanh Lab: Xay Dung RAG Pipeline",
            "Huong dan sinh vien trien khai he thong truy xuat tai lieu bang PostgreSQL pgvector.",
            [
                "Buoc 1: Khoi tao container PostgreSQL 16 voi extension pgvector.",
                "Buoc 2: Nap tai lieu PDF va thuc hien chunking theo ranh gioi doan van.",
                "Buoc 3: Tao chi muc HNSW va truy van Top-5 ngu canh lien quan.",
            ],
        ),
        "it3080_ch2_wireshark_lab.docx": (
            "IT3080 - Bai Thuc Hanh Lab: Phan tich Goi tin Wireshark",
            "Sinh vien su dung Wireshark de bat va phan tich qua trinh bat tay 3 buoc TCP.",
            [
                "Buoc 1: Chon giao dien mang va dat bo loc 'tcp.port == 8080'.",
                "Buoc 2: Quan sat cac goi tin SYN, SYN-ACK, ACK va Sequence Number.",
            ],
        ),
    }

    md_specs = {
        "it4409_ch2_pgvector_handbook.md": (
            "# Cẩm nang: Tối ưu truy vấn Cosine Similarity trên pgvector HNSW\n\n"
            "## 1. Chỉ mục HNSW (Hierarchical Navigable Small World)\n\n"
            "HNSW xây dựng đồ thị đa tầng giúp tìm kiếm vector lân cận gần đúng (ANN) với độ phức tạp $O(\\log N)$.\n\n"
            "```sql\n"
            "CREATE INDEX ON learning_chunks USING hnsw (embedding vector_cosine_ops)\n"
            "WITH (m = 16, ef_construction = 64);\n"
            "```\n\n"
            "## 2. Công thức Cosine Similarity\n\n"
            "$$\\text{similarity}(A, B) = \\frac{A \\cdot B}{\\|A\\| \\|B\\|}$$\n\n"
            "- Giá trị càng gần `1.0` thì hai đoạn văn bản càng tương đồng về mặt ngữ nghĩa.\n"
        ),
        "it4010_ch2_microservices.md": (
            "# Microservices & Event-Driven Patterns\n\n"
            "## 1. Giao tiếp Bất đồng bộ (Asynchronous Messaging)\n\n"
            "- Sử dụng Message Broker (Kafka / RabbitMQ) để tách rời các dịch vụ.\n"
            "- Đảm bảo tính nhất quán cuối cùng (Eventual Consistency) với Outbox Pattern.\n"
        ),
    }

    paths = {}
    for fname, args in pdf_specs.items():
        fpath = os.path.join(materials_dir, fname)
        if not os.path.exists(fpath) or os.path.getsize(fpath) < 500:
            _generate_real_pdf(fpath, *args)
        paths[fname] = f"materials/{fname}"

    for fname, args in pptx_specs.items():
        fpath = os.path.join(materials_dir, fname)
        if not os.path.exists(fpath) or os.path.getsize(fpath) < 500:
            _generate_real_pptx(fpath, *args)
        paths[fname] = f"materials/{fname}"

    for fname, args in docx_specs.items():
        fpath = os.path.join(materials_dir, fname)
        if not os.path.exists(fpath) or os.path.getsize(fpath) < 500:
            _generate_real_docx(fpath, *args)
        paths[fname] = f"materials/{fname}"

    for fname, content in md_specs.items():
        fpath = os.path.join(materials_dir, fname)
        if not os.path.exists(fpath) or os.path.getsize(fpath) < 120:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)
        paths[fname] = f"materials/{fname}"

    _sync_to_docker_volume(materials_dir)
    return paths


async def _ensure_accounts(db) -> dict:
    """Idempotently ensure core evaluation accounts exist."""
    id_repo = IdentityRepository(db)

    async def ensure_user(email: str, code: str, full_name: str, password: str, role: str = "USER"):
        existing = await id_repo.get_by_email(email)
        if existing is not None:
            return existing
        return await id_repo.create_user(
            email=email,
            user_code=code,
            full_name=full_name,
            password_hash=hash_password(password),
            system_role=role,
        )

    admin = await ensure_user("admin@adlas.edu.vn", "AD202600", "ADLAS System Admin", "AdminPass123!", role="ADMIN")
    teacher = await ensure_user("teacher1@adlas.edu.vn", "GV202601", "TS. Nguyen Minh Tuan", "TeacherPass123!")
    student1 = await ensure_user("student1@adlas.edu.vn", "SV2026001", "Le Hoang Nam", "StudentPass123!")
    student2 = await ensure_user("student2@adlas.edu.vn", "SV2026002", "Pham Thi Mai", "StudentPass123!")

    return {
        "admin": admin,
        "teacher": teacher,
        "student1": student1,
        "student2": student2,
    }


async def _cleanup_duplicate_template(db) -> None:
    """Remove unused IT4409 TEMPLATE course so only unified active courses remain."""
    tpl_stmt = select(Course).where(Course.course_code == "IT4409", Course.section_code == "TEMPLATE")
    tpl = (await db.execute(tpl_stmt)).scalar_one_or_none()
    if tpl is not None:
        asg_count = (await db.execute(select(Assignment).where(Assignment.course_id == tpl.id))).scalars().first()
        if asg_count is None:
            await db.execute(delete(LearningMaterial).where(LearningMaterial.module_id.in_(
                select(LearningModule.id).where(LearningModule.course_id == tpl.id)
            )))
            await db.execute(delete(LearningModule).where(LearningModule.course_id == tpl.id))
            await db.execute(delete(LearningObjective).where(LearningObjective.course_id == tpl.id))
            await db.execute(delete(CourseEnrollment).where(CourseEnrollment.course_id == tpl.id))
            await db.delete(tpl)
            await db.flush()
            print("[SEED] Cleaned up duplicate IT4409 - TEMPLATE record.")


async def _upsert_course_with_data(db, spec: dict, users: dict, file_paths: dict[str, str]) -> None:
    """Idempotently upsert a single course along with LOs, enrollments, modules, materials, and assessment data."""
    now = datetime.now(UTC)
    teacher = users["teacher"]
    student1 = users["student1"]
    student2 = users["student2"]

    # 1. Course
    stmt = select(Course).where(
        Course.course_code == spec["code"],
        Course.section_code == "L01",
    )
    course = (await db.execute(stmt)).scalar_one_or_none()
    if course is None:
        start = date.today()
        course = Course(
            id=_det_uuid(f"course:{spec['code']}:L01"),
            course_code=spec["code"],
            section_code="L01",
            name=spec["name"],
            semester="HK1-2026-2027",
            credits=spec["credits"],
            start_date=start,
            end_date=start + timedelta(days=90),
            syllabus_text=spec["syllabus"],
            join_code=generate_join_code(),
            is_enrollment_open=True,
            is_template=False,
            status=CourseStatus.PUBLISHED.value,
            created_by=teacher.id,
        )
        db.add(course)
        await db.flush()
        print(f"  + Created Course: {course.course_code} - {course.name}")
    else:
        course.name = spec["name"]
        course.syllabus_text = spec["syllabus"]
        course.status = CourseStatus.PUBLISHED.value
        print(f"  * Verified Course: {course.course_code} - {course.name}")

    # 2. Enrollments (Instructor + 2 Students)
    for usr, role in [
        (teacher, ContextualRole.INSTRUCTOR.value),
        (student1, ContextualRole.STUDENT.value),
        (student2, ContextualRole.STUDENT.value),
    ]:
        enr_stmt = select(CourseEnrollment).where(
            CourseEnrollment.course_id == course.id,
            CourseEnrollment.user_id == usr.id,
        )
        if (await db.execute(enr_stmt)).scalar_one_or_none() is None:
            db.add(
                CourseEnrollment(
                    course_id=course.id,
                    user_id=usr.id,
                    contextual_role=role,
                    enrollment_status=EnrollmentStatus.ACTIVE.value,
                )
            )
    await db.flush()

    # 3. Learning Objectives (LO-01, LO-02, LO-03)
    lo_map: dict[str, LearningObjective] = {}
    for idx, (lo_code, desc, bloom) in enumerate(spec["los"], start=1):
        lo_stmt = select(LearningObjective).where(
            LearningObjective.course_id == course.id,
            LearningObjective.code == lo_code,
        )
        lo = (await db.execute(lo_stmt)).scalar_one_or_none()
        if lo is None:
            lo = LearningObjective(
                id=_det_uuid(f"lo:{spec['code']}:{lo_code}"),
                course_id=course.id,
                code=lo_code,
                description=desc,
                bloom_level=bloom.value,
                order_index=idx,
            )
            db.add(lo)
            await db.flush()
        lo_map[lo_code] = lo

    # 4. Learning Modules & Materials (TV2)
    mod_map: dict[str, LearningModule] = {}
    for idx, mod_spec in enumerate(spec["modules"], start=1):
        mod_id = _det_uuid(f"module:{spec['code']}:{mod_spec['key']}")
        # Preserve fixed IDs for IT4409 if already seeded with earlier UUIDs
        existing_by_title = (
            await db.execute(
                select(LearningModule).where(
                    LearningModule.course_id == course.id,
                    LearningModule.title == mod_spec["title"],
                )
            )
        ).scalar_one_or_none()

        mod = existing_by_title or (await db.execute(select(LearningModule).where(LearningModule.id == mod_id))).scalar_one_or_none()
        prereq_id = mod_map[mod_spec["prereq"]].id if mod_spec.get("prereq") in mod_map else None
        unlock_at = (now + timedelta(days=mod_spec["unlock_days"])) if mod_spec.get("unlock_days") else None

        if mod is None:
            mod = LearningModule(
                id=mod_id,
                course_id=course.id,
                title=mod_spec["title"],
                order_index=idx,
                unlock_at=unlock_at,
                prerequisite_module_id=prereq_id,
                is_published=mod_spec.get("is_published", True),
            )
            db.add(mod)
            await db.flush()
        else:
            mod.prerequisite_module_id = prereq_id
            mod.unlock_at = unlock_at
            mod.is_published = mod_spec.get("is_published", True)
        mod_map[mod_spec["key"]] = mod

        # Materials inside module
        for mat_spec in mod_spec["materials"]:
            mat_id = _det_uuid(f"material:{spec['code']}:{mat_spec['key']}")
            existing_mat = (
                await db.execute(
                    select(LearningMaterial).where(
                        LearningMaterial.module_id == mod.id,
                        LearningMaterial.title == mat_spec["title"],
                    )
                )
            ).scalar_one_or_none()

            if existing_mat is None:
                lo_ref = lo_map.get(mat_spec["lo"]).id if mat_spec.get("lo") else None
                f_url = mat_spec.get("url") or file_paths.get(mat_spec.get("file", ""), "")
                db.add(
                    LearningMaterial(
                        id=mat_id,
                        module_id=mod.id,
                        lo_id=lo_ref,
                        title=mat_spec["title"],
                        material_type=mat_spec["type"].value,
                        file_url=f_url,
                        is_mandatory=mat_spec.get("mandatory", True),
                        est_duration_minutes=mat_spec.get("duration", 30),
                        is_published=mat_spec.get("is_published", True),
                    )
                )
            else:
                f_url = mat_spec.get("url") or file_paths.get(mat_spec.get("file", ""), "")
                if f_url:
                    existing_mat.file_url = f_url
    await db.flush()

    # 5. Assessment, Rubrics & Submissions (TV1 & TV3)
    asg_spec = spec["assignment"]
    asg_id = _det_uuid(f"assignment:{spec['code']}:main")
    asg = (
        await db.execute(
            select(Assignment).where(
                Assignment.course_id == course.id,
                Assignment.title == asg_spec["title"],
            )
        )
    ).scalar_one_or_none()

    if asg is None:
        asg = Assignment(
            id=asg_id,
            course_id=course.id,
            title=asg_spec["title"],
            instructions=asg_spec["instructions"],
            submission_type="FILE_UPLOAD",
            allowed_extensions=".zip,.pdf,.docx",
            max_file_size_mb=50,
            is_group_assignment=False,
            is_transfer_task=False,
            due_date=now + timedelta(days=14),
            is_viva_required=True,
            viva_question_count=asg_spec.get("viva_count", 3),
            ai_policy_level="YELLOW",
        )
        db.add(asg)
        await db.flush()

    # Rubric & Criteria (TV3)
    rubric = (await db.execute(select(Rubric).where(Rubric.assignment_id == asg.id))).scalar_one_or_none()
    if rubric is None:
        rubric = Rubric(
            id=_det_uuid(f"rubric:{spec['code']}:main"),
            assignment_id=asg.id,
            title=f"Rubric Danh gia - {spec['code']}",
            total_points=10.0,
            is_frozen=False,
            version=1,
        )
        db.add(rubric)
        await db.flush()

        for c_idx, (c_code, c_title, lo_code, pts) in enumerate(asg_spec["criteria"], start=1):
            db.add(
                RubricCriteria(
                    id=_det_uuid(f"criteria:{spec['code']}:{c_code}:{c_idx}"),
                    rubric_id=rubric.id,
                    lo_id=lo_map[lo_code].id if lo_code in lo_map else None,
                    competency_code=c_code,
                    title=c_title,
                    description=f"Tieu chi danh gia nang luc {c_code} lien ket chuan dau ra {lo_code}",
                    max_points=pts,
                    rating_levels=[
                        {"label": "Xuat sac", "points": pts, "desc": "Hoan thanh toan dien va giai thich sau sac"},
                        {"label": "Dat", "points": round(pts * 0.7, 1), "desc": "Dap ung yeu cau co ban"},
                        {"label": "Chua dat", "points": 0.0, "desc": "Thieu minh chung hoac khong vuot qua viva"},
                    ],
                    order_index=c_idx,
                )
            )
        await db.flush()

    # Student Submission + Viva Transcript (if configured)
    if asg_spec.get("seed_submission"):
        sub_stmt = select(AssignmentSubmission).where(
            AssignmentSubmission.assignment_id == asg.id,
            AssignmentSubmission.user_id == student1.id,
            AssignmentSubmission.version == 1,
        )
        sub = (await db.execute(sub_stmt)).scalar_one_or_none()
        if sub is None:
            sub = AssignmentSubmission(
                id=_det_uuid(f"submission:{spec['code']}:student1:v1"),
                assignment_id=asg.id,
                user_id=student1.id,
                version=1,
                project_title=asg_spec["submission_title"],
                file_url=f"uploads/submissions/{spec['code'].lower()}_demo_submission.zip",
                comments="Em da hoan thanh bao cao va ma nguon theo dung huong dan.",
                ai_disclosure_data={"tools_used": ["GitHub Copilot"], "purpose": "Ho tro viet unit test"},
                self_contribution_pct=85,
                is_pledge_signed=True,
                status="VIVA_COMPLETED",
            )
            db.add(sub)
            await db.flush()

            db.add(
                VivaTranscript(
                    id=_det_uuid(f"viva:{spec['code']}:student1:v1"),
                    submission_id=sub.id,
                    questions_answers={
                        "generation_source": "seed_demo",
                        "ai_digest_summary": f"Sinh vien trinh bay giai phap cho {spec['code']} voi do tin cay cao.",
                        "items": [
                            {
                                "question": "Giai thich quyet dinh kien truc chinh trong bai nop cua ban?",
                                "answer": "Em ap dung tach biet tang Service va Repository de de kiem thu va bao tri.",
                                "score": 8.5,
                            }
                        ],
                    },
                    violation_logs=[],
                    started_at=now - timedelta(minutes=15),
                    completed_at=now - timedelta(minutes=5),
                    status="COMPLETED",
                )
            )
            await db.flush()


COURSE_SPECS = [
    {
        "code": "IT4409",
        "name": "Phát triển Ứng dụng Web Nâng cao",
        "credits": 3,
        "syllabus": "<p>Học phần trang bị kiến thức xây dựng hệ thống Web hiện đại theo kiến trúc phân tầng, API an toàn, Vector Database và tích hợp AI.</p>",
        "los": [
            ("LO-01", "Hiểu và áp dụng kiến trúc phân tầng trong phần mềm web", BloomLevel.UNDERSTAND),
            ("LO-02", "Thiết kế và xây dựng REST API an toàn với xác thực JWT và phân quyền RBAC", BloomLevel.APPLY),
            ("LO-03", "Đánh giá hiệu năng, bảo mật và kiểm thử tự động toàn trình hệ thống web", BloomLevel.EVALUATE),
        ],
        "modules": [
            {
                "key": "m1",
                "title": "Chương 1: Tổng quan Kiến trúc Hệ thống & RAG Tri thức",
                "is_published": True,
                "materials": [
                    {"key": "mat1", "title": "Slide Bài giảng: Kiến trúc DX-OS Open-Core và 8 Bounded Contexts", "type": MaterialType.SLIDE, "file": "it4409_ch1_architecture.pptx", "lo": "LO-01", "duration": 45},
                    {"key": "mat2", "title": "Tài liệu đọc: Hướng dẫn RAG và Vector Database trong Giáo dục Đại học", "type": MaterialType.PDF, "file": "it4409_ch1_rag_guide.pdf", "lo": "LO-01", "duration": 30},
                ],
            },
            {
                "key": "m2",
                "title": "Chương 2: Kỹ thuật Chunking & Vector Database pgvector",
                "prereq": "m1",
                "is_published": True,
                "materials": [
                    {"key": "mat3", "title": "Video: Trực quan hóa HNSW Indexing với m=16 và ef_construction=64", "type": MaterialType.VIDEO, "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4", "lo": "LO-02", "duration": 25},
                    {"key": "mat4", "title": "Cẩm nang: Tối ưu truy vấn Cosine Similarity trên PostgreSQL 16", "type": MaterialType.DOCUMENT, "file": "it4409_ch2_pgvector_handbook.md", "lo": "LO-02", "mandatory": False, "duration": 20},
                ],
            },
            {
                "key": "m3",
                "title": "Chương 3: Động cơ Đối thoại Socratic AI (Socratic Dialog Engine)",
                "unlock_days": 3,
                "is_published": True,
                "materials": [
                    {"key": "mat5", "title": "Slide: Phương pháp Socratic Scaffolding và Hướng dẫn Tư duy Từng bước", "type": MaterialType.SLIDE, "file": "it4409_ch3_socratic.pptx", "lo": "LO-03", "duration": 40},
                ],
            },
            {
                "key": "m4",
                "title": "Chương 4: Đánh giá Năng lực Đa chiều (Bản nháp)",
                "is_published": False,
                "materials": [
                    {"key": "mat6", "title": "Đề cương bài tập thực hành phòng Lab (Nội dung nháp)", "type": MaterialType.DOCUMENT, "file": "it4409_ch4_lab.docx", "lo": "LO-03", "mandatory": False, "duration": 15, "is_published": False},
                ],
            },
        ],
        "assignment": {
            "title": "Đồ án giữa kỳ: Xây dựng API Hệ thống Quản lý Học liệu & RAG",
            "instructions": "Nộp báo cáo kiến trúc và mã nguồn backend FastAPI kèm unit tests. Sinh viên cần tham gia phiên vấn đáp Viva.",
            "viva_count": 3,
            "seed_submission": True,
            "submission_title": "Hệ thống RAG Learning Engine trên FastAPI & pgvector",
            "criteria": [
                ("C1", "Thiết kế kiến trúc phân tầng Bounded Context", "LO-01", 3.0),
                ("C2", "Xây dựng API an toàn và kiểm soát truy cập RBAC", "LO-02", 4.0),
                ("C4", "Kiểm thử tự động và bảo vệ Viva", "LO-03", 3.0),
            ],
        },
    },
    {
        "code": "IT3080",
        "name": "Mạng Máy tính & An toàn Thông tin",
        "credits": 3,
        "syllabus": "<p>Học phần cung cấp kiến thức về kiến trúc mạng OSI/TCP-IP, phân tích gói tin và các nguyên tắc bảo mật hệ thống mạng.</p>",
        "los": [
            ("LO-01", "Phân tích các giao thức mạng trong mô hình OSI/TCP-IP", BloomLevel.ANALYZE),
            ("LO-02", "Cấu hình phân tích lưu lượng mạng và phát hiện bất thường bằng Wireshark", BloomLevel.APPLY),
            ("LO-03", "Thiết kế chính sách an toàn thông tin và phòng thủ tấn công mạng cơ bản", BloomLevel.CREATE),
        ],
        "modules": [
            {
                "key": "m1",
                "title": "Chương 1: Mô hình OSI & Họ giao thức TCP/IP",
                "is_published": True,
                "materials": [
                    {"key": "mat1", "title": "Slide: Phân tích chi tiết tầng Giao vận (TCP/UDP)", "type": MaterialType.SLIDE, "file": "it3080_ch1_osi_tcpip.pptx", "lo": "LO-01", "duration": 45},
                    {"key": "mat2", "title": "Tài liệu tham khảo: Chuẩn giao thức RFC 791 & 793", "type": MaterialType.PDF, "file": "it3080_ch1_rfc_notes.pdf", "lo": "LO-01", "duration": 35},
                ],
            },
            {
                "key": "m2",
                "title": "Chương 2: Phân tích Gói tin với Wireshark",
                "prereq": "m1",
                "is_published": True,
                "materials": [
                    {"key": "mat3", "title": "Hướng dẫn thực hành: Bắt và lọc gói tin HTTP/DNS bất thường", "type": MaterialType.DOCUMENT, "file": "it3080_ch2_wireshark_lab.docx", "lo": "LO-02", "duration": 40},
                ],
            },
            {
                "key": "m3",
                "title": "Chương 3: Tường lửa & Phòng thủ Tấn công Mạng",
                "prereq": "m2",
                "is_published": True,
                "materials": [
                    {"key": "mat4", "title": "Slide: Thiết lập quy tắc Iptables và Chống DDoS cơ bản", "type": MaterialType.SLIDE, "file": "it3080_ch3_firewall_rules.pptx", "lo": "LO-03", "duration": 50},
                ],
            },
        ],
        "assignment": {
            "title": "Bài thực hành Lab 2: Điều tra lưu lượng mạng độc hại (PCAP Analysis)",
            "instructions": "Phân tích tệp PCAP mẫu, chỉ ra IP nguồn tấn công và giải thích cơ chế gói tin trong phiên Viva.",
            "viva_count": 3,
            "seed_submission": True,
            "submission_title": "Báo cáo điều tra gói tin SYN Flood trên Wireshark",
            "criteria": [
                ("C2", "Kỹ năng đọc và lọc gói tin TCP/IP", "LO-01", 4.0),
                ("C3", "Phát hiện dấu hiệu bất thường và đề xuất luật tường lửa", "LO-02", 6.0),
            ],
        },
    },
    {
        "code": "IT4010",
        "name": "Kiến trúc & Thiết kế Phần mềm",
        "credits": 3,
        "syllabus": "<p>Học phần tập trung vào nguyên lý SOLID, các mẫu thiết kế hướng đối tượng (Design Patterns) và kiến trúc hệ thống phân tán.</p>",
        "los": [
            ("LO-01", "Nhận diện và giải thích các nguyên lý thiết kế SOLID và mẫu thiết kế GOF", BloomLevel.UNDERSTAND),
            ("LO-02", "Xây dựng kiến trúc Microservices và Event-Driven Architecture", BloomLevel.APPLY),
            ("LO-03", "Đánh giá các đánh đổi kiến trúc và khả năng chịu tải hệ thống", BloomLevel.EVALUATE),
        ],
        "modules": [
            {
                "key": "m1",
                "title": "Chương 1: Nguyên lý SOLID & Các mẫu thiết kế GOF",
                "is_published": True,
                "materials": [
                    {"key": "mat1", "title": "Slide: Dependency Inversion và Clean Architecture", "type": MaterialType.SLIDE, "file": "it4010_ch1_solid_gof.pptx", "lo": "LO-01", "duration": 45},
                    {"key": "mat2", "title": "Tài liệu đọc: Clean Architecture trong dự án thực tế", "type": MaterialType.PDF, "file": "it4010_ch1_clean_arch.pdf", "lo": "LO-01", "duration": 30},
                ],
            },
            {
                "key": "m2",
                "title": "Chương 2: Kiến trúc Microservices & Message Broker",
                "prereq": "m1",
                "is_published": True,
                "materials": [
                    {"key": "mat3", "title": "Cẩm nang: Giao tiếp bất đồng bộ với Kafka/RabbitMQ", "type": MaterialType.DOCUMENT, "file": "it4010_ch2_microservices.md", "lo": "LO-02", "duration": 35},
                ],
            },
            {
                "key": "m3",
                "title": "Chương 3: Đánh giá Độ tin cậy và Khả năng Mở rộng",
                "is_published": True,
                "materials": [
                    {"key": "mat4", "title": "Slide: Circuit Breaker, Rate Limiting và High Availability", "type": MaterialType.SLIDE, "file": "it4010_ch3_reliability.pptx", "lo": "LO-03", "duration": 40},
                ],
            },
        ],
        "assignment": {
            "title": "Đồ án cuối kỳ: Thiết kế Kiến trúc Hệ thống Đặt vé Trực tuyến Chịu tải cao",
            "instructions": "Thiết kế sơ đồ kiến trúc C4 Model, lựa chọn mẫu thiết kế phù hợp và bảo vệ các đánh đổi (trade-offs).",
            "viva_count": 4,
            "seed_submission": False,
            "criteria": [
                ("C1", "Áp dụng chuẩn xác nguyên lý SOLID và Design Patterns", "LO-01", 3.5),
                ("C4", "Thiết kế giao tiếp bất đồng bộ và phân tách dịch vụ", "LO-02", 3.5),
                ("C5", "Phân tích đánh đổi kiến trúc (CAP, Latency vs Consistency)", "LO-03", 3.0),
            ],
        },
    },
]


async def seed_learning_demo() -> None:
    """Run unified 3-course cross-context seed idempotently."""
    file_paths = _ensure_demo_files()

    async with AsyncSessionLocal() as db:
        users = await _ensure_accounts(db)
        await _cleanup_duplicate_template(db)

        print("[SEED] Synchronizing 3 unified courses (TV1 + TV2 + TV3 data)...")
        for spec in COURSE_SPECS:
            await _upsert_course_with_data(db, spec, users, file_paths)

        await db.commit()
        print("[SEED] Completed successfully! 3 courses are consistent and ready.")


if __name__ == "__main__":
    asyncio.run(seed_learning_demo())
