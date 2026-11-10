"""
ROUTER FASTAPI — RF-006: GOVERNANÇA E MANUTENÇÃO
Grand Plaza Hotel Management System
"""

import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import OrdemServicoModel, AcomodacaoModel
from schemas import (
    OrdemServicoCreateSchema,
    OrdemServicoConcluirSchema,
    OrdemServicoResponseSchema,
    EnvelopeResponse
)

router = APIRouter(prefix="/api/v1/governanca", tags=["RF-006: Governança e Manutenção"])

@router.get("/ordens", response_model=EnvelopeResponse[List[OrdemServicoResponseSchema]])
def listar_ordens(db: Session = Depends(get_db)):
    """Lista todas as Ordens de Serviço cadastradas em ordem decrescente."""
    ordens = db.query(OrdemServicoModel).order_by(OrdemServicoModel.criado_em.desc()).all()
    return EnvelopeResponse(success=True, data=ordens, error=None)

@router.post("/ordens", response_model=EnvelopeResponse[OrdemServicoResponseSchema], status_code=status.HTTP_201_CREATED)
def criar_ordem(dados: OrdemServicoCreateSchema, db: Session = Depends(get_db)):
    """Cria uma nova OS e ajusta o quarto para LIMPEZA ou MANUTENCAO no rack se não estiver ocupado."""
    total = db.query(OrdemServicoModel).count()
    codigo = f"OS-2026-{str(total + 1).zfill(4)}"

    nova = OrdemServicoModel(
        codigo_os=codigo,
        quarto_numero=dados.quarto_numero.strip(),
        tipo=dados.tipo,
        prioridade=dados.prioridade,
        status="PENDENTE",
        descricao=dados.descricao.strip(),
        responsavel=dados.responsavel or "Equipe de Governança",
        criado_em=datetime.utcnow()
    )
    db.add(nova)

    # Atualiza quarto correspondente se existir
    quarto = db.query(AcomodacaoModel).filter(AcomodacaoModel.numero == dados.quarto_numero.strip()).first()
    if quarto and quarto.status != "OCUPADO":
        quarto.status = "MANUTENCAO" if dados.tipo == "MANUTENCAO" else "LIMPEZA"

    db.commit()
    db.refresh(nova)
    return EnvelopeResponse(success=True, data=nova, error=None)

@router.patch("/ordens/{uuid_os}/concluir", response_model=EnvelopeResponse[OrdemServicoResponseSchema])
def concluir_ordem(uuid_os: str, dados: OrdemServicoConcluirSchema, db: Session = Depends(get_db)):
    """Conclui a OS e libera o quarto para DISPONIVEL."""
    os_db = db.query(OrdemServicoModel).filter(OrdemServicoModel.uuid_os == uuid_os).first()
    if not os_db:
        raise HTTPException(status_code=404, detail="Ordem de Serviço não encontrada.")

    if os_db.status == "CONCLUIDA":
        raise HTTPException(status_code=400, detail="Esta Ordem de Serviço já foi concluída.")

    os_db.status = "CONCLUIDA"
    os_db.observacoes_conclusao = dados.observacoes_conclusao
    os_db.responsavel = dados.responsavel_conclusao or os_db.responsavel
    os_db.concluido_em = datetime.utcnow()

    # Transição atômica: quarto torna-se DISPONÍVEL
    quarto = db.query(AcomodacaoModel).filter(AcomodacaoModel.numero == os_db.quarto_numero).first()
    if quarto and quarto.status != "OCUPADO":
        quarto.status = "DISPONIVEL"

    db.commit()
    db.refresh(os_db)
    return EnvelopeResponse(success=True, data=os_db, error=None)

