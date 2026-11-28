# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""1-Click question extraction service from PDF and DOCX documents (TV3)."""

import io
import re
from typing import List, Optional
from app.modules.examination.exceptions import QuestionExtractionFailedException
from app.modules.examination.schemas import (
    ExtractedQuestionDraft,
    ExtractionPreviewResponse,
    QuestionOptionSchema,
)


class QuestionExtractorService:
    """Parses text, DOCX and PDF documents into draft question structures."""

    QUESTION_HEADER_PATTERN = re.compile(
        r"^(?:câu|cau|question)\s*(\d+)[\s.:\-]+",
        re.IGNORECASE | re.MULTILINE,
    )
    OPTION_PATTERN = re.compile(
        r"^([*]?)([A-Da-d])[\s.):\-]+(.*)$",
        re.MULTILINE,
    )
    ANSWER_PATTERN = re.compile(
        r"(?:đáp án|dap an|answer|correct answer)[\s.:\-]+([A-Da-d])",
        re.IGNORECASE,
    )
    EXPLANATION_PATTERN = re.compile(
        r"(?:giải thích|giai thich|lời giải|loi giai|explanation)[\s.:\-]+(.*)",
        re.IGNORECASE,
    )

    def extract_from_text(self, text: str, filename: str = "document.txt") -> ExtractionPreviewResponse:
        """Parse raw text string into structured question drafts."""
        cleaned_text = text.replace("\r\n", "\n").replace("\r", "\n")
        blocks = self._split_into_question_blocks(cleaned_text)

        drafts: List[ExtractedQuestionDraft] = []
        for block in blocks:
            draft = self._parse_block(block)
            if draft:
                drafts.append(draft)

        if not drafts:
            raise QuestionExtractionFailedException("No valid questions detected in the provided content.")

        return ExtractionPreviewResponse(
            filename=filename,
            total_extracted=len(drafts),
            questions=drafts,
        )

    def extract_from_docx_bytes(self, content_bytes: bytes, filename: str = "exam.docx") -> ExtractionPreviewResponse:
        """Parse DOCX binary content using python-docx."""
        try:
            import docx
            doc = docx.Document(io.BytesIO(content_bytes))
            full_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            return self.extract_from_text(full_text, filename=filename)
        except Exception as ex:
            raise QuestionExtractionFailedException(f"Failed to parse DOCX file: {str(ex)}")

    def extract_from_pdf_bytes(self, content_bytes: bytes, filename: str = "exam.pdf") -> ExtractionPreviewResponse:
        """Parse PDF binary content using pypdf or PyMuPDF/fitz."""
        text = ""
        try:
            import fitz
            doc = fitz.open(stream=content_bytes, filetype="pdf")
            pages_text = [page.get_text() for page in doc]
            text = "\n".join(pages_text)
        except ImportError:
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(content_bytes))
                pages_text = [page.extract_text() or "" for page in reader.pages]
                text = "\n".join(pages_text)
            except Exception as ex:
                raise QuestionExtractionFailedException(f"Failed to read PDF pages: {str(ex)}")
        except Exception as ex:
            raise QuestionExtractionFailedException(f"Failed to read PDF with fitz: {str(ex)}")

        return self.extract_from_text(text, filename=filename)

    def _split_into_question_blocks(self, text: str) -> List[str]:
        """Split document text into individual question segments."""
        matches = list(self.QUESTION_HEADER_PATTERN.finditer(text))
        if not matches:
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            if lines:
                return ["\n".join(lines)]
            return []

        blocks = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            blocks.append(text[start:end].strip())
        return blocks

    def _parse_block(self, block: str) -> Optional[ExtractedQuestionDraft]:
        """Parse single question block into prompt, options, answer and explanation."""
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            return None

        prompt_lines = []
        options: List[QuestionOptionSchema] = []
        correct_key = ""
        explanation = None

        i = 0
        while i < len(lines):
            line = lines[i]

            ans_match = self.ANSWER_PATTERN.search(line)
            if ans_match:
                correct_key = ans_match.group(1).upper()
                i += 1
                continue

            exp_match = self.EXPLANATION_PATTERN.search(line)
            if exp_match:
                explanation = exp_match.group(1).strip()
                i += 1
                continue

            opt_match = self.OPTION_PATTERN.match(line)
            if opt_match:
                has_star = bool(opt_match.group(1))
                key = opt_match.group(2).upper()
                opt_text = opt_match.group(3).strip()
                is_correct = False
                if has_star:
                    is_correct = True
                    correct_key = key
                options.append(QuestionOptionSchema(key=key, text=opt_text, is_correct=is_correct))
                i += 1
                continue

            if not options:
                clean_line = self.QUESTION_HEADER_PATTERN.sub("", line).strip()
                prompt_lines.append(clean_line if clean_line else line)
            i += 1

        prompt = " ".join(prompt_lines).strip()
        if not prompt or len(options) < 2:
            return None

        if correct_key:
            for opt in options:
                if opt.key == correct_key:
                    opt.is_correct = True

        confidence = 1.0 if any(o.is_correct for o in options) else 0.5
        if not any(o.is_correct for o in options) and options:
            options[0].is_correct = True
            correct_key = options[0].key

        return ExtractedQuestionDraft(
            prompt=prompt,
            options=options,
            correct_key=correct_key or options[0].key,
            explanation=explanation,
            difficulty="medium",
            confidence_score=confidence,
        )
