"""
ROUTER FASTAPI — RF-006: GOVERNANÇA E MANUTENÇÃO
Grand Plaza Hotel Management System — Core Unificado
Sincronizado bidirecionalmente com RF-004 (Acomodações & Rack Hoteleiro) e RF-003 (Autenticação & Auditoria)
"""

import json
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models import OrdemServicoModel, AcomodacaoModel, OperadorModel, AuditLogModel
from schemas import (
    OrdemServicoCreateSchema,
    OrdemServicoConcluirSchema,
    OrdemServicoResponseSchema,
    EnvelopeResponse
)
from routers.auth import get_current_active_operator

router = APIRouter(prefix="/api/v1/governanca", tags=["RF-006: Governança e Manutenção"])

@router.get("/ordens", response_model=EnvelopeResponse[List[OrdemServicoResponseSchema]])
def listar_ordens(
    status_filtro: Optional[str] = Query(None, alias="status", description="Filtrar por PENDENTE, EM_EXECUCAO ou CONCLUIDA"),
    quarto_numero: Optional[str] = Query(None, description="Filtrar pelo número do quarto do Rack"),
    db: Session = Depends(get_db),
    operador: OperadorModel = Depends(get_current_active_operator)
):
    """Lista todas as Ordens de Serviço cadastradas em ordem decrescente, sincronizadas com o inventário do Rack."""
    query = db.query(OrdemServicoModel)
    if status_filtro:
        query = query.filter(OrdemServicoModel.status == status_filtro.strip().upper())
    if quarto_numero:
        query = query.filter(OrdemServicoModel.quarto_numero == quarto_numero.strip())

    ordens = query.order_by(OrdemServicoModel.criado_em.desc()).all()
    return EnvelopeResponse(success=True, data=ordens, error=None)

@router.post("/ordens", response_model=EnvelopeResponse[OrdemServicoResponseSchema], status_code=status.HTTP_201_CREATED)
def criar_ordem(
    dados: OrdemServicoCreateSchema,
    request: Request,
    db: Session = Depends(get_db),
    operador: OperadorModel = Depends(get_current_active_operator)
):
    """Cria uma nova OS validando o quarto contra tb_acomodacoes e transiciona seu status no Rack para LIMPEZA ou MANUTENCAO."""
    num_quarto = dados.quarto_numero.strip()
    quarto = db.query(AcomodacaoModel).filter(
        AcomodacaoModel.numero == num_quarto,
        AcomodacaoModel.is_ativo == 1
    ).first()
    if not quarto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quarto {num_quarto} não existe no inventário de acomodações (RF-004)."
        )

    if quarto.status == "OCUPADO":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Quarto {num_quarto} está OCUPADO no momento. Realize o check-out antes de abrir bloqueio de {dados.tipo}."
        )

    total = db.query(OrdemServicoModel).count()
    codigo = f"OS-2026-{str(total + 1).zfill(4)}"

    nova = OrdemServicoModel(
        uuid_os=str(uuid.uuid4()),
        codigo_os=codigo,
        quarto_numero=quarto.numero,
        tipo=dados.tipo,
        prioridade=dados.prioridade,
        status="PENDENTE",
        descricao=dados.descricao.strip(),
        responsavel=dados.responsavel or operador.nome or "Equipe de Governança",
        criado_em=datetime.utcnow()
    )
    db.add(nova)

    status_anterior_quarto = quarto.status
    quarto.status = "MANUTENCAO" if dados.tipo == "MANUTENCAO" else "LIMPEZA"

    log = AuditLogModel(
        id_operador=operador.id,
        acao="CRIAR_ORDEM_SERVICO",
        tabela_afetada="tb_ordens_servico",
        registro_id=nova.uuid_os,
        detalhes_json=json.dumps({
            "codigo_os": codigo,
            "quarto": quarto.numero,
            "tipo": dados.tipo,
            "status_quarto_de": status_anterior_quarto,
            "status_quarto_para": quarto.status
        }),
        ip_origem=request.client.host if request.client else None
    )
    db.add(log)

    db.commit()
    db.refresh(nova)
    return EnvelopeResponse(success=True, data=nova, error=None)

@router.patch("/ordens/{uuid_os}/concluir", response_model=EnvelopeResponse[OrdemServicoResponseSchema])
def concluir_ordem(
    uuid_os: str,
    dados: OrdemServicoConcluirSchema,
    request: Request,
    db: Session = Depends(get_db),
    operador: OperadorModel = Depends(get_current_active_operator)
):
    """Conclui a OS e libera o quarto correspondente para DISPONIVEL no Rack se não houver outra OS aberta."""
    os_db = db.query(OrdemServicoModel).filter(OrdemServicoModel.uuid_os == uuid_os).first()
    if not os_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ordem de Serviço não encontrada.")

    if os_db.status == "CONCLUIDA":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Esta Ordem de Serviço já foi concluída.")

    os_db.status = "CONCLUIDA"
    os_db.observacoes_conclusao = dados.observacoes_conclusao
    os_db.responsavel = dados.responsavel_conclusao or os_db.responsavel or operador.nome
    os_db.concluido_em = datetime.utcnow()

    # Verifica se ainda existe outra OS pendente/em execução para o mesmo quarto antes de liberar
    quarto = db.query(AcomodacaoModel).filter(AcomodacaoModel.numero == os_db.quarto_numero).first()
    if quarto and quarto.status != "OCUPADO":
        outra_os_aberta = db.query(OrdemServicoModel).filter(
            OrdemServicoModel.quarto_numero == os_db.quarto_numero,
            OrdemServicoModel.uuid_os != os_db.uuid_os,
            OrdemServicoModel.status != "CONCLUIDA"
        ).first()
        if outra_os_aberta:
            quarto.status = "MANUTENCAO" if outra_os_aberta.tipo == "MANUTENCAO" else "LIMPEZA"
        else:
            quarto.status = "DISPONIVEL"

    log = AuditLogModel(
        id_operador=operador.id,
        acao="CONCLUIR_ORDEM_SERVICO",
        tabela_afetada="tb_ordens_servico",
        registro_id=os_db.uuid_os,
        detalhes_json=json.dumps({
            "codigo_os": os_db.codigo_os,
            "quarto": os_db.quarto_numero,
            "novo_status_quarto": quarto.status if quarto else None
        }),
        ip_origem=request.client.host if request.client else None
    )
    db.add(log)

    db.commit()
    db.refresh(os_db)
    return EnvelopeResponse(success=True, data=os_db, error=None)

