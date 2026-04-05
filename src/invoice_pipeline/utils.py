from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional


EURO_NUMBER_RE = re.compile(r"(\d{1,3}(?:\.\d{3})*,\d+|\d+,\d+|\d+(?:\.\d+)?)")


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_spanish_number(value: str) -> Optional[float]:
    if value is None:
        return None
    value = value.strip().replace("€", "").replace(" ", "")
    if not value:
        return None
    value = value.replace(".", "").replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return None


def find_first_number(text: str) -> Optional[float]:
    m = EURO_NUMBER_RE.search(text)
    return parse_spanish_number(m.group(1)) if m else None


def to_iso_date(value: str) -> Optional[str]:
    if not value:
        return None
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%d.%m.%y", "%d/%m/%y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def append_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
