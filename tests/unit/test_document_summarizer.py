# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Unit tests for clean document extraction, large-document paragraph splitting, and offline excerpt."""

import os
import tempfile
from app.modules.assessment.ingestion.document_summarizer import DocumentSummarizer


def test_extract_text_from_txt_file():
    extractor = DocumentSummarizer()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Nội dung tệp kiểm thử bóc tách văn bản.\n\nĐoạn thứ hai trình bày phương pháp.")
        temp_path = f.name

    try:
        extracted = extractor.extract_text_from_file(temp_path)
        assert "Nội dung tệp kiểm thử" in extracted
        assert "Đoạn thứ hai" in extracted
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_split_large_text_by_paragraphs_preserves_boundaries():
    extractor = DocumentSummarizer()
    paragraphs = [f"Đoạn văn số {i} trình bày nội dung chi tiết về thí nghiệm và kết quả đánh giá." for i in range(40)]
    full_text = "\n\n".join(paragraphs)

    chunks = extractor.split_large_text_by_paragraphs(full_text, max_words=120, overlap_paragraphs=1)
    assert len(chunks) > 1
    for c in chunks:
        assert c.endswith(".")


def test_build_offline_excerpt_empty_and_long():
    extractor = DocumentSummarizer()
    assert "không có nội dung" in extractor.build_offline_excerpt("   ")

    long_text = " ".join([f"word{i}" for i in range(1000)])
    excerpt = extractor.build_offline_excerpt(long_text, max_words=100)
    assert "[...]" in excerpt
    assert "word0" in excerpt
    assert "word999" in excerpt
