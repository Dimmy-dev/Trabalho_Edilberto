import os
import json
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import engine, Base, get_db
from models import HospedeModel, AuditLogModel
from schemas import HospedeCreateSchema, HospedeResponseSchema, ApiResponse

import time
from collections import defaultdict

# Inicializa as tabelas no banco de dados configurado
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Grand Plaza Hotel Management API",
    description="API REST Segura para Gerenciamento de Hóspedes, Reservas e Pagamentos Pix — Laboratório de Inovação III",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Controle de Taxa em Memória (Rate Limiting por IP: máx 30 requisições por minuto)
RATE_LIMIT_STORE = defaultdict(list)
MAX_REQUESTS_PER_MINUTE = 30

@app.middleware("http")
async def security_and_rate_limit_middleware(request: Request, call_next):
    # 1. Rate Limiting por IP (Prevenção de Abuso e Brute-Force - OWASP API4)
    client_ip = request.client.host if request.client else "unknown"
    agora = time.time()
    
    # Limpa requisições com mais de 60 segundos
    RATE_LIMIT_STORE[client_ip] = [t for t in RATE_LIMIT_STORE[client_ip] if agora - t < 60]
    
    if len(RATE_LIMIT_STORE[client_ip]) >= MAX_REQUESTS_PER_MINUTE:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "success": False,
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Limite de requisições excedido. Por favor, aguarde 1 minuto."
                }
            },
            headers={"Retry-After": "60"}
        )
    
    RATE_LIMIT_STORE[client_ip].append(agora)

    # 2. Executa a requisição
    response = await call_next(request)

    # 3. Injeta Headers de Segurança Mandatórios (OWASP A05)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response

# Configuração de CORS Seguro
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Handler Global para Violação de Unicidade no Banco (RN-01 e RN-02)
@app.exception_handler(IntegrityError)
async def integrity_exception_handler(request: Request, exc: IntegrityError):
    error_str = str(exc.orig).lower() if hasattr(exc, "orig") else str(exc).lower()
    field = "dados"
    msg = "Registro já existente no sistema."

    if "email" in error_str:
        field = "email"
        msg = "Este endereço de e-mail já está cadastrado para outro hóspede."
    elif "cpf" in error_str:
        field = "cpf"
        msg = "Este CPF já se encontra registrado na base de dados."

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "success": False,
            "error": {
                "code": "DUPLICATE_ENTRY",
                "message": msg,
                "field": field
            }
        }
    )

@app.get("/api/v1/health", tags=["Monitoramento"])
def health_check():
    return {"status": "ONLINE", "service": "Grand Plaza Hotel API", "version": "1.0.0"}

@app.post(
    "/api/v1/hospedes",
    response_model=ApiResponse[HospedeResponseSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar Novo Hóspede (RF-001)",
    tags=["Hóspedes"]
)
def criar_hospede(payload: HospedeCreateSchema, request: Request, db: Session = Depends(get_db)):
    """
    Cadastra um novo hóspede aplicando validação estrita (Módulo 11 para CPF, RFC 5322 para e-mail)
    e proteção contra SQL Injection através de Prepared Statements (SQLAlchemy).
    """
    # Verificação preventiva de unicidade (Prevenção de Colisão)
    if db.query(HospedeModel).filter(HospedeModel.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "DUPLICATE_EMAIL", "message": "Este e-mail já está cadastrado no sistema.", "field": "email"}
        )
    
    if db.query(HospedeModel).filter(HospedeModel.cpf == payload.cpf).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "DUPLICATE_CPF", "message": "Este CPF já se encontra registrado.", "field": "cpf"}
        )

    novo_hospede = HospedeModel(
        nome=payload.nome.strip(),
        email=payload.email.strip().lower(),
        cpf=payload.cpf.strip(),
        telefone=payload.telefone.strip(),
        data_nascimento=payload.data_nascimento,
        observacoes=payload.observacoes.strip() if payload.observacoes else None
    )

    db.add(novo_hospede)
    db.commit()
    db.refresh(novo_hospede)

    # Registro na Trilha de Auditoria (RN-08 e LGPD)
    client_ip = request.client.host if request.client else "127.0.0.1"
    audit = AuditLogModel(
        id_hospede=novo_hospede.id,
        acao="CADASTRO_HOSPEDE_RF001",
        tabela_afetada="tb_hospedes",
        registro_id=novo_hospede.id,
        ip_origem=client_ip
    )
    db.add(audit)
    db.commit()

    return ApiResponse(
        success=True,
        data=novo_hospede,
        message="Hóspede cadastrado com sucesso no sistema Grand Plaza!"
    )

@app.get(
    "/api/v1/hospedes",
    response_model=ApiResponse[List[HospedeResponseSchema]],
    summary="Listar Hóspedes Cadastrados",
    tags=["Hóspedes"]
)
def listar_hospedes(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """Retorna a listagem paginada de hóspedes ordenada pelos registros mais recentes."""
    hospedes = db.query(HospedeModel).order_by(HospedeModel.created_at.desc()).offset(skip).limit(limit).all()
    return ApiResponse(
        success=True,
        data=hospedes,
        message=f"{len(hospedes)} hóspedes retornados com sucesso."
    )

@app.get("/export-swagger-json", include_in_schema=False)
def export_swagger_json():
    """Rota utilitária para salvar o contrato Swagger na pasta docs/api/"""
    openapi_schema = app.openapi()
    docs_api_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "docs", "api"))
    os.makedirs(docs_api_path, exist_ok=True)
    swagger_file = os.path.join(docs_api_path, "swagger.json")
    with open(swagger_file, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
    return {"message": "swagger.json gerado com sucesso!", "path": swagger_file}

# Serve o frontend (HTML, CSS, JS) diretamente na raiz do servidor
static_dir = os.path.dirname(__file__)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
