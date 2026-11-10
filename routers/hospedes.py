"""
ROUTER DE GESTÃO DE HÓSPEDES (RF-001 & RF-002)
Grand Plaza Hotel Management System — Core Unificado
Diretrizes: regras/back.md e OWASP Top 10 (A03 SQL Injection)
"""

import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database import get_db
from models import HospedeModel, OperadorModel, AuditLogModel
from schemas import (
    HospedeCreateSchema,
    HospedeUpdateSchema,
    HospedeResponseSchema,
    EnvelopeResponse
)
from routers.auth import get_current_active_operator

router = APIRouter(prefix="/api/v1/hospedes", tags=["Hóspedes (RF-001/002)"])

@router.post("", response_model=EnvelopeResponse[HospedeResponseSchema], status_code=status.HTTP_201_CREATED)
def cadastrar_hospede(
    payload: HospedeCreateSchema,
    request: Request,
    db: Session = Depends(get_db),
    operador: OperadorModel = Depends(get_current_active_operator)
):
    """Cadastra um novo hóspede com validação estrita de CPF (Módulo 11) e unicidade."""
    # Checagem de duplicidade por CPF ou E-mail
    existente = db.query(HospedeModel).filter(
        or_(HospedeModel.cpf == payload.cpf, HospedeModel.email == payload.email)
    ).first()

    if existente:
        campo_duplicado = "cpf" if existente.cpf == payload.cpf else "email"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe um hóspede cadastrado com este {campo_duplicado.upper()}."
        )

    novo = HospedeModel(
        nome=payload.nome,
        email=payload.email,
        cpf=payload.cpf,
        telefone=payload.telefone,
        data_nascimento=payload.data_nascimento,
        observacoes=payload.observacoes,
        is_ativo=1
    )
    db.add(novo)
    db.flush()

    # Trilha de Auditoria LGPD
    log = AuditLogModel(
        id_operador=operador.id,
        acao="CADASTRO_HOSPEDE",
        tabela_afetada="tb_hospedes",
        registro_id=novo.uuid_publico,
        detalhes_json=json.dumps({"cpf": novo.cpf, "email": novo.email}),
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

@router.get("", response_model=EnvelopeResponse[List[HospedeResponseSchema]])
def listar_hospedes(
    termo: Optional[str] = Query(None, description="Busca preditiva por nome, CPF ou e-mail"),
    is_ativo: Optional[int] = Query(None, description="Filtro de status ativo (1) ou inativo (0)"),
    db: Session = Depends(get_db),
    operador: OperadorModel = Depends(get_current_active_operator)
):
    """Lista todos os hóspedes cadastrados com suporte a busca preditiva e paginação."""
    query = db.query(HospedeModel)

    if is_ativo is not None:
        query = query.filter(HospedeModel.is_ativo == is_ativo)

    if termo:
        t = f"%{termo.strip().lower()}%"
        query = query.filter(
            or_(
                HospedeModel.nome.ilike(t),
                HospedeModel.cpf.like(f"%{termo.strip()}%"),
                HospedeModel.email.ilike(t)
            )
        )

    hospedes = query.order_by(HospedeModel.nome.asc()).all()

    from models import HospedagemModel
    resultado = []
    for h in hospedes:
        # Busca se há estadia ativa em curso para este hóspede
        estadia_ativa = db.query(HospedagemModel).filter(
            HospedagemModel.id_hospede == h.id,
            HospedagemModel.status == "ATIVA"
        ).first()

        resultado.append({
            "uuid_publico": h.uuid_publico,
            "nome": h.nome,
            "email": h.email,
            "cpf": h.cpf,
            "telefone": h.telefone,
            "data_nascimento": h.data_nascimento,
            "observacoes": h.observacoes,
            "is_ativo": h.is_ativo,
            "esta_hospedado": estadia_ativa is not None,
            "quarto_atual": estadia_ativa.acomodacao.numero if estadia_ativa and estadia_ativa.acomodacao else None,
            "created_at": h.created_at
        })

    return {
        "success": True,
        "data": resultado,
        "error": None
    }

@router.get("/{uuid_hospede}", response_model=EnvelopeResponse[HospedeResponseSchema])
def obter_hospede(
    uuid_hospede: str,
    db: Session = Depends(get_db),
    operador: OperadorModel = Depends(get_current_active_operator)
):
    """Retorna os dados detalhados de um hóspede pelo seu UUID público."""
    hospede = db.query(HospedeModel).filter_by(uuid_publico=uuid_hospede).first()
    if not hospede:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hóspede não localizado no sistema."
        )

    return {
        "success": True,
        "data": hospede,
        "error": None
    }

@router.put("/{uuid_hospede}", response_model=EnvelopeResponse[HospedeResponseSchema])
def atualizar_hospede(
    uuid_hospede: str,
    payload: HospedeUpdateSchema,
    request: Request,
    db: Session = Depends(get_db),
    operador: OperadorModel = Depends(get_current_active_operator)
):
    """Atualiza dados cadastrais permitidos do hóspede (RF-002)."""
    hospede = db.query(HospedeModel).filter_by(uuid_publico=uuid_hospede).first()
    if not hospede:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hóspede não localizado."
        )

    if payload.email and payload.email != hospede.email:
        existente = db.query(HospedeModel).filter(
            HospedeModel.email == payload.email,
            HospedeModel.id != hospede.id
        ).first()
        if existente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe outro hóspede cadastrado com este e-mail."
            )
        hospede.email = payload.email

    if payload.nome:
        hospede.nome = payload.nome
    if payload.telefone:
        hospede.telefone = payload.telefone
    if payload.observacoes is not None:
        hospede.observacoes = payload.observacoes

    log = AuditLogModel(
        id_operador=operador.id,
        acao="ALTERACAO_HOSPEDE",
        tabela_afetada="tb_hospedes",
        registro_id=hospede.uuid_publico,
        detalhes_json=json.dumps({"nome": hospede.nome, "email": hospede.email}),
        ip_origem=request.client.host if request.client else None
    )
    db.add(log)
    db.commit()
    db.refresh(hospede)

    return {
        "success": True,
        "data": hospede,
        "error": None
    }

@router.patch("/{uuid_hospede}/status", response_model=EnvelopeResponse[HospedeResponseSchema])
def alternar_status_hospede(
    uuid_hospede: str,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    operador: OperadorModel = Depends(get_current_active_operator)
):
    """Ativa ou inativa o cadastro de um hóspede no hotel (Soft Delete)."""
    hospede = db.query(HospedeModel).filter_by(uuid_publico=uuid_hospede).first()
    if not hospede:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hóspede não localizado."
        )

    novo_status = int(payload.get("is_ativo", 1))
    hospede.is_ativo = novo_status

    log = AuditLogModel(
        id_operador=operador.id,
        acao="STATUS_HOSPEDE",
        tabela_afetada="tb_hospedes",
        registro_id=hospede.uuid_publico,
        detalhes_json=json.dumps({"novo_status": novo_status}),
        ip_origem=request.client.host if request.client else None
    )
    db.add(log)
    db.commit()
    db.refresh(hospede)

    return {
        "success": True,
        "data": hospede,
        "error": None
    }
