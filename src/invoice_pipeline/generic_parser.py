from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import InvoiceRecord
from .utils import normalize_space, parse_spanish_number, to_iso_date


LABEL_PATTERNS: Dict[str, List[str]] = {
    "invoice_number": [r"N[ºo°]?\s*factura[:\s]+([^\n]+)", r"Invoice\s*(?:No|Number)[:\s]+([^\n]+)"],
    "reference_number": [r"N[ºo°]?\s*Referencia[:\s]+([^\n]+)", r"Referencia[:\s]+([^\n]+)"],
    "issue_date": [r"Fecha de emisi[oó]n[:\s]+(\d{2}[./-]\d{2}[./-]\d{2,4})", r"Invoice date[:\s]+(\d{2}[./-]\d{2}[./-]\d{2,4})"],
    "charge_date": [r"Fecha de cargo[:\s]+(\d{2}[./-]\d{2}[./-]\d{2,4})"],
    "total_amount": [r"Total a pagar\s*([\d.,]+)\s*€", r"Total due\s*([\d.,]+)"],
    "customer_number": [r"N[ºo°]?\s*cliente[:\s]+([^\n]+)"],
    "contract_number": [r"Contrato[:\s]+([0-9A-Z-]+)"],
    "iban_masked": [r"IBAN\s+([A-Z]{2}XX[^\n]+)", r"IBAN\s+([A-Z]{2}[A-Z0-9\sX]+)"],
}

SUPPLIER_MARKERS = [
    "naturgy",
    "iberdrola",
    "endesa",
    "repsol",
    "totalenergies",
    "holaluz",
    "edp",
    "cepsa",
    "vodafone",
    "movistar",
    "orange",
    "masmovil",
    "digi",
    "ayuntamiento",
]


def _search(patterns: List[str], text: str) -> Optional[str]:
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return normalize_space(m.group(1))
    return None


def infer_supplier_name(text: str) -> Optional[str]:
    low = text.lower()
    if "naturgy" in low:
        return "Naturgy Iberia, S.A."
    for marker in SUPPLIER_MARKERS:
        if marker in low:
            return marker.upper() if marker == "edp" else marker.title()
    first = next((line.strip() for line in text.splitlines() if line.strip()), None)
    return first[:120] if first else None


def extract_period(text: str) -> Tuple[Optional[str], Optional[str]]:
    m = re.search(r"del\s+(\d{2}[./-]\d{2}[./-]\d{2,4})\s+al\s+(\d{2}[./-]\d{2}[./-]\d{2,4})", text, re.IGNORECASE)
    if not m:
        return None, None
    return to_iso_date(m.group(1)), to_iso_date(m.group(2))


