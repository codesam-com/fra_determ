from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class InvoiceRecord:
    source_file: str
    source_method: str
    supplier_name: Optional[str] = None
    invoice_number: Optional[str] = None
    reference_number: Optional[str] = None
    issue_date: Optional[str] = None
    charge_date: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    currency: str = "EUR"
    subtotal_amount: Optional[float] = None
    tax_amount: Optional[float] = None
    total_amount: Optional[float] = None
    electricity_amount: Optional[float] = None
    energy_price_eur_per_kwh: Optional[float] = None
    power_price_p1_eur_per_kw_day: Optional[float] = None
    power_price_p2_eur_per_kw_day: Optional[float] = None
    social_bonus_price_eur_per_day: Optional[float] = None
    meter_rental_price_eur_per_day: Optional[float] = None
    electricity_tax_rate: Optional[float] = None
    vat_rate: Optional[float] = None
    billed_days: Optional[int] = None
    contracted_power_p1_kw: Optional[float] = None
    contracted_power_p2_kw: Optional[float] = None
    total_consumption_kwh: Optional[float] = None
    consumption_punta_kwh: Optional[float] = None
    consumption_llano_kwh: Optional[float] = None
    consumption_valle_kwh: Optional[float] = None
    customer_name: Optional[str] = None
    customer_tax_id: Optional[str] = None
    customer_number: Optional[str] = None
    contract_number: Optional[str] = None
    access_contract_number: Optional[str] = None
    cups: Optional[str] = None
    tariff: Optional[str] = None
    meter_number: Optional[str] = None
    supply_address: Optional[str] = None
    fiscal_address: Optional[str] = None
    iban_masked: Optional[str] = None
    utility_type: Optional[str] = None
    line_items: List[Dict[str, Any]] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    confidence: float = 0.0
    needs_review: bool = False
    raw_text_path: Optional[str] = None
    ocr_pdf_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
