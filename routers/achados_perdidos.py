"""
ROUTER FASTAPI — RF-007: GESTÃO DE ACHADOS E PERDIDOS (LOST & FOUND)
Grand Plaza Hotel Management System — Core Unificado
Conformidade: Envelope Pattern, RBAC (OWASP A01), Sanitização ORM/XSS (OWASP A03) e Trilha LGPD.
"""

import json
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models import AchadoPerdidoModel, OperadorModel, AuditLogModel
from schemas import (
    AchadoPerdidoCreateSchema,
    AchadoPerdidoDevolverSchema,
    AchadoPerdidoDescartarSchema,
    AchadoPerdidoResponseSchema,
    EnvelopeResponse,
)
from routers.auth import get_current_active_operator

router = APIRouter(prefix="/api/v1/achados-perdidos", tags=["RF-007: Achados e Perdidos"])


def _registrar_auditoria(
    db: Session,
    operador: OperadorModel,
    acao: str,
    registro_id: str,
    detalhes: dict,
    request: Request,
) -> None:
    """Registra evento imutável na trilha de auditoria LGPD."""
    log = AuditLogModel(
        id_operador=operador.id,
        acao=acao,
        tabela_afetada="tb_achados_perdidos",
        registro_id=registro_id,
        detalhes_json=json.dumps(detalhes, ensure_ascii=False),
        ip_origem=request.client.host if request.client else None,
    )
    db.add(log)


@router.get("", response_model=EnvelopeResponse[List[AchadoPerdidoResponseSchema]])
def listar_itens(
    status_filtro: Optional[str] = Query(
        None, alias="status", description="Filtrar por ENCONTRADO, DEVOLVIDO ou DESCARTADO"
    ),
    busca: Optional[str] = Query(None, description="Filtrar por descrição, código ou local"),
    db: Session = Depends(get_db),
    operador: OperadorModel = Depends(get_current_active_operator),
):
    """Lista os itens de achados e perdidos ordenados do mais recente para o mais antigo."""
    query = db.query(AchadoPerdidoModel)
    if status_filtro:
        query = query.filter(AchadoPerdidoModel.status == status_filtro.strip().upper())
    if busca:
        termo = f"%{busca.strip()}%"
        query = query.filter(
            (AchadoPerdidoModel.descricao.ilike(termo))
            | (AchadoPerdidoModel.codigo_item.ilike(termo))
            | (AchadoPerdidoModel.local_encontrado.ilike(termo))
        )

    itens = query.order_by(AchadoPerdidoModel.encontrado_em.desc()).all()
    return EnvelopeResponse(success=True, data=itens, error=None)


@router.post(
    "",
    response_model=EnvelopeResponse[AchadoPerdidoResponseSchema],
    status_code=status.HTTP_201_CREATED,
)
def registrar_item(
    dados: AchadoPerdidoCreateSchema,
    request: Request,
    db: Session = Depends(get_db),
    operador: OperadorModel = Depends(get_current_active_operator),
):
    """Registra um novo objeto encontrado no hotel gerando código único AP-2026-XXXX."""
    total = db.query(AchadoPerdidoModel).count()
    codigo = f"AP-2026-{str(total + 1).zfill(4)}"

    novo_item = AchadoPerdidoModel(
        uuid_item=str(uuid.uuid4()),
        codigo_item=codigo,
        descricao=dados.descricao,
        categoria=dados.categoria,
        local_encontrado=dados.local_encontrado,
        status="ENCONTRADO",
        encontrado_por=dados.encontrado_por or operador.nome or "Equipe do Hotel",
        observacoes=dados.observacoes,
        encontrado_em=datetime.utcnow(),
    )
    db.add(novo_item)

    _registrar_auditoria(
        db=db,
        operador=operador,
        acao="REGISTRAR_ACHADO_PERDIDO",
        registro_id=novo_item.uuid_item,
        detalhes={
            "codigo_item": codigo,
            "categoria": dados.categoria,
            "local_encontrado": dados.local_encontrado,
        },
        request=request,
    )

    db.commit()
    db.refresh(novo_item)
    return EnvelopeResponse(success=True, data=novo_item, error=None)


@router.patch(
    "/{uuid_item}/devolver",
    response_model=EnvelopeResponse[AchadoPerdidoResponseSchema],
)
def devolver_item(
    uuid_item: str,
    dados: AchadoPerdidoDevolverSchema,
    request: Request,
    db: Session = Depends(get_db),
    operador: OperadorModel = Depends(get_current_active_operator),
):
    """Registra a devolução do item ao hóspede/responsável com documento obrigatório."""
    item = db.query(AchadoPerdidoModel).filter(AchadoPerdidoModel.uuid_item == uuid_item).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item de achados e perdidos não encontrado.",
        )

    if item.status != "ENCONTRADO":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Item {item.codigo_item} não pode ser devolvido pois já está com status {item.status}.",
        )

    item.status = "DEVOLVIDO"
    item.retirado_por = dados.retirado_por
    item.documento_retirada = dados.documento_retirada
    if dados.observacoes:
        item.observacoes = dados.observacoes
    item.devolvido_em = datetime.utcnow()

    _registrar_auditoria(
        db=db,
        operador=operador,
        acao="DEVOLVER_ACHADO_PERDIDO",
        registro_id=item.uuid_item,
        detalhes={
            "codigo_item": item.codigo_item,
            "retirado_por": dados.retirado_por,
        },
        request=request,
    )

    db.commit()
    db.refresh(item)
    return EnvelopeResponse(success=True, data=item, error=None)


@router.patch(
    "/{uuid_item}/descartar",
    response_model=EnvelopeResponse[AchadoPerdidoResponseSchema],
)
def descartar_item(
    uuid_item: str,
    dados: AchadoPerdidoDescartarSchema,
    request: Request,
    db: Session = Depends(get_db),
    operador: OperadorModel = Depends(get_current_active_operator),
):
    """Marca o item como descartado/doado. Operação restrita a GERENTE ou ADMIN (OWASP A01)."""
    if operador.cargo not in ("GERENTE", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas GERENTE ou ADMIN podem descartar itens de achados e perdidos.",
        )

    item = db.query(AchadoPerdidoModel).filter(AchadoPerdidoModel.uuid_item == uuid_item).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item de achados e perdidos não encontrado.",
        )

    if item.status != "ENCONTRADO":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Item {item.codigo_item} não pode ser descartado pois já está com status {item.status}.",
        )

    item.status = "DESCARTADO"
    item.observacoes = f"Descarte/Doação: {dados.motivo}"
    item.descartado_em = datetime.utcnow()

    _registrar_auditoria(
        db=db,
        operador=operador,
        acao="DESCARTAR_ACHADO_PERDIDO",
        registro_id=item.uuid_item,
        detalhes={
            "codigo_item": item.codigo_item,
            "motivo": dados.motivo,
        },
        request=request,
    )

    db.commit()
    db.refresh(item)
    return EnvelopeResponse(success=True, data=item, error=None)
