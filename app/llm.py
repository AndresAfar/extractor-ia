import base64, os
from anthropic import AsyncAnthropic
from .schemas import InvoiceData

client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

EXTRACT_TOOL = {
    "name": "extract_invoice_data",
    "description": "Extrae los datos clave de una factura de servicios.",
    "input_schema": InvoiceData.model_json_schema(),
}

async def extract_from_document(file_bytes: bytes, media_type: str) -> InvoiceData:
    b64 = base64.standard_b64encode(file_bytes).decode("utf-8")
    source_type = "document" if media_type == "application/pdf" else "image"

    msg = await client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        tools=[EXTRACT_TOOL],
        tool_choice={"type": "tool", "name": "extract_invoice_data"},
        messages=[{
            "role": "user",
            "content": [
                {"type": source_type, "source": {
                    "type": "base64", "media_type": media_type, "data": b64
                }},
                {"type": "text", "text":
                    "Actúa como un extractor de datos de facturas. Devuelve los datos clave de esta factura de servicios. "
                    "La fecha de emisión debe ir en formato YYYY-MM-DD. "
                    "El valor total debe ser solo el número, sin símbolos de moneda."
                    "Cualquier dato adicional como fecha de vencimiento, número de medidor (si es servicios públicos), o periodos de consumo, agrégalos en el campo 'info_adicional'."
                },
            ],
        }],
    )

    # Validador en InvoiceData para limpiar string antes de conversion
    try:
        tool_use = next(b for b in msg.content if b.type == "tool_use")
        return InvoiceData.model_validate(tool_use.input)
    except Exception as e:
        print(f"Error validando datos de la factura: {e}")
        raise