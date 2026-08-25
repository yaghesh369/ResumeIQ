from ..utils.text_cleaner import clean_text, extract_sections
from .resume_parser import (
    _pdf_bytes_to_text,
    _docx_bytes_to_text,
    _image_bytes_to_text,
    IMAGE_MIMES,
)


def parse_job_description(text) -> dict:
    """Parse a job description and extract structured information."""
    if not text or not text.strip():
        raise ValueError("Job description is empty. Please paste or upload one.")

    cleaned = clean_text(text)
    sections = extract_sections(cleaned)

    return {
        "raw_text": text,
        "clean_text": cleaned,
        "sections": sections,
    }


def parse_jd_upload(uploaded_file) -> dict:
    """Route an uploaded JD file by extension (pdf/txt/docx/images)."""
    name = (getattr(uploaded_file, "name", "") or "").lower()
    data = uploaded_file.read()

    ext = name.rsplit(".", 1)[-1] if "." in name else ""

    if ext == "pdf":
        raw = _pdf_bytes_to_text(data)
    elif ext == "txt":
        try:
            raw = data.decode("utf-8")
        except UnicodeDecodeError:
            raw = data.decode("latin-1", errors="ignore")
    elif ext == "docx":
        raw = _docx_bytes_to_text(data)
    elif ext in IMAGE_MIMES:
        from ..ai.gemini_client import GEMINI_API_KEY

        if not GEMINI_API_KEY:
            raise ValueError("Image JD parsing requires GEMINI_API_KEY — paste the text instead.")
        raw = _image_bytes_to_text(data, ext)
    else:
        if data[:5] == b"%PDF-":
            raw = _pdf_bytes_to_text(data)
        else:
            raise ValueError(
                "Unsupported job description format. Please upload a PDF, TXT, or DOCX file."
            )

    return parse_job_description(raw)


# Backwards-compatible alias
parse_job_description_upload = parse_jd_upload
