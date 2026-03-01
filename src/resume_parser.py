"""Parse resumes from .docx, .pdf, and .txt files."""

from __future__ import annotations

import io
from pathlib import Path

from docx import Document
from PyPDF2 import PdfReader


def parse_resume(uploaded_file) -> str:
    """Extract text from an uploaded resume file.

    Args:
        uploaded_file: A Streamlit UploadedFile object.

    Returns:
        Extracted plain text content.

    Raises:
        ValueError: If the file type is not supported.
    """
    name = uploaded_file.name.lower()
    data = uploaded_file.read()
    uploaded_file.seek(0)

    if name.endswith(".txt"):
        return data.decode("utf-8", errors="replace")
    elif name.endswith(".pdf"):
        return _parse_pdf(data)
    elif name.endswith(".docx"):
        return _parse_docx(data)
    else:
        raise ValueError(f"Unsupported file type: {Path(name).suffix}")


def _parse_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()


def _parse_docx(data: bytes) -> str:
    doc = Document(io.BytesIO(data))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs).strip()
