from datetime import datetime, date
from decimal import Decimal
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON

class Invoice(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    filename: str
    fecha_emision: date
    valor_total: Decimal
    numero_factura: str | None = None
    proveedor: str | None = None
    nit: str | None = None
    moneda: str = "COP"
    metadata: dict | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)