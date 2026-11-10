"""
ROUTER DE USUÁRIOS E OPERADORES DO SISTEMA (RF-003)
Grand Plaza Hotel Management System — Core Unificado
Diretrizes: regras/back.md e OWASP Top 10 (A07 Broken Auth, RBAC)
"""

import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from database import get_db
from models import OperadorModel, AuditLogModel
from schemas import (
    OperadorCreateSchema,
    OperadorStatusSchema,
    OperadorResponseSchema,
    EnvelopeResponse
)
from routers.auth import get_current_active_operator, require_role, gerar_hash_senha

router = APIRouter(prefix="/api/v1/operadores", tags=["Operadores (RF-003)"])

@router.post("", response_model=EnvelopeResponse[OperadorResponseSchema], status_code=status.HTTP_201_CREATED)
def cadastrar_operador(
    payload: OperadorCreateSchema,
    request: Request,
    db: Session = Depends(get_db),
    operador_atual: OperadorModel = Depends(require_role(["ADMIN", "GERENTE"]))
):
    """Cadastra um novo operador com derivação de senha em Bcrypt (12 rounds)."""
    if payload.confirmacao_senha and payload.senha != payload.confirmacao_senha:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A senha e a confirmação de senha não coincidem."
        )

    existente = db.query(OperadorModel).filter(
        OperadorModel.email == payload.email.lower().strip()
    ).first()

    if existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este e-mail já está em uso por outro operador da equipe."
        )

    novo = OperadorModel(
        nome=payload.nome,
        email=payload.email.lower().strip(),
        senha_hash=gerar_hash_senha(payload.senha),
        cargo=payload.cargo.upper(),
        is_ativo=1
    )
    db.add(novo)
    db.flush()

    log = AuditLogModel(
        id_operador=operador_atual.id,
        acao="CADASTRO_OPERADOR",
        tabela_afetada="tb_operadores",
        registro_id=novo.uuid_publico,
        detalhes_json=json.dumps({"nome": novo.nome, "email": novo.email, "cargo": novo.cargo}),
        ip_origem=request.client.host if request.client else None
    )
    db.add(log)
    db.commit()
    db.refresh(novo)

    return {
        "success": True,
        "data": novo,
        "error": None
    }

@router.get("", response_model=EnvelopeResponse[List[OperadorResponseSchema]])
def listar_operadores(
    db: Session = Depends(get_db),
    operador: OperadorModel = Depends(get_current_active_operator)
):
    """Lista todos os operadores com status de presença em tempo real (Online se houver sessão ativa)."""
    from datetime import datetime
    from models import SessaoModel
    
    agora = datetime.utcnow()
    operadores = db.query(OperadorModel).order_by(OperadorModel.nome.asc()).all()
    
    resultado = []
    for op in operadores:
        # Verifica se o operador possui sessão ativa não expirada
        tem_sessao_ativa = db.query(SessaoModel).filter(
            SessaoModel.id_operador == op.id,
            SessaoModel.is_active == 1,
            SessaoModel.expires_at > agora
        ).first() is not None
        
        resultado.append({
            "uuid_publico": op.uuid_publico,
            "nome": op.nome,
            "email": op.email,
            "cargo": op.cargo,
            "is_ativo": op.is_ativo,
            "is_online": tem_sessao_ativa,
            "token": None,
            "created_at": op.created_at
        })

    return {
        "success": True,
        "data": resultado,
        "error": None
    }

@router.patch("/{uuid_operador}/status", response_model=EnvelopeResponse[OperadorResponseSchema])
def alternar_status_operador(
    uuid_operador: str,
    payload: OperadorStatusSchema,
    request: Request,
    db: Session = Depends(get_db),
    operador_atual: OperadorModel = Depends(require_role(["ADMIN", "GERENTE"]))
):
    """Ativa ou desativa o acesso de um operador no sistema (apenas Admin/Gerente)."""
    alvo = db.query(OperadorModel).filter_by(uuid_publico=uuid_operador).first()
    if not alvo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operador não localizado."
        )

    if alvo.id == operador_atual.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não pode desativar seu próprio acesso administrativo."
        )

    alvo.is_ativo = payload.is_ativo

    log = AuditLogModel(
        id_operador=operador_atual.id,
        acao="STATUS_OPERADOR",
        tabela_afetada="tb_operadores",
        registro_id=alvo.uuid_publico,
        detalhes_json=json.dumps({"novo_status": payload.is_ativo}),
        ip_origem=request.client.host if request.client else None
    )
    db.add(log)
    db.commit()
    db.refresh(alvo)

    return {
        "success": True,
        "data": alvo,
        "error": None
    }
