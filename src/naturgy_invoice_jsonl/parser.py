from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from pypdf import PdfReader


@dataclass
class InvoiceData:
    source_file: str
    company: str | None = None
    invoice_number: str | None = None
    issue_date: str | None = None
    charge_date: str | None = None
    billing_period_start: str | None = None
    billing_period_end: str | None = None
    reference_number: str | None = None
    total_amount_eur: float | None = None
    electricity_total_eur: float | None = None
    vat_eur: float | None = None
    plan_name: str | None = None
    contract_number: str | None = None
    billed_days: int | None = None
    total_consumption_kwh: int | None = None
    energy_price_eur_per_kwh: float | None = None
    energy_amount_eur: float | None = None
    power_p1_kw: float | None = None
    power_p1_price_eur_per_kw_day: float | None = None
    power_p1_amount_eur: float | None = None
    power_p2_kw: float | None = None
    power_p2_price_eur_per_kw_day: float | None = None
    power_p2_amount_eur: float | None = None
    social_bonus_price_eur_per_day: float | None = None
    social_bonus_amount_eur: float | None = None
    subtotal_eur: float | None = None
    electricity_tax_rate: float | None = None
    electricity_tax_amount_eur: float | None = None
    meter_rental_price_eur_per_day: float | None = None
    meter_rental_amount_eur: float | None = None
    taxable_base_eur: float | None = None
    vat_rate: float | None = None
    customer_name: str | None = None
    customer_nif: str | None = None
    customer_number: str | None = None
    fiscal_address: str | None = None
    supply_address: str | None = None
    bank_entity: str | None = None
    bank_iban_masked: str | None = None
    direct_debit_mandate: str | None = None
    direct_debit_mandate_date: str | None = None
    meter_number: str | None = None
    readings: dict[str, Any] | None = None
    access_contract_number: str | None = None
    cups: str | None = None
    cnae: str | None = None
    tariff: str | None = None
    contracted_power_p1_kw: float | None = None
    contracted_power_p2_kw: float | None = None
    charge_segment: int | None = None
    access_charges_eur: float | None = None
    contract_end_date: str | None = None
    max_power_last_year_p1_kw: float | None = None
    max_power_last_year_p2_kw: float | None = None
    average_zip_consumption_kwh: float | None = None


def extract_text(pdf_path: str | Path) -> str:
    reader = PdfReader(str(pdf_path))
    chunks: list[str] = []
    for page in reader.pages:
        chunks.append(page.extract_text() or "")
    return "\n".join(chunks)


def normalize_spaces(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r" ?€", "€", text)
    return text.strip()


def parse_spanish_number(num: str | None) -> float | None:
    if not num:
        return None
    cleaned = num.replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_int_from_spanish(num: str | None) -> int | None:
    value = parse_spanish_number(num)
    return int(value) if value is not None else None


def search(pattern: str, text: str, flags: int = 0, group: int | str = 1) -> str | None:
    m = re.search(pattern, text, flags)
    if not m:
        return None
    return m.group(group).strip()


def parse_date_range(raw: str | None) -> tuple[str | None, str | None]:
    if not raw:
        return None, None
    m = re.search(r"(\d{2}\.\d{2}\.\d{4})\s+al\s+(\d{2}\.\d{2}\.\d{4})", raw)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def parse_readings(text: str) -> dict[str, Any]:
    readings: dict[str, Any] = {}
    for period in ["Punta", "Llano", "Valle"]:
        actual = search(rf"Lectura actual: {period} real \d{{2}}\.\d{{2}}\.\d{{2}} ([\d\.]+) kWh", text)
        previous = search(rf"Lectura anterior: {period} real \d{{2}}\.\d{{2}}\.\d{{2}} ([\d\.]+) kWh", text)
        consumption = search(rf"Consumo: {period} ([\d\.]+) kWh", text)
        readings[period.lower()] = {
            "actual_kwh": parse_spanish_number(actual),
            "previous_kwh": parse_spanish_number(previous),
            "consumption_kwh": parse_spanish_number(consumption),
        }
    return readings


