"""Extract searchable text from raster images via optional OCR (Pillow + pytesseract)."""

from __future__ import annotations

from pathlib import Path


def extract_image_plain_text(path: Path | str) -> str:
    """Run OCR when Pillow + pytesseract are installed (and Tesseract OCR engine is on PATH)."""
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(str(resolved))

    try:
        from PIL import Image
    except ImportError as exc:
        raise ValueError(
            "Image OCR requires optional dependencies. Install with: "
            "``uv sync --extra image`` or ``pip install pillow pytesseract`` "
            "(Tesseract OCR must also be installed on the host)."
        ) from exc

    try:
        import pytesseract
    except ImportError as exc:
        raise ValueError(
            "Image OCR requires pytesseract. Install with ``uv sync --extra image`` and ensure the ``tesseract`` binary is discoverable via PATH."
        ) from exc

    with Image.open(resolved) as img:
        if img.mode not in {"RGB", "L"}:
            img = img.convert("RGB")

        txt = pytesseract.image_to_string(img, lang="eng+chi_sim")

    cleaned = txt.replace("\x00", "").strip()
    if not cleaned:
        raise ValueError(f"No OCR text produced for image: {resolved}")
    return cleaned


__all__ = ["extract_image_plain_text"]
