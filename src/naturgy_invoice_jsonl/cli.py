from __future__ import annotations

import argparse
from pathlib import Path

from .parser import extract_text, invoice_to_dict, parse_invoice, write_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Extrae datos de facturas PDF de Naturgy y los guarda en JSONL.")
    parser.add_argument("pdf", nargs="+", help="Ruta(s) a PDF(s) de factura")
    parser.add_argument("-o", "--output", default="output/invoices.jsonl", help="Ruta del archivo JSONL de salida")
    args = parser.parse_args()

    for pdf in args.pdf:
        pdf_path = Path(pdf)
        text = extract_text(pdf_path)
        invoice = parse_invoice(text, source_file=pdf_path.name)
        write_jsonl(invoice_to_dict(invoice), args.output)
        print(f"Procesada: {pdf_path} -> {args.output}")


if __name__ == "__main__":
    main()
