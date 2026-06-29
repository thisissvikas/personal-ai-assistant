import os
from pathlib import Path

from langchain_core.tools import StructuredTool

from .registry import register

_MAX_CHARS = 12_000


def _read_document(path: str, max_chars: int = _MAX_CHARS) -> str:
    """Read a local file and return its text content.

    Supports PDF (via pypdf), Markdown, plain text, and any UTF-8 or Latin-1
    encoded text file. Long documents are truncated at ``max_chars`` with a
    note showing how many characters were omitted.
    """
    resolved_path = Path(os.path.expanduser(path))
    if not resolved_path.exists():
        return f"File not found: {path}"
    if not resolved_path.is_file():
        return f"Path is not a file: {path}"

    file_extension = resolved_path.suffix.lower()

    if file_extension == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            return "pypdf package not installed. Run: uv sync"
        pdf_reader = PdfReader(str(resolved_path))
        text = "\n\n".join(page.extract_text() or "" for page in pdf_reader.pages)
    else:
        try:
            text = resolved_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = resolved_path.read_text(encoding="latin-1")

    text = text.strip()
    if not text:
        return f"File is empty or could not extract text: {path}"

    if len(text) > max_chars:
        omitted_chars = len(text) - max_chars
        text = text[:max_chars] + f"\n\n[… truncated — {omitted_chars} more characters not shown]"

    return f"Contents of {resolved_path.name}:\n\n{text}"


register(
    StructuredTool.from_function(
        func=_read_document,
        name="read_document",
        description=(
            "Read the contents of a local file (PDF, markdown, or plain text) so you can "
            "answer questions about it. Supports .pdf, .md, .txt, and similar text formats."
        ),
    )
)
