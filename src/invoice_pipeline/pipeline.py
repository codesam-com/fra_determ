from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import List

from .generic_parser import parse_generic_invoice
from .reviewer import ai_like_review, score_record, validate_record
from .template_parser import parse_with_templates
from .text_extraction import extract_text_with_fallback
from .utils import append_jsonl


def merge_template_data(record, template_data: dict) -> None:
    mapping = {
        "issuer": "supplier_name",
        "invoice_number": "invoice_number",
        "date": "issue_date",
        "amount": "total_amount",
        "currency": "currency",
        "desc": None,
    }
    for src, dst in mapping.items():
        if dst and template_data.get(src) and not getattr(record, dst):
            setattr(record, dst, template_data[src])


def process_pdf(pdf_path: Path, repo_root: Path) -> dict:
    work_dir = repo_root / ".work"
    work_dir.mkdir(parents=True, exist_ok=True)
    text, source_method, ocr_pdf = extract_text_with_fallback(pdf_path, work_dir)

    raw_text_dir = repo_root / "output" / "raw_text"
    raw_text_dir.mkdir(parents=True, exist_ok=True)
    raw_text_path = raw_text_dir / f"{pdf_path.stem}.txt"
    raw_text_path.write_text(text, encoding="utf-8")

    record = parse_generic_invoice(
        text,
        source_file=pdf_path.name,
        source_method=source_method,
        raw_text_path=raw_text_path,
        ocr_pdf_path=ocr_pdf,
    )

    template_data = parse_with_templates(pdf_path, repo_root / "templates")
    if template_data:
        merge_template_data(record, template_data)

    record.validation_errors = validate_record(record)
    record.confidence = score_record(record)
    record.needs_review = record.confidence < 0.70 or bool(record.validation_errors)

    if record.needs_review:
        record = ai_like_review(record, text)

    return record.to_dict()


def move_source(pdf_path: Path, repo_root: Path, ok: bool) -> Path:
    target_dir = repo_root / ("processed" if ok else "failed")
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / pdf_path.name
    if target.exists():
        target = target_dir / f"{pdf_path.stem}-{pdf_path.stat().st_mtime_ns}{pdf_path.suffix}"
    shutil.move(str(pdf_path), str(target))
    return target


def run(repo_root: Path) -> List[dict]:
    inbox = repo_root / "inbox"
    output_jsonl = repo_root / "output" / "invoices.jsonl"
    rows: List[dict] = []
    for pdf_path in sorted(inbox.glob("*.pdf")):
        row = process_pdf(pdf_path, repo_root)
        rows.append(row)
        ok = not row.get("needs_review", False)
        move_source(pdf_path, repo_root, ok=ok)
    if rows:
        append_jsonl(output_jsonl, rows)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Process invoice PDFs from inbox/ into output/invoices.jsonl")
    parser.add_argument("--repo-root", default=".", help="Path to the repository root")
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    rows = run(repo_root)
    print(json.dumps({"processed": len(rows), "files": [r["source_file"] for r in rows]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
