# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Unit tests for Grounded Citation Verification and Batch Checkpoint Creation (T2-I-M2-04)."""

from app.modules.learning.section_extractor import IndexedParagraph
from app.modules.learning.service import LearningCheckpointService


def test_verify_and_resolve_citation_exact_match():
    """Exact substring match on claimed page and paragraph succeeds."""
    paragraphs = [
        IndexedParagraph(
            page=14,
            paragraph=2,
            text="Cơ chế bắt tay 3 bước (3-way handshake) gồm SYN, SYN-ACK và ACK.",
            word_count=14,
        )
    ]
    res = LearningCheckpointService._verify_and_resolve_citation(
        evidence_quote="Cơ chế bắt tay 3 bước (3-way handshake) gồm SYN, SYN-ACK và ACK.",
        claimed_page=14,
        claimed_para=2,
        section_paragraphs=paragraphs,
    )
    assert res is not None
    assert res[0] == 14
    assert res[1] == 2


def test_verify_and_resolve_citation_remaps_wrong_page():
    """If LLM misattributes page number but quote exists in another paragraph, remap to true page."""
    paragraphs = [
        IndexedParagraph(page=10, paragraph=1, text="Nội dung trang 10 không liên quan.", word_count=7),
        IndexedParagraph(
            page=12,
            paragraph=3,
            text="Tầng Trình diễn đảm nhận việc định dạng, mã hóa và nén dữ liệu.",
            word_count=14,
        ),
    ]
    res = LearningCheckpointService._verify_and_resolve_citation(
        evidence_quote="Tầng Trình diễn đảm nhận việc định dạng, mã hóa và nén dữ liệu.",
        claimed_page=10,
        claimed_para=1,
        section_paragraphs=paragraphs,
    )
    assert res is not None
    assert res[0] == 12
    assert res[1] == 3


def test_verify_and_resolve_citation_rejects_hallucination():
    """Fabricated quote not present in source paragraphs returns None (BR-RAG-01)."""
    paragraphs = [
        IndexedParagraph(
            page=5,
            paragraph=1,
            text="Giao thức HTTP hoạt động ở tầng ứng dụng.",
            word_count=9,
        )
    ]
    res = LearningCheckpointService._verify_and_resolve_citation(
        evidence_quote="Giao thức lượng tử truyền dữ liệu nhanh hơn ánh sáng.",
        claimed_page=5,
        claimed_para=1,
        section_paragraphs=paragraphs,
    )
    assert res is None
