# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Unit tests for SectionExtractor (T2-I-M2-04): PDF/PPTX extraction, scan detection (E-RAG-01)."""

import os
import tempfile
import pytest

from app.modules.learning.exceptions import (
    InvalidMaterialFormatException,
    NoTextLayerException,
)
from app.modules.learning.section_extractor import SectionExtractor


def test_extract_pptx_success():
    """Verify PPTX slides are extracted with titles, indexed paragraphs, and word counts."""
    from pptx import Presentation

    prs = Presentation()
    slide1 = prs.slides.add_slide(prs.slide_layouts[1])
    slide1.shapes.title.text = "Chương 1: Giới thiệu"
    slide1.placeholders[1].text = "Đây là nội dung giới thiệu về mô hình mạng máy tính hiện đại và các giao thức."

    slide2 = prs.slides.add_slide(prs.slide_layouts[1])
    slide2.shapes.title.text = "Chương 2: Giao thức TCP"
    slide2.placeholders[1].text = "TCP sử dụng cơ chế bắt tay 3 bước để thiết lập kết nối tin cậy giữa hai máy."

    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        prs.save(tmp_path)
        extractor = SectionExtractor()
        doc = extractor.extract_document(tmp_path)
        assert doc.total_pages == 2
        assert doc.page_titles[1] == "Chương 1: Giới thiệu"
        assert doc.page_titles[2] == "Chương 2: Giao thức TCP"
        assert len(doc.paragraphs) >= 2
        assert sum(doc.page_word_counts.values()) > 15
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_extract_pdf_scan_raises_no_text_layer():
    """Verify PDF without text layer triggers E-RAG-01 (NoTextLayerException)."""
    import fitz

    pdf = fitz.open()
    pdf.new_page()
    pdf.new_page()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        pdf.save(tmp_path)
        pdf.close()
        extractor = SectionExtractor()
        with pytest.raises(NoTextLayerException) as exc_info:
            extractor.extract_document(tmp_path)
        assert exc_info.value.status_code == 422
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_extract_legacy_ppt_rejected():
    """Verify legacy binary .ppt files raise InvalidMaterialFormatException."""
    with tempfile.NamedTemporaryFile(suffix=".ppt", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        extractor = SectionExtractor()
        with pytest.raises(InvalidMaterialFormatException):
            extractor.extract_document(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
