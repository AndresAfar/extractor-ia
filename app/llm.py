import base64, os, asyncio
from io import BytesIO
from anthropic import AsyncAnthropic
from .schemas import InvoiceData

client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

EXTRACT_TOOL = {
    "name": "extract_invoice_data",
    "description": "Extrae los datos clave de una factura de servicios.",
    "input_schema": InvoiceData.model_json_schema(),
}

def _pdf_to_text(file_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(file_bytes))
        text = "\n".join(p.extract_text() or "" for p in reader.pages).strip()
        return text[:6000]
    except Exception:
        return ""

def _image_preprocess(file_bytes: bytes, media_type: str) -> tuple[bytes, str]:
    try:
        from PIL import Image, ImageEnhance, ImageOps
        img = Image.open(BytesIO(file_bytes)).convert("RGB")

        img = ImageOps.exif_transpose(img)

        # Reducir si es muy grande
        max_side = 2000
        if max(img.size) > max_side:
            img.thumbnail((max_side, max_side), Image.LANCZOS)

        # Mejorar contraste y nitidez
        img = ImageEnhance.Contrast(img).enhance(1.4)
        img = ImageEnhance.Sharpness(img).enhance(1.5)

        buf = BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue(), "image/jpeg"
    except Exception:
        return file_bytes, media_type

def _image_to_text(file_bytes: bytes) -> str:
    """OCR con pytesseract como contexto de respaldo (opcional)."""
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(BytesIO(file_bytes))
        text = pytesseract.image_to_string(img, lang="spa+eng")
        return text.strip()[:6000]
    except Exception:
        return ""

async def _call_claude(file_bytes: bytes, media_type: str) -> InvoiceData:
    extra_context = ""

    if media_type == "application/pdf":
        raw_text = _pdf_to_text(file_bytes)
        if raw_text:
            extra_context = f"\n\nTexto extraído del PDF:\n```\n{raw_text}\n```"
    else:
        # Preprocesar imagen y sacar OCR
        file_bytes, media_type = _image_preprocess(file_bytes, media_type)
        raw_text = _image_to_text(file_bytes)
        if raw_text:
            extra_context = f"\n\nTexto detectado por OCR (puede tener errores):\n```\n{raw_text}\n```"

    b64 = base64.standard_b64encode(file_bytes).decode("utf-8")
    source_type = "document" if media_type == "application/pdf" else "image"

    msg = await client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        tools=[EXTRACT_TOOL],
        tool_choice={"type": "tool", "name": "extract_invoice_data"},
        messages=[{
            "role": "user",
            "content": [
                {"type": source_type, "source": {
                    "type": "base64", "media_type": media_type, "data": b64
                }},
                {"type": "text", "text": (
                    "Actúa como un extractor de datos de facturas. "
                    "Devuelve los datos clave de esta factura. "
                    "La fecha de emisión debe ir en formato YYYY-MM-DD. "
                    "El valor total debe ser solo el número sin símbolos ni separadores de miles. "
                    "Datos adicionales (vencimiento, medidor, periodo de consumo) van en 'info_adicional'."
                    + extra_context
                )},
            ],
        }],
    )

    tool_use = next(b for b in msg.content if b.type == "tool_use")
    return InvoiceData.model_validate(tool_use.input)

async def extract_from_document(file_bytes: bytes, media_type: str) -> InvoiceData:
    last_exc = None
    for attempt in range(3):
        try:
            return await _call_claude(file_bytes, media_type)
        except Exception as e:
            last_exc = e
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
    raise last_exc