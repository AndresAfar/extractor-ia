from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from dotenv import load_dotenv

from .llm import extract_from_document
from .models import Invoice

load_dotenv()

engine = create_async_engine("sqlite+aiosqlite:///./facturas.db")
SessionMaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield

app = FastAPI(title="Extractor de Facturas", lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")

ALLOWED = {"application/pdf", "image/jpeg", "image/png", "image/webp"}

async def get_session():
    async with SessionMaker() as session:
        yield session

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Invoice).order_by(Invoice.created_at.desc()).limit(20))
    invoices = result.scalars().all()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "invoices": invoices
        }
    )

@app.post("/extract", response_class=HTMLResponse)
async def extract(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session),
):
    if file.content_type not in ALLOWED:
        raise HTTPException(415, "Solo se aceptan PDF o imágenes (JPG/PNG/WEBP)")

    data = await extract_from_document(await file.read(), file.content_type)
    invoice = Invoice(filename=file.filename, **data.model_dump())
    db.add(invoice); await db.commit(); await db.refresh(invoice)

    # Devuelve el partial — HTMX lo inserta en el DOM
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "invoices": invoice
        }
    )