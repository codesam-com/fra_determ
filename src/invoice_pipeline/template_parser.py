from __future__ import annotations

from pathlib import Path
from typing import Optional

from invoice2data import extract_data
from invoice2data.extract.loader import read_templates


def parse_with_templates(pdf_path: Path, templates_dir: Path) -> Optional[dict]:
    templates = read_templates(str(templates_dir))
    return extract_data(str(pdf_path), templates=templates) or None
