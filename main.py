"""
APLICAÇÃO PRINCIPAL FASTAPI UNIFICADA
Grand Plaza Hotel Management System — Core Unificado (RF-001 a RF-005)
Laboratório de Inovação III — Prof. Edilberto Silva (2026)

Módulos Integrados:
- RF-001 & RF-002: Gestão de Hóspedes e Modificações Cadastrais
- RF-003: Gestão de Operadores e Autenticação com Cookies HttpOnly
- RF-004: Hospedagens, Check-in Atômico, Check-out e Rack Hoteleiro
- RF-005: Controle de Frigobar, Catálogo de Serviços e Lançamento de Consumo
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from database import engine, Base, garantir_dados_iniciais
from routers.auth import router as auth_router
from routers.hospedes import router as hospedes_router
from routers.operadores import router as operadores_router
from routers.hospedagem import router as hospedagem_router
from routers.consumo import router as consumo_router
from routers.governanca import router as governanca_router

# Inicialização da Base SQLAlchemy e Auto-Seed Idempotente
try:
    Base.metadata.create_all(bind=engine)
    garantir_dados_iniciais()
except Exception as e:
    print(f"[WARN] Inicialização de tabelas e dados: {e}")

app = FastAPI(
    title="Grand Plaza Hotel Management System — API Corporativa Unificada",
    description="Suíte completa de serviços hoteleiros corporativos com resiliência de dados, conformidade LGPD e segurança OWASP.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# ----------------------------------------------------------------------------
# MIDDLEWARES DE SEGURANÇA E RATE LIMITING
# ----------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.vercel\.app|http://(localhost|127\.0\.0\.1)(:[0-9]+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REQUEST_HISTORY = {}
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 180

@app.middleware("http")
async def security_and_rate_limit(request: Request, call_next):
    """Aplica cabeçalhos de segurança OWASP e proteção contra DoS."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    now = datetime.utcnow()

    # Rate Limiting
    if client_ip not in REQUEST_HISTORY:
        REQUEST_HISTORY[client_ip] = []
    
    REQUEST_HISTORY[client_ip] = [
        t for t in REQUEST_HISTORY[client_ip]
        if (now - t).total_seconds() < RATE_LIMIT_WINDOW
    ]

    if len(REQUEST_HISTORY[client_ip]) >= RATE_LIMIT_MAX:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Muitas requisições. Aguarde 60 segundos.",
                    "field": None
                }
            }
        )

    REQUEST_HISTORY[client_ip].append(now)

    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response

# ----------------------------------------------------------------------------
# TRATAMENTO PADRONIZADO DE ERROS (ENVELOPE PATTERN)
# ----------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Garante que qualquer HTTPException respeite o Envelope Pattern."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail,
                "field": None
            }
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Intercepta falhas de validação de schemas Pydantic v2."""
    erros = exc.errors()
    primeiro = erros[0] if erros else {}
    campo = ".".join(str(loc) for loc in primeiro.get("loc", []))
    msg = primeiro.get("msg", "Erro de validação dos dados de entrada.")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": f"Campo '{campo}': {msg}",
                "field": campo
            }
        }
    )

# ----------------------------------------------------------------------------
# REGISTRO DE ROUTERS MODULARES
# ----------------------------------------------------------------------------

app.include_router(auth_router)
app.include_router(hospedes_router)
app.include_router(operadores_router)
app.include_router(hospedagem_router)
app.include_router(consumo_router)
app.include_router(governanca_router)

# ----------------------------------------------------------------------------
# EXPORTAÇÃO AUTOMÁTICA DE CONTRATO OPENAPI 3.1
# ----------------------------------------------------------------------------

@app.on_event("startup")
def exportar_openapi_spec():
    """Garante exportação automática de docs/api/swagger.json para atendimento à rubrica."""
    try:
        docs_api_dir = CURRENT_DIR.parent / "docs" / "api"
        docs_api_dir.mkdir(parents=True, exist_ok=True)
        swagger_file = docs_api_dir / "swagger.json"
        
        with open(swagger_file, "w", encoding="utf-8") as f:
            json.dump(app.openapi(), f, indent=2, ensure_ascii=False)
        print(f"[SWAGGER] OpenAPI 3.1 exportado com sucesso em: {swagger_file}")
    except Exception as e:
        print(f"[SWAGGER-WARN] Falha ao exportar swagger.json: {e}")

# ----------------------------------------------------------------------------
# ROTAS ESTÁTICAS DA SPA INTEGRADA
# ----------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse, tags=["Frontend"])
def serve_index():
    """Entrega a SPA corporativa consolidada do Grand Plaza Hotel."""
    html_path = CURRENT_DIR / "index.html"
    if not html_path.exists():
        return HTMLResponse("<h1>Grand Plaza Hotel — Core Unificado Ativo</h1>")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.get("/app.js", tags=["Frontend"])
def serve_app_js():
    """Entrega o script unificado da SPA."""
    js_path = CURRENT_DIR / "app.js"
    if not js_path.exists():
        raise HTTPException(status_code=404, detail="app.js não encontrado")
    return FileResponse(js_path, media_type="application/javascript")
