from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Tuple

import fitz


def extract_native_text(pdf_path: Path) -> str:
    doc = fitz.open(pdf_path)
    try:
        pages = [page.get_text("text", sort=True) for page in doc]
    finally:
        doc.close()
    return "\n\n".join(pages).strip()


def run_ocrmypdf(pdf_path: Path, out_dir: Path, languages: str = "spa+eng") -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ocr_pdf = out_dir / f"{pdf_path.stem}.ocr.pdf"
    cmd = [
        "ocrmypdf",
        "--force-ocr",
        "--skip-big",
        "50",
        "--rotate-pages",
        "--deskew",
        "--clean",
        "-l",
        languages,
        str(pdf_path),
        str(ocr_pdf),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return ocr_pdf


def extract_text_with_fallback(pdf_path: Path, work_dir: Path) -> Tuple[str, str, Path | None]:
    native_text = extract_native_text(pdf_path)
    if len(native_text) >= 400:
        return native_text, "native_text", None

    try:
        ocr_pdf = run_ocrmypdf(pdf_path, work_dir / "ocr")
        ocr_text = extract_native_text(ocr_pdf)
        if ocr_text:
            return ocr_text, "ocr", ocr_pdf
    except Exception:
        pass

    return native_text, "native_text_low_text", None
