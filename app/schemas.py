from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field

class InvoiceData(BaseModel):
    fecha_emision: date = Field(..., description="Fecha de emisión en formato YYYY-MM-DD")
    valor_total: Decimal = Field(..., description="Valor total a pagar (solo número)")
    numero_factura: str | None = None
    proveedor: str | None = None
    nit: str | None = None
    moneda: str = Field(default="COP")