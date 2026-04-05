from __future__ import annotations

from typing import List

from .models import InvoiceRecord
from .utils import normalize_space


CRITICAL_FIELDS = [
    "supplier_name",
    "invoice_number",
    "issue_date",
    "total_amount",
]


def validate_record(record: InvoiceRecord) -> List[str]:
    errors: List[str] = []
    if record.total_amount is None:
        errors.append("missing_total")
    if record.issue_date is None:
        errors.append("missing_issue_date")
    if record.invoice_number is None:
        errors.append("missing_invoice_number")

    total = record.total_amount
    if total is not None:
        if record.electricity_amount is not None and record.tax_amount is not None:
            expected = round(record.electricity_amount + record.tax_amount, 2)
            if abs(expected - total) > 0.06:
                errors.append(f"electricity_plus_vat_mismatch:{expected}!={total}")
        elif record.subtotal_amount is not None and record.tax_amount is not None:
            expected = round(record.subtotal_amount + record.tax_amount, 2)
            if abs(expected - total) > 0.06:
                errors.append(f"subtotal_plus_tax_mismatch:{expected}!={total}")

    if record.total_consumption_kwh is not None:
        parts = [x for x in [record.consumption_punta_kwh, record.consumption_llano_kwh, record.consumption_valle_kwh] if x is not None]
        if parts and abs(sum(parts) - record.total_consumption_kwh) > 1.0:
            errors.append("consumption_breakdown_mismatch")
    return errors


def score_record(record: InvoiceRecord) -> float:
    score = 0.0
    for field in CRITICAL_FIELDS:
        if getattr(record, field):
            score += 0.2
    for field in [
        "subtotal_amount",
        "tax_amount",
        "customer_name",
        "customer_tax_id",
        "contract_number",
        "cups",
        "total_consumption_kwh",
    ]:
        if getattr(record, field) not in (None, "", []):
            score += 0.025
    if not record.validation_errors:
        score += 0.125
    return min(score, 0.99)


def ai_like_review(record: InvoiceRecord, raw_text: str) -> InvoiceRecord:
    """A lightweight local correction pass.

    It does not call any external model or paid API. It only applies a second,
    context-aware review over OCR text to repair common extraction misses.
    """
    lines = [normalize_space(x) for x in raw_text.splitlines() if normalize_space(x)]
    joined = "\n".join(lines)

    if not record.total_amount:
        for marker in ["Total a pagar", "Importe total", "Total factura", "Total due"]:
            idx = joined.lower().find(marker.lower())
            if idx >= 0:
                snippet = joined[idx: idx + 120]
                from .utils import find_first_number
                number = find_first_number(snippet)
                if number is not None:
                    record.total_amount = number
                    break

    if not record.supplier_name:
        for line in lines[:12]:
            low = line.lower()
            if any(k in low for k in ["s.a", "s.l", "iberdrola", "naturgy", "endesa", "repsol", "vodafone", "orange"]):
                record.supplier_name = line[:120]
                break

    if not record.invoice_number:
        import re
        for line in lines:
            if re.search(r"factura", line, re.IGNORECASE):
                m = re.search(r"([A-Z]{1,4}\d{6,})", line)
                if m:
                    record.invoice_number = m.group(1)
                    break

    if not record.customer_name:
        for i, line in enumerate(lines):
            if line.lower().startswith("nombre:"):
                record.customer_name = line.split(":", 1)[1].strip()
                break
            if i > 0 and line.isupper() and len(line.split()) >= 2 and len(line) < 80:
                record.customer_name = line
                break

    record.validation_errors = validate_record(record)
    record.confidence = score_record(record)
    record.needs_review = record.confidence < 0.70 or bool(record.validation_errors)
    return record
