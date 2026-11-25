# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Unit tests for Repomix Ingestion Client and fallback packer."""

import os
import tempfile
import pytest
from app.modules.assessment.ingestion.repomix_client import RepomixClient


@pytest.mark.asyncio
async def test_repomix_client_fallback_with_empty_or_missing_path():
    client = RepomixClient(base_url="http://invalid-repomix-host:9999")
    result = await client.pack_source_code(source_path="/non/existent/path")
    assert result["success"] is True
    assert result["source"] == "in_process_fallback"
    assert "<repository>" in result["packed_xml"]


@pytest.mark.asyncio
async def test_repomix_client_fallback_with_local_files():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create a sample python file
        py_file = os.path.join(tmp_dir, "solution.py")
        with open(py_file, "w", encoding="utf-8") as f:
            f.write("def solve(a, b):\n    return a + b\n")

        # Create ignored file
        ignored_dir = os.path.join(tmp_dir, "node_modules")
        os.makedirs(ignored_dir, exist_ok=True)
        with open(os.path.join(ignored_dir, "junk.js"), "w", encoding="utf-8") as f:
            f.write("// junk code")

        client = RepomixClient(base_url="http://invalid-repomix-host:9999")
        result = await client.pack_source_code(source_path=tmp_dir, max_tokens=1000)

        assert result["success"] is True
        assert result["file_count"] == 1
        assert "solution.py" in result["packed_xml"]
        assert "junk.js" not in result["packed_xml"]
        assert "def solve" in result["packed_xml"]


@pytest.mark.asyncio
async def test_repomix_client_git_reference_handling():
    client = RepomixClient(base_url="http://invalid-repomix-host:9999")
    result = await client.pack_source_code(git_url="https://github.com/example/demo.git")
    assert result["success"] is True
    assert "https://github.com/example/demo.git" in result["packed_xml"]


def test_repomix_trim_keeps_directory_and_most_active_files():
    raw_xml = (
        "<directory_structure>\nconfig.py\nservice.py\n</directory_structure>\n\n"
        "<files>\n"
        '<file path="config.py">' + ("x" * 600) + "</file>\n"
        '<file path="service.py">' + ("y" * 200) + "</file>\n"
        "</files>"
    )
    trimmed = RepomixClient._trim_xml_keeping_active_files(raw_xml, max_tokens=100)
    assert "<directory_structure>" in trimmed
    assert 'path="service.py"' in trimmed
    assert 'path="config.py"' not in trimmed