def parse_invoice(text: str, source_file: str) -> InvoiceData:
    text = normalize_spaces(text)
    NUM = r"([\d\s\.,]+)"

    billing_period_raw = search(r"Electricidad: del (\d{2}\.\d{2}\.\d{4} al \d{2}\.\d{2}\.\d{4})", text)
    billing_start, billing_end = parse_date_range(billing_period_raw)

    data = InvoiceData(
        source_file=source_file,
        company=search(r"^(Naturgy Iberia, S\.A\. - Mercado Libre)", text, flags=re.M),
        invoice_number=search(r"Nº factura: ([A-Z0-9]+)", text),
        issue_date=search(r"Fecha de emisión: (\d{2}\.\d{2}\.\d{4})", text),
        charge_date=search(r"Fecha de cargo: (\d{2}\.\d{2}\.\d{4})", text),
        billing_period_start=billing_start,
        billing_period_end=billing_end,
        reference_number=search(r"Nº Referencia: (\d+)", text),
        total_amount_eur=parse_spanish_number(search(rf"Total a pagar {NUM}€", text)),
        electricity_total_eur=parse_spanish_number(search(rf"Total electricidad {NUM}€", text)),
        vat_eur=parse_spanish_number(search(r"Total IVA 21% [\d\s\.,]+€ 21 ?% ([\d\s\.,]+)€", text)),
        plan_name=search(r"Detalle de tu factura Concepto Cálculo Importe ([A-Za-zÁÉÍÓÚáéíóú ]+) Contrato:", text),
        contract_number=search(r"Contrato: (\d+)", text),
        billed_days=parse_int_from_spanish(search(r"Contrato: \d+ (\d+) días", text)),
        total_consumption_kwh=parse_int_from_spanish(search(rf"Consumo electricidad {NUM} kWh", text)),
        energy_price_eur_per_kwh=parse_spanish_number(search(rf"Consumo electricidad {NUM} kWh {NUM}€/kWh", text)),
        energy_amount_eur=parse_spanish_number(search(rf"Consumo electricidad {NUM} kWh {NUM}€/kWh {NUM}€", text, group=3)),
        power_p1_kw=parse_spanish_number(search(r"Término de potencia P1 \(([\d\.,]+) kW\)", text)),
        power_p1_price_eur_per_kw_day=parse_spanish_number(search(r"Término de potencia P1 \([\d\.,]+ kW\) \d+ días ([\d\.,]+)€/kW día", text)),
        power_p1_amount_eur=parse_spanish_number(search(rf"Término de potencia P1 \({NUM} kW\) \d+ días {NUM}€/kW día {NUM}€", text, group=3)),
        power_p2_kw=parse_spanish_number(search(r"Término de potencia P2 \(([\d\.,]+) kW\)", text)),
        power_p2_price_eur_per_kw_day=parse_spanish_number(search(r"Término de potencia P2 \([\d\.,]+ kW\) \d+ días ([\d\.,]+)€/kW día", text)),
        power_p2_amount_eur=parse_spanish_number(search(rf"Término de potencia P2 \({NUM} kW\) \d+ días {NUM}€/kW día {NUM}€", text, group=3)),
        social_bonus_price_eur_per_day=parse_spanish_number(search(rf"Financiación del Bono Social \d+ días {NUM}€/día", text)),
        social_bonus_amount_eur=parse_spanish_number(search(rf"Financiación del Bono Social \d+ días {NUM}€/día {NUM}€", text, group=2)),
        subtotal_eur=parse_spanish_number(search(rf"Subtotal {NUM}€", text)),
        electricity_tax_rate=parse_spanish_number(search(r"Impuesto electricidad [\d\s\.,]+€ ([\d\s\.,]+) [\d\s\.,]+€", text)),
        electricity_tax_amount_eur=parse_spanish_number(search(r"Impuesto electricidad [\d\s\.,]+€ [\d\s\.,]+? ([\d\s\.,]+)€", text)),
        meter_rental_price_eur_per_day=parse_spanish_number(search(rf"Alquiler de contador \d+ días {NUM}€/día", text)),
        meter_rental_amount_eur=parse_spanish_number(search(rf"Alquiler de contador \d+ días {NUM}€/día {NUM}€", text, group=2)),
        taxable_base_eur=parse_spanish_number(search(rf"Base imponible {NUM}€", text)),
        vat_rate=parse_spanish_number(search(r"Total IVA (\d+)%", text)),
        customer_name=search(r"Tus datos de facturación Nombre: ([A-ZÁÉÍÓÚÑ ]+?) NIF:", text),
        customer_nif=search(r"NIF: (ES - [A-Z0-9]+)", text),
        customer_number=search(r"Nº cliente: (\d+)", text),
        fiscal_address=search(r"Dirección fiscal: (.+?) Nº cliente:", text),
        supply_address=search(r"Dirección suministro: (.+?) Nº factura:", text),
        bank_entity=search(r"Entidad: (.+?) Datos bancarios:", text),
        bank_iban_masked=search(r"Datos bancarios: (IBAN [A-Z0-9X ]+?)(?: Esta factura|$)", text),
        direct_debit_mandate=search(r"mandato (\d+) de fecha", text),
        direct_debit_mandate_date=search(r"mandato \d+ de fecha (\d{2}\.\d{2}\.\d{4})", text),
        meter_number=search(r"Nº contador: (\d+)", text),
        readings=parse_readings(text),
        access_contract_number=search(r"Nº contrato de acceso .*?: (\d+)", text),
        cups=search(r"Código CUPS: ([A-Z0-9]+)", text),
        cnae=search(r"Nº de CNAE: (\d+)", text),
        tariff=search(r"Peaje de transporte y distribución: ([\d\.A-Z]+)", text),
        contracted_power_p1_kw=parse_spanish_number(search(r"Potencia contratada P1 ([\d\.,]+) kW", text)),
        contracted_power_p2_kw=parse_spanish_number(search(r"Potencia contratada P2 ([\d\.,]+) kW", text)),
        charge_segment=parse_int_from_spanish(search(r"Segmento de cargos: (\d+)", text)),
        access_charges_eur=parse_spanish_number(search(r"Cuantía de peajes y cargos: ([\d\.,]+)€", text)),
        contract_end_date=search(r"Fecha final del contrato: (\d{2}\.\d{2}\.\d{4})", text),
        max_power_last_year_p1_kw=parse_spanish_number(search(r"han sido ([\d\.,]+) kW en P1", text)),
        max_power_last_year_p2_kw=parse_spanish_number(search(r"y ([\d\.,]+) kW en P2", text)),
        average_zip_consumption_kwh=parse_spanish_number(search(r"según tu distribuidora: ([\d\.,]+) kWh", text)),
    )
    return data


def invoice_to_dict(invoice: InvoiceData) -> dict[str, Any]:
    return asdict(invoice)


def write_jsonl(record: dict[str, Any], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
