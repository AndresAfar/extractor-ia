from datetime import datetime, date
from decimal import Decimal
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Numeric, JSON

class Invoice(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    filename: str
    fecha_emision: date
    valor_total: Decimal = Field(sa_column=Column(Numeric(precision=18, scale=2)))
    numero_factura: str | None = None
    proveedor: str | None = None
    nit: str | None = None
    moneda: str = "COP"
    info_adicional: dict | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)