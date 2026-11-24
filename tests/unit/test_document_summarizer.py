# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Unit tests for Document Summarizer and Recursive Map-Reduce engine."""

import os
import tempfile
from app.modules.assessment.ingestion.document_summarizer import DocumentSummarizer


def test_sliding_window_chunking_short_text():
    summarizer = DocumentSummarizer(window_size_words=100, overlap_words=20)
    text = "Đây là một đoạn văn ngắn phục vụ kiểm thử phân mảnh."
    chunks = summarizer.chunk_text_sliding_window(text)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_sliding_window_chunking_with_overlap():
    summarizer = DocumentSummarizer(window_size_words=20, overlap_words=5)
    words = [f"từ_{i}" for i in range(50)]
    text = ". ".join(words) + "."
    chunks = summarizer.chunk_text_sliding_window(text)
    assert len(chunks) >= 2


def test_summarize_chunk_extractive():
    summarizer = DocumentSummarizer()
    chunk = (
        "Nghiên cứu này phân tích hiệu năng của thuật toán. "
        "Dữ liệu được thu thập từ 1000 sinh viên. "
        "Kết quả thực nghiệm chứng minh giải pháp đề xuất đạt độ chính xác cao. "
        "Kết luận bài báo mở ra hướng đi mới."
    )
    summary = summarizer.summarize_chunk(chunk, max_words=30)
    assert len(summary.split()) <= 30
    assert "Nghiên cứu" in summary


def test_recursive_map_reduce_long_document():
    summarizer = DocumentSummarizer(window_size_words=50, overlap_words=10)
    paragraphs = []
    for i in range(15):
        paragraphs.append(
            f"Đoạn văn số {i}: Mục tiêu nghiên cứu nhằm khảo sát phương pháp tối ưu hóa. "
            "Kết quả kiểm thử cho thấy giải pháp đạt hiệu năng vượt trội so với giải thuật truyền thống. "
            "Kết luận bài báo khẳng định tính khả thi của mô hình."
        )
    full_text = "\n\n".join(paragraphs)
    res = summarizer.recursive_map_reduce(full_text)

    assert "executive_summary" in res
    assert res["total_chunks"] > 1
    assert res["digest_word_count"] <= 400
    assert len(res["executive_summary"].split()) <= 400


def test_extract_text_from_txt_file():
    summarizer = DocumentSummarizer()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Nội dung tệp kiểm thử bóc tách văn bản.")
        temp_path = f.name

    try:
        extracted = summarizer.extract_text_from_file(temp_path)
        assert "Nội dung tệp kiểm thử" in extracted
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_recursive_map_reduce_empty_text_has_word_counts():
    summarizer = DocumentSummarizer()
    res = summarizer.recursive_map_reduce("   ")
    assert res["total_chunks"] == 0
    assert res["original_word_count"] == 0
    assert res["digest_word_count"] == 0
    assert "executive_summary" in res
