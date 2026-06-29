"""Tests for the document-reading tool."""

from unittest.mock import MagicMock, patch


def _get_read_document():
    import sys

    for k in list(sys.modules):
        if "assistant.tools" in k:
            del sys.modules[k]
    from assistant.tools.documents import _read_document

    return _read_document


def test_missing_file_returns_not_found():
    read_document = _get_read_document()
    result = read_document("/nonexistent/path/to/file.txt")
    assert "not found" in result.lower()


def test_reads_plain_text_file(tmp_path):
    read_document = _get_read_document()
    f = tmp_path / "hello.txt"
    f.write_text("Hello, world!\nLine two.")

    result = read_document(str(f))
    assert "Hello, world!" in result
    assert "Line two." in result


def test_reads_markdown_file(tmp_path):
    read_document = _get_read_document()
    f = tmp_path / "notes.md"
    f.write_text("# Heading\n\nSome content here.")

    result = read_document(str(f))
    assert "Heading" in result
    assert "Some content here." in result


def test_truncation_applied(tmp_path):
    read_document = _get_read_document()
    f = tmp_path / "big.txt"
    f.write_text("x" * 5000)

    result = read_document(str(f), max_chars=100)
    assert "truncated" in result.lower()
    assert len(result) < 5000


def test_directory_path_returns_error(tmp_path):
    read_document = _get_read_document()
    result = read_document(str(tmp_path))
    assert "not a file" in result.lower()


def test_empty_file_returns_empty_message(tmp_path):
    read_document = _get_read_document()
    f = tmp_path / "empty.txt"
    f.write_text("")

    result = read_document(str(f))
    assert "empty" in result.lower() or "could not extract" in result.lower()


def test_reads_latin1_encoded_file(tmp_path):
    read_document = _get_read_document()
    f = tmp_path / "latin1.txt"
    f.write_bytes(b"Hello \xe9 world")  # \xe9 is valid latin-1 but not utf-8

    result = read_document(str(f))
    assert "Hello" in result


def test_reads_pdf_file(tmp_path):
    read_document = _get_read_document()
    f = tmp_path / "report.pdf"
    f.write_bytes(b"%PDF-1.4 fake")

    mock_page = MagicMock()
    mock_page.extract_text.return_value = "PDF page content"
    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]

    with patch("pypdf.PdfReader", return_value=mock_reader):
        result = read_document(str(f))

    assert "PDF page content" in result
