# Extractor de Facturas con IA

Permite cargar una factura (PDF o imagen), extraer información clave mediante un LLM y visualizar los datos.

## Stack

- **Backend:** FastAPI (Python 3.11+)
- **LLM:** Anthropic Claude Sonnet 4.5 (con tool use)
- **Persistencia:** SQLite + SQLModel
- **Frontend:** Jinja2 + Tailwind CSS + HTMX

## Requisitos

- Python 3.11 o superior
- API key de Anthropic ([console.anthropic.com](https://console.anthropic.com))

## Instalación y ejecución

```bash
# 1. Clonar el repositorio
git clone https://github.com/AndresAfar/extractor-ia.git
cd extractor-ia

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate    # Windows: .\venv\Scripts\Activate.ps1 

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env y agregar la ANTHROPIC_API_KEY

# 5. Levantar aplicacion
fastapi dev app/main.py
```

## Uso

1. Abrir `http://localhost:8000`
2. Cargar una factura en formato PDF, JPG, PNG o WEBP
3. Hacer clic en **Extraer datos**
4. Ver los campos extraídos: fecha de emisión, valor total, número de factura, proveedor y NIT
5. Las facturas procesadas se guardan automáticamente y aparecen en el historial

En la carpeta `sample_invoices/` se incluye una factura de ejemplo para probar.