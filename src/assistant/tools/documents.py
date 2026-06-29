import os
from pathlib import Path

from langchain_core.tools import StructuredTool

from .registry import register

_MAX_CHARS = 12_000


def _read_document(path: str, max_chars: int = _MAX_CHARS) -> str:
    resolved = Path(os.path.expanduser(path))
    if not resolved.exists():
        return f"File not found: {path}"
    if not resolved.is_file():
        return f"Path is not a file: {path}"

    suffix = resolved.suffix.lower()

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            return "pypdf package not installed. Run: pip install pypdf"
        reader = PdfReader(str(resolved))
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        try:
            text = resolved.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = resolved.read_text(encoding="latin-1")

    text = text.strip()
    if not text:
        return f"File is empty or could not extract text: {path}"

    if len(text) > max_chars:
        text = (
            text[:max_chars]
            + f"\n\n[… truncated — {len(text) - max_chars} more characters not shown]"
        )

    return f"Contents of {resolved.name}:\n\n{text}"


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
