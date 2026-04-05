# Invoice pipeline for GitHub Actions

Este repo procesa automáticamente facturas PDF colocadas en `inbox/`.

## Qué hace

1. Detecta PDFs nuevos en `inbox/`.
2. Extrae texto nativo con **PyMuPDF** cuando el PDF ya tiene capa de texto.
3. Si el texto es insuficiente, aplica **OCRmyPDF + Tesseract** para OCR.
4. Hace una extracción híbrida:
   - parser genérico por etiquetas y patrones
   - plantillas por proveedor con `invoice2data`
   - segunda pasada "AI-like" local para corregir fallos frecuentes
5. Valida el resultado.
6. Añade una línea JSON a `output/invoices.jsonl`.
7. Mueve el PDF a `processed/` si la confianza es suficiente, o a `failed/` si no.

## Estructura

```text
inbox/      # tú subes aquí las facturas
processed/  # facturas bien procesadas
failed/     # facturas dudosas o mal extraídas
output/     # invoices.jsonl y raw_text/
templates/  # plantillas por proveedor
```

## Cómo se usa en GitHub

- Sube una factura PDF a `inbox/`.
- GitHub Actions lanzará el workflow `Process invoices`.
- El workflow dejará:
  - `output/invoices.jsonl`
  - `output/raw_text/<archivo>.txt`
  - el PDF movido a `processed/` o `failed/`

## Formato JSONL

Cada línea contiene algo como esto:

```json
{
  "source_file": "Factura.pdf",
  "source_method": "native_text",
  "supplier_name": "Naturgy Iberia, S.A.",
  "invoice_number": "FE25321494893037",
  "issue_date": "2025-04-16",
  "total_amount": 100.91,
  "confidence": 0.9,
  "needs_review": false,
  "validation_errors": []
}
```

## Importante

### Coste

Esto está pensado para **repos públicos**, porque los runners estándar de GitHub Actions son gratuitos e ilimitados en repos públicos.

### Privacidad

Si subes facturas reales a un repo público, el contenido será público.

## Prueba local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
python process_invoices.py --repo-root .
```

## Mejoras fáciles

- Añadir más plantillas en `templates/`
- Añadir normalizadores por sector: luz, gas, agua, telecom
- Enviar resumen por PR o issue