def extract_address_block(text: str, label: str) -> Optional[str]:
    m = re.search(label + r"[:\s]+(.+?)(?:\n\n|N[ºo°]?\s|C[oó]digo|Contrato|$)", text, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    block = normalize_space(m.group(1).replace("\n", " "))
    return re.sub(r"\s{2,}", " ", block)[:220]


def extract_inline_field(text: str, label: str, next_label: str | None = None) -> Optional[str]:
    if next_label:
        pattern = rf"{label}\s*:?\s*(.*?)\s+{next_label}"
    else:
        pattern = rf"{label}\s*:?\s*([^\n]+)"
    m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    return normalize_space(m.group(1).replace("\n", " "))


def extract_line_items(text: str) -> List[dict]:
    items: List[dict] = []
    known = [
        "Consumo electricidad",
        "Término de potencia P1",
        "Término de potencia P2",
        "Financiación del Bono Social",
        "Alquiler de contador",
    ]
    for marker in known:
        m = re.search(marker + r".*", text, re.IGNORECASE)
        if m:
            items.append({"name": marker, "raw_match": normalize_space(m.group(0))[:300]})
    return items


def _extract_float(text: str, pattern: str) -> Optional[float]:
    m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    return parse_spanish_number(m.group(1))


def _extract_rate_near_label(text: str, label: str, unit_pattern: str) -> Optional[float]:
    idx = text.lower().find(label.lower())
    if idx < 0:
        return None
    snippet = text[idx: idx + 260]
    m = re.search(unit_pattern, snippet, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    return parse_spanish_number(m.group(1))


def parse_generic_invoice(text: str, source_file: str, source_method: str, raw_text_path: Path | None = None, ocr_pdf_path: Path | None = None) -> InvoiceRecord:
    record = InvoiceRecord(source_file=source_file, source_method=source_method)
    record.supplier_name = infer_supplier_name(text)
    for field, patterns in LABEL_PATTERNS.items():
        value = _search(patterns, text)
        if value is None:
            continue
        if field.endswith("_date"):
            setattr(record, field, to_iso_date(value) or value)
        else:
            setattr(record, field, value)

    period_start, period_end = extract_period(text)
    record.period_start = period_start
    record.period_end = period_end
    record.utility_type = "electricity" if "electricidad" in text.lower() else None

    record.subtotal_amount = _extract_float(text, r"Subtotal\s*([\d.,]+)€")
    record.tax_amount = _extract_float(text, r"Total IVA\s*\d+%\s*[\d.,]+€\s*\d+%\s*([\d.,]+)€")
    record.total_amount = record.total_amount if isinstance(record.total_amount, float) else parse_spanish_number(str(record.total_amount)) if record.total_amount else None

    record.electricity_amount = _extract_float(text, r"Total electricidad\s*([\d.,]+)€")
    record.energy_price_eur_per_kwh = _extract_float(text, r"Consumo.*?electricidad.*?([\d.,]+)€/kWh")
    record.power_price_p1_eur_per_kw_day = _extract_float(text, r"potencia.*?P1.*?([\d.,]+)€/kW.*?día")
    record.power_price_p2_eur_per_kw_day = _extract_float(text, r"potencia.*?P2.*?([\d.,]+)€/kW.*?día")
    record.social_bonus_price_eur_per_day = _extract_rate_near_label(text, "Financiación", r"([\d.,]+)€/día")
    record.meter_rental_price_eur_per_day = _extract_rate_near_label(text, "Alquiler", r"([\d.,]+)€/día")
    record.electricity_tax_rate = _extract_float(text, r"Impuesto.*?electricidad.*?[\d.,]+€\s*([\d.,]+)\s*[\d.,]+€")
    record.vat_rate = _extract_float(text, r"Total IVA\s*(\d+)%")
    record.contracted_power_p1_kw = _extract_float(text, r"Potencia contratada P1\s*([\d.,]+)\s*kW")
    record.contracted_power_p2_kw = _extract_float(text, r"Potencia contratada P2\s*([\d.,]+)\s*kW")
    record.total_consumption_kwh = _extract_float(text, r"Total consumo\s*([\d.,]+)\s*kWh")
    record.consumption_punta_kwh = _extract_float(text, r"Consumo:\s*Punta\s*([\d.,]+)\s*kWh")
    record.consumption_llano_kwh = _extract_float(text, r"Consumo:\s*Llano\s*([\d.,]+)\s*kWh")
    record.consumption_valle_kwh = _extract_float(text, r"Consumo:\s*Valle\s*([\d.,]+)\s*kWh")

    m_days = re.search(r"Contrato:\s*[0-9A-Z-]+.*?(\d+)\s*d[ií]as", text, re.IGNORECASE | re.DOTALL)
    if m_days:
        record.billed_days = int(m_days.group(1))

    record.customer_name = extract_inline_field(text, r"Nombre", r"N[ºo°]? cliente")
    tax = extract_inline_field(text, r"NIF", r"Entidad")
    if tax:
        m = re.search(r"([A-Z0-9\- ]{6,})", tax)
        record.customer_tax_id = normalize_space(m.group(1)).replace("ES - ", "") if m else tax
    record.customer_number = extract_inline_field(text, r"N[ºo°]? cliente") or record.customer_number
    record.contract_number = _search([r"Contrato:\s*([0-9A-Z-]+)"], text)
    m_access = re.search(r"N[ºo°]? contrato de acceso\s+([0-9]+)", text, re.IGNORECASE)
    if m_access:
        record.access_contract_number = m_access.group(1)
    m_cups = re.search(r"C[oó]digo CUPS:\s*([A-Z0-9]+)", text, re.IGNORECASE)
    if m_cups:
        record.cups = m_cups.group(1)
    compact = re.sub(r'\s+', ' ', text)
    m_tariff = re.search(r"Peaje de transporte y\s+distribuci[oó]n:\s*([0-9A-Z.]+)", compact, re.IGNORECASE)
    if m_tariff:
        record.tariff = m_tariff.group(1)
    m_meter = re.search(r"N[ºo°]? contador:\s*.*?\n\s*([0-9]{4,})", text, re.IGNORECASE)
    if m_meter:
        record.meter_number = m_meter.group(1)

    record.supply_address = extract_address_block(text, r"Direcci[oó]n suministro")
    m_fiscal = re.search(r"Direcci[oó]n fiscal:\s*(.*?)\s*Datos bancarios:", text, re.IGNORECASE | re.DOTALL)
    if m_fiscal:
        record.fiscal_address = normalize_space(m_fiscal.group(1).replace("\n", " "))
    else:
        record.fiscal_address = extract_address_block(text, r"Direcci[oó]n fiscal")
    record.line_items = extract_line_items(text)
    record.raw_text_path = str(raw_text_path) if raw_text_path else None
    record.ocr_pdf_path = str(ocr_pdf_path) if ocr_pdf_path else None
    return record
