# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Domain exceptions for Learning bounded context inheriting core ADLASException."""

from typing import Optional
from fastapi import status
from app.core.exceptions import ADLASException


class LearningModuleNotFoundException(ADLASException):
    """Module does not exist within the specified course."""

    def __init__(self, detail: str = "Không tìm thấy chương/bài học yêu cầu."):
        super().__init__(
            code="E-LEARN-NOT-FOUND",
            detail=detail,
            status_code=status.HTTP_404_NOT_FOUND,
        )


class LearningMaterialNotFoundException(ADLASException):
    """Learning material does not exist within the specified module."""

    def __init__(self, detail: str = "Không tìm thấy tài liệu học tập yêu cầu."):
        super().__init__(
            code="E-LEARN-NOT-FOUND",
            detail=detail,
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ModuleCircularDependencyException(ADLASException):
    """Circular prerequisite dependency detected among modules."""

    def __init__(self, detail: str = "Phát hiện điều kiện tiên quyết vòng tròn giữa các bài học."):
        super().__init__(
            code="E-LEARN-CIRCULAR",
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class MaterialQuotaExceededException(ADLASException):
    """Uploaded material file exceeds system global quota (Rule BR-STORAGE-02)."""

    def __init__(self, detail: str = "Tệp học liệu vượt quá dung lượng tối đa cho phép theo hạn ngạch hệ thống."):
        super().__init__(
            code="E-LEARN-QUOTA",
            detail=detail,
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )


class InvalidMaterialFormatException(ADLASException):
    """File extension or MIME type not supported for learning materials."""

    def __init__(self, detail: str = "Định dạng tệp học liệu không được hỗ trợ."):
        super().__init__(
            code="E-LEARN-FORMAT",
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class ModuleLockedException(ADLASException):
    """Student attempted to access locked module (prerequisite or unlock_at schedule)."""

    def __init__(self, detail: str = "Bài học đang tạm khóa do chưa hoàn thành bài tiên quyết hoặc chưa đến thời gian mở."):
        super().__init__(
            code="E-LEARN-LOCKED",
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class CheckpointNotFoundException(ADLASException):
    """Checkpoint does not exist within the specified material."""

    def __init__(self, detail: str = "Không tìm thấy điểm dừng kiểm tra yêu cầu."):
        super().__init__(
            code="E-CHK-NOT-FOUND",
            detail=detail,
            status_code=status.HTTP_404_NOT_FOUND,
        )


class CheckpointSpacingException(ADLASException):
    """Video checkpoints must be at least 5 seconds apart."""

    def __init__(self, detail: str = "Khoảng cách giữa hai điểm dừng video phải tối thiểu 5 giây."):
        super().__init__(
            code="E-CHK-SPACING",
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class UncompletedCheckpointsException(ADLASException):
    """Material has uncompleted blocking checkpoints preventing completion."""

    def __init__(self, detail: str = "Cần hoàn thành tất cả các mốc kiểm tra nhận thức bắt buộc trước khi kết thúc học liệu."):
        super().__init__(
            code="E-CHK-UNCOMPLETED",
            detail=detail,
            status_code=status.HTTP_409_CONFLICT,
        )


class NoTextLayerException(ADLASException):
    """Document is a scanned image or has no extractable text layer (E-RAG-01)."""

    def __init__(
        self,
        detail: str = (
            "Tài liệu này là bản scan hình ảnh hoặc không có lớp văn bản có thể đọc được. "
            "Hệ thống không thể bóc tách nội dung chương mục tự động. "
            "Vui lòng tải lên tệp tài liệu gốc có văn bản hoặc tự nhập câu hỏi thủ công."
        ),
    ):
        super().__init__(
            code="NO_TEXT_LAYER",
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class SectionTooShortException(ADLASException):
    """Selected section has fewer than 100 words (E-RAG-02)."""

    def __init__(
        self,
        detail: str = (
            "Mục được chọn quá ít nội dung thông tin (dưới 100 từ) để tạo câu hỏi có chất lượng sư phạm. "
            "Vui lòng chọn phân đoạn dài hơn hoặc gộp chung với mục kế bên."
        ),
    ):
        super().__init__(
            code="SECTION_TOO_SHORT",
            detail=detail,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
