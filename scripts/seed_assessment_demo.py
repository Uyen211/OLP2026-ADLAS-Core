# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Seed script to populate a sample Assignment and Submission for T2-P-M3-04 and T2-I-M3-05 demo."""

import asyncio
from datetime import datetime, timedelta, timezone
import os
import sys
import uuid

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.modules.assessment.models import Assignment, AssignmentSubmission, VivaTranscript
from app.modules.course.models import Course
from app.modules.system.models import User

ASSIGNMENT_ID = uuid.UUID("a1111111-1111-1111-1111-111111111111")
SUBMISSION_ID = uuid.UUID("b2222222-2222-2222-2222-222222222222")


async def seed_assessment_demo() -> None:
    async with AsyncSessionLocal() as db:
        # 1. Get course and student
        course_stmt = select(Course).where(Course.course_code == "IT4409", Course.section_code == "L01")
        course = (await db.execute(course_stmt)).scalar_one_or_none()
        if not course:
            course_all = (await db.execute(select(Course).limit(1))).scalar_one_or_none()
            course = course_all
        if not course:
            print("No course found!")
            return

        student_stmt = select(User).where(User.email == "student1@adlas.edu.vn")
        student = (await db.execute(student_stmt)).scalar_one_or_none()
        if not student:
            print("Student not found!")
            return

        # 2. Upsert Assignment
        now = datetime.now(timezone.utc)
        due = now + timedelta(days=7)
        until = now + timedelta(days=14)

        assign_stmt = select(Assignment).where(Assignment.id == ASSIGNMENT_ID)
        assignment = (await db.execute(assign_stmt)).scalar_one_or_none()
        if not assignment:
            assignment = Assignment(
                id=ASSIGNMENT_ID,
                course_id=course.id,
                title="Bài tập lớn: Phát triển hệ thống Trích xuất Tri thức & AI Chatbot",
                instructions="""## Yêu cầu bài tập lớn (T2-P-M3-04 & T2-I-M3-05)

Sinh viên thực hiện thiết kế và phát triển mô-đun dịch vụ phân tích dữ liệu văn bản và tích hợp mô hình ngôn ngữ tự nhiên (NLP).

### 1. Yêu cầu sản phẩm:
- Xây dựng pipeline trích xuất văn bản (PDF, DOCX) theo thuật toán Sliding Window và Recursive Map-Reduce.
- Tích hợp Git repository service (Repomix) đóng gói ngữ cảnh mã nguồn an toàn.
- Kiểm thử tự động đạt độ phủ trên 80%.

### 2. Quy chế nộp bài và Liêm chính học thuật:
- Bắt buộc khai báo trung thực tỷ lệ sử dụng AI (AI Disclosure) và mô tả chi tiết prompt chính.
- Sau khi nộp bài, sinh viên bắt buộc tham gia phòng thi vấn đáp Viva Sandbox trực tiếp để bảo vệ kết quả.""",
                submission_type="DUAL",
                allowed_extensions=".zip,.pdf,.docx,.tar.gz",
                max_file_size_mb=25,
                is_group_assignment=False,
                is_transfer_task=False,
                due_date=due,
                until_date=until,
                late_penalty_percent=5.0,
                is_viva_required=True,
                viva_question_count=5,
            )
            db.add(assignment)
            await db.flush()
            print(f"Created Assignment: {ASSIGNMENT_ID}")
        else:
            print(f"Assignment {ASSIGNMENT_ID} already exists.")

        # 3. Upsert Submission
        sub_stmt = select(AssignmentSubmission).where(AssignmentSubmission.id == SUBMISSION_ID)
        sub = (await db.execute(sub_stmt)).scalar_one_or_none()
        project_title = "Nghiên cứu mô hình Active Learning cho bài toán trích xuất thực thể y sinh tiếng Việt (VietBioNER)"
        
        if not sub:
            sub = AssignmentSubmission(
                id=SUBMISSION_ID,
                assignment_id=ASSIGNMENT_ID,
                user_id=student.id,
                version=1,
                project_title=project_title,
                git_repo_url="https://github.com/Uyen211/research_activelearning_vietbioner.git",
                file_url="https://storage.adlas.edu.vn/submissions/NLP-BTL-Nguyen_Ha_Phuong_Uyen.docx",
                comments="Bài nộp hoàn thiện kèm mô hình trích xuất tri thức và pipeline tiền xử lý.",
                ai_disclosure_data={
                    "self_contribution_pct": 80,
                    "tools_used": ["ChatGPT", "GitHub Copilot"],
                    "usage_description": "Em sử dụng ChatGPT để tham khảo ý tưởng tiền xử lý dữ liệu và hỗ trợ sinh các unit test biên; toàn bộ thuật toán trích xuất thực thể tên riêng và huấn luyện Active Learning do em tự cài đặt.",
                },
                self_contribution_pct=80,
                is_pledge_signed=True,
                submitted_at=now - timedelta(hours=1),
                is_late=False,
                late_penalty_applied=0.0,
                status="SUBMITTED",
            )
            db.add(sub)
            await db.commit()
            print(f"Created Submission: {SUBMISSION_ID}")
        else:
            sub.project_title = project_title
            await db.commit()
            print(f"Updated Submission {SUBMISSION_ID} with project_title.")

        # 4. Upsert VivaTranscript
        trans_stmt = select(VivaTranscript).where(VivaTranscript.submission_id == SUBMISSION_ID)
        trans = (await db.execute(trans_stmt)).scalar_one_or_none()
        viva_payload = {
            "total_questions": 5,
            "current_index": 1,
            "questions": [
                {
                    "id": "q1",
                    "question_index": 1,
                    "total_questions": 5,
                    "question_text": "Trong kiến trúc PhoBERT + BiLSTM-CRF, tại sao bạn lại chọn sử dụng lớp CRF ở tầng cuối cùng thay vì một lớp Softmax thông thường, và cơ chế này hỗ trợ như thế nào trong việc duy trì tính nhất quán của các nhãn thực thể y sinh (như B-DISEASE, I-DISEASE)?",
                    "category": "DEFENSE",
                },
                {
                    "id": "q2",
                    "question_index": 2,
                    "total_questions": 5,
                    "question_text": "Dữ liệu y sinh tiếng Việt thường có tính chuyên môn cao và từ vựng đặc thù. Bạn đã xử lý vấn đề Out-of-Vocabulary (OOV) hoặc các từ viết tắt trong bệnh án như thế nào khi sử dụng bộ tokenizer mặc định của PhoBERT?",
                    "category": "DEFENSE",
                },
                {
                    "id": "q3",
                    "question_index": 3,
                    "total_questions": 5,
                    "question_text": "Chiến lược chọn mẫu dựa trên Least Confidence và Entropy thường có xu hướng chọn các mẫu nhiễu (outliers). Bạn đã thực hiện biện pháp gì để đảm bảo các mẫu được chọn cho chuyên gia gán nhãn là các mẫu thực sự có giá trị thông tin thay vì chỉ là dữ liệu nhiễu?",
                    "category": "DEFENSE",
                },
                {
                    "id": "q4",
                    "question_index": 4,
                    "total_questions": 5,
                    "question_text": "Trong phần khai báo sử dụng AI, bạn đề cập dùng ChatGPT để sinh unit test biên. Hãy chỉ ra một trường hợp kiểm thử cụ thể mà AI đã gợi ý giúp bạn phát hiện lỗi trong logic của thuật toán Active Learning hoặc quá trình hậu xử lý nhãn?",
                    "category": "DEFENSE",
                },
                {
                    "id": "q5",
                    "question_index": 5,
                    "total_questions": 5,
                    "question_text": "Dựa trên kết quả thực nghiệm, tại ngưỡng bao nhiêu phần trăm dữ liệu được gán nhãn thì mô hình Active Learning của bạn đạt được hiệu năng tương đương với việc huấn luyện trên toàn bộ 5000 câu? Hãy phân tích sự đánh đổi giữa độ chính xác và chi phí gán nhãn trong dự án này.",
                    "category": "DEFENSE",
                },
            ],
            "answers": {},
        }
        if not trans:
            trans = VivaTranscript(
                submission_id=SUBMISSION_ID,
                status="READY",
                questions_answers=viva_payload,
                violation_logs=[],
            )
            db.add(trans)
            await db.commit()
            print(f"Created Viva Transcript for submission: {SUBMISSION_ID}")
        else:
            trans.status = "READY"
            trans.questions_answers = viva_payload
            trans.violation_logs = []
            await db.commit()
            print(f"Updated Viva Transcript for submission: {SUBMISSION_ID}")


if __name__ == "__main__":
    asyncio.run(seed_assessment_demo())
