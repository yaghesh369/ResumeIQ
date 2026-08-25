from pathlib import Path

# Extension -> (mime or None, human label)
ALLOWED = {
    "pdf": ("application/pdf", "PDF"),
    "txt": ("text/plain", "TXT"),
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "DOCX"),
    "png": ("image/png", "PNG image"),
    "jpg": ("image/jpeg", "JPEG image"),
    "jpeg": ("image/jpeg", "JPEG image"),
    "webp": ("image/webp", "WebP image"),
    "bmp": ("image/bmp", "BMP image"),
}

MAX_SIZE_MB = 10


def validate_file(file):
    """Validate uploaded file type and size. Returns (ok, message)."""
    if file is None:
        return False, "No file uploaded"

    name = getattr(file, "name", "") or ""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""

    # Trust extension first (browsers send inconsistent image mimes)
    if ext not in ALLOWED:
        if getattr(file, "type", None) in [m for m, _ in ALLOWED.values()]:
            return True, ""
        return False, (
            f"Unsupported file format: .{ext or 'unknown'}. "
            "Please upload PDF, TXT, DOCX, PNG or JPG."
        )

    size = getattr(file, "size", None)
    if size is not None and size > MAX_SIZE_MB * 1024 * 1024:
        return False, f"File too large ({MAX_SIZE_MB} MB max)."

    return True, ""


def validate_text(text: str) -> tuple:
    """Validate that text content is not empty/too short."""
    if not text or not text.strip():
        return False, "No text content found. The document may be image-based or empty."
    if len(text.strip()) < 50:
        return False, "Text too short. Please ensure the document contains readable content."
    return True, ""
