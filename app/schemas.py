import re
from decimal import Decimal, InvalidOperation
from datetime import date
from pydantic import BaseModel, Field, field_validator, model_validator

# monedas
CURRENCY_MAP = {
    "$": ("USD", True),
    "usd": ("USD", True),
    "€": ("EUR", False),
    "eur": ("EUR", False),
    "cop": ("COP", True),
    "gbp": ("GBP", True),
    "£": ("GBP", True),
    "mxn": ("MXN", True),
    "brl": ("BRL", False),
    "r$": ("BRL", False),
    "clp": ("CLP", True),
    "pen": ("PEN", True),
    "ars": ("ARS", False),
}

def _detect_currency(raw: str) -> tuple[str | None, bool | None]:
    lower = raw.lower()
    for symbol, (code, dot_is_decimal) in CURRENCY_MAP.items():
        if symbol in lower:
            return code, dot_is_decimal
    return None, None

def _parse_number(raw: str, dot_is_decimal: bool | None = None) -> Decimal:
    # Quitar todo menos dígitos, puntos y comas
    clean = re.sub(r"[^\d.,]", "", raw).strip()
    if not clean:
        raise ValueError(f"No hay número en '{raw}'")

    dots = clean.count(".")
    commas = clean.count(",")

    if dot_is_decimal is True:
        # Estilo anglosajón: 1,234,567.89
        clean = clean.replace(",", "")
    elif dot_is_decimal is False:
        # Estilo europeo: 1.234.567,89
        clean = clean.replace(".", "").replace(",", ".")
    else:
        # Inferir por estructura
        if dots == 1 and commas == 0:
            after_dot = clean.split(".")[1]
            if len(after_dot) == 3:
                clean = clean.replace(".", "")
        elif commas == 1 and dots == 0:
            after_comma = clean.split(",")[1]
            if len(after_comma) == 3:
                clean = clean.replace(",", "")
            else:
                clean = clean.replace(",", ".")
        elif dots >= 1 and commas >= 1:
            last_dot = clean.rfind(".")
            last_comma = clean.rfind(",")
            if last_dot > last_comma:
                clean = clean.replace(",", "")
            else:
                clean = clean.replace(".", "").replace(",", ".")
        elif dots > 1:
            clean = clean.replace(".", "")
        elif commas > 1:
            clean = clean.replace(",", "")

    try:
        return Decimal(clean)
    except InvalidOperation:
        raise ValueError(f"No se pudo parsear '{raw}' → '{clean}'")

def _clean_key(k: str) -> str:
    k = k.lower().strip()
    k = re.sub(r"[%°]", "", k)
    k = re.sub(r"\s+", "_", k)
    k = re.sub(r"[^\w]", "", k)
    return k

def _clean_value(v, dot_is_decimal: bool | None = None):
    if not isinstance(v, str):
        return v
    raw = v.strip()
    # Dejar fecha como string
    if re.match(r"\d{4}-\d{2}-\d{2}", raw) or re.match(r"\d{2}/\d{2}/\d{4}", raw):
        return raw
    # Si tiene contenido numérico, convertir
    if re.search(r"\d", raw):
        try:
            currency_code, fmt = _detect_currency(raw)
            effective_fmt = fmt if fmt is not None else dot_is_decimal
            return float(_parse_number(raw, effective_fmt))
        except ValueError:
            pass
    return raw

class InvoiceData(BaseModel):
    fecha_emision: date = Field(..., description="Fecha de emisión YYYY-MM-DD")
    valor_total: Decimal = Field(..., description="Valor total numérico sin símbolos")
    numero_factura: str | None = None
    proveedor: str | None = None
    nit: str | None = None
    moneda: str = Field(default="COP")
    info_adicional: dict | None = Field(default=None)

    _dot_is_decimal: bool | None = None

    @field_validator("moneda", mode="before")
    @classmethod
    def normalize_moneda(cls, v):
        if not v:
            return "COP"
        upper = str(v).upper().strip()
        # Normalizar símbolos a ISO
        symbol_to_iso = {"$": "USD", "€": "EUR", "£": "GBP", "R$": "BRL"}
        return symbol_to_iso.get(upper, upper)

    @field_validator("valor_total", mode="before")
    @classmethod
    def clean_valor(cls, v):
        if isinstance(v, (int, float, Decimal)):
            return Decimal(str(v))
        _, dot_is_decimal = _detect_currency(str(v))
        return _parse_number(str(v), dot_is_decimal)

    @field_validator("fecha_emision", mode="before")
    @classmethod
    def clean_fecha(cls, v):
        if isinstance(v, date):
            return v
        from datetime import datetime
        formatos = [
            "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d",
            "%d %B %Y", "%B %d, %Y", "%d de %B de %Y",
        ]
        for fmt in formatos:
            try:
                return datetime.strptime(str(v).strip(), fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Fecha no reconocida: '{v}'")

    @field_validator("nit", mode="before")
    @classmethod
    def clean_nit(cls, v):
        if not v:
            return None
        return re.sub(r"[^\d]", "", str(v)) or None

    @field_validator("numero_factura", "proveedor", mode="before")
    @classmethod
    def strip_str(cls, v):
        return str(v).strip() if v else None

    @field_validator("info_adicional", mode="before")
    @classmethod
    def normalize_info(cls, v):
        if not v:
            return None
        return {_clean_key(k): _clean_value(str(val)) for k, val in v.items()}

    @model_validator(mode="after")
    def clean_nits_in_info(self):
        if not self.info_adicional:
            return self
        nit_re = re.compile(r"nit", re.IGNORECASE)
        self.info_adicional = {
            k: (re.sub(r"[^\d]", "", str(val)) if nit_re.search(k) and isinstance(val, str) else val)
            for k, val in self.info_adicional.items()
        }
        return self