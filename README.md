# naturgy-invoice-jsonl

Repo mínimo para extraer datos de una factura PDF de Naturgy y guardarlos en un archivo `jsonl`.

## Qué hace

- Lee uno o varios PDFs
- Extrae texto con `pypdf`
- Usa expresiones regulares para localizar los campos principales
- Guarda **un JSON por línea** en `output/invoices.jsonl`

## Estructura

```text
naturgy-invoice-jsonl/
├── README.md
├── requirements.txt
├── extract_invoice.py
└── src/
    └── naturgy_invoice_jsonl/
        ├── __init__.py
        ├── cli.py
        └── parser.py
```

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate  # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Uso

### Un PDF

```bash
python extract_invoice.py /ruta/a/factura.pdf
```

### Varios PDFs

```bash
python extract_invoice.py factura1.pdf factura2.pdf factura3.pdf
```

### Elegir salida

```bash
python extract_invoice.py factura.pdf -o data/facturas.jsonl
```

## Ejemplo de salida

```json
{"source_file": "Factura_FE25321494893037.pdf", "invoice_number": "FE25321494893037", "total_amount_eur": 100.91, "energy_price_eur_per_kwh": 0.142865}
```

## Nota

Este parser está pensado para el formato de factura de Naturgy que me pasaste. Si cambian mucho el diseño o los textos, habrá que ajustar los regex.
