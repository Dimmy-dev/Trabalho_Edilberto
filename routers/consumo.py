"""
ROUTER DE CATÁLOGO, FRIGOBAR E CONSUMO (RF-005)
Grand Plaza Hotel Management System — Core Unificado
Diretrizes: regras/back.md e OWASP Top 10 (A04 Insecure Design - Snapshot de Preço)
"""

import json
from decimal import Decimal
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from database import get_db
from models import (
    ItemServicoModel,
    ConsumoModel,
    HospedagemModel,
    OperadorModel,
    AuditLogModel
)
from schemas import (
    ItemServicoResponseSchema,
    ConsumoCreateSchema,
    ConsumoEstornoSchema,
    ConsumoResponseSchema,
    ExtratoHospedagemSchema,
    EnvelopeResponse
)
from routers.auth import get_current_active_operator, require_role

router = APIRouter(tags=["Consumo & Frigobar (RF-005)"])

@router.get("/api/v1/itens-servicos", response_model=EnvelopeResponse[List[ItemServicoResponseSchema]])
def listar_catalogo(
    categoria: Optional[str] = Query(None, description="Filtrar por FRIGOBAR, RESTAURANTE, LAVANDERIA, SERVICO_QUARTO"),
    db: Session = Depends(get_db)
):
    """Lista os itens de frigobar e serviços disponíveis no catálogo oficial do hotel."""
    query = db.query(ItemServicoModel).filter(ItemServicoModel.is_ativo == 1)

    if categoria:
        query = query.filter(ItemServicoModel.categoria == categoria.strip().upper())

    itens = query.order_by(ItemServicoModel.categoria.asc(), ItemServicoModel.nome.asc()).all()

    return {
        "success": True,
        "data": [
            {
                "uuid_publico": i.uuid_publico,
                "codigo": i.codigo,
                "nome": i.nome,
                "categoria": i.categoria,
                "preco_unitario": float(i.preco_unitario),
                "descricao": i.descricao,
                "is_ativo": i.is_ativo
            }
            for i in itens
        ],
        "error": None
    }

@router.post("/api/v1/consumos", response_model=EnvelopeResponse[ConsumoResponseSchema], status_code=status.HTTP_201_CREATED)
def registrar_consumo(
    payload: ConsumoCreateSchema,
    request: Request,
    db: Session = Depends(get_db),
    operador: OperadorModel = Depends(get_current_active_operator)
):
    """Lança um item de consumo em tempo real vinculado a uma estadia ativa."""
    hospedagem = db.query(HospedagemModel).filter_by(
        uuid_publico=payload.uuid_hospedagem,
        status="ATIVA"
    ).first()

    if not hospedagem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hospedagem ativa não localizada para este lançamento."
        )

    item = db.query(ItemServicoModel).filter_by(
        uuid_publico=payload.uuid_item_servico,
        is_ativo=1
    ).first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item do catálogo não localizado ou inativo."
        )

    preco_unitario = Decimal(str(item.preco_unitario))
    qtd = Decimal(str(payload.quantidade))
    valor_total = preco_unitario * qtd

    novo_consumo = ConsumoModel(
        id_hospedagem=hospedagem.id,
        id_item_servico=item.id,
        id_operador=operador.id,
        quantidade=payload.quantidade,
        preco_unitario_aplicado=preco_unitario,
        valor_total=valor_total,
        observacoes=payload.observacoes,
        status="CONFIRMADO"
    )
    db.add(novo_consumo)

    log = AuditLogModel(
        id_operador=operador.id,
        acao="LANCAMENTO_CONSUMO",
        tabela_afetada="tb_consumos",
        registro_id=novo_consumo.uuid_publico,
        detalhes_json=json.dumps({
            "quarto": hospedagem.acomodacao.numero if hospedagem.acomodacao else "-",
            "item": item.nome,
            "quantidade": payload.quantidade,
            "total": float(valor_total)
        }),
        ip_origem=request.client.host if request.client else None
    )
    db.add(log)
    db.commit()
    db.refresh(novo_consumo)

    return {
        "success": True,
        "data": {
            "uuid_publico": novo_consumo.uuid_publico,
            "uuid_hospedagem": hospedagem.uuid_publico,
            "quarto_numero": hospedagem.acomodacao.numero if hospedagem.acomodacao else "-",
            "item_nome": item.nome,
            "item_codigo": item.codigo,
            "item_categoria": item.categoria,
            "quantidade": novo_consumo.quantidade,
            "preco_unitario_aplicado": float(novo_consumo.preco_unitario_aplicado),
            "valor_total": float(novo_consumo.valor_total),
            "status": novo_consumo.status,
            "motivo_estorno": None,
            "operador_nome": operador.nome,
            "created_at": novo_consumo.created_at
        },
        "error": None
    }

@router.get("/api/v1/consumos/extrato/{uuid_hospedagem}", response_model=EnvelopeResponse[ExtratoHospedagemSchema])
def extrato_consumo(
    uuid_hospedagem: str,
    db: Session = Depends(get_db),
    operador: OperadorModel = Depends(get_current_active_operator)
):
    """Retorna o extrato completo de consumo discriminado de uma hospedagem."""
    hospedagem = db.query(HospedagemModel).filter_by(uuid_publico=uuid_hospedagem).first()
    if not hospedagem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hospedagem não localizada."
        )

    consumos = db.query(ConsumoModel).filter_by(
        id_hospedagem=hospedagem.id
    ).order_by(ConsumoModel.created_at.desc()).all()

    total_confirmado = sum(
        float(c.valor_total) for c in consumos if c.status == "CONFIRMADO"
    )

    lista_itens = []
    for c in consumos:
        lista_itens.append({
            "uuid_publico": c.uuid_publico,
            "uuid_hospedagem": hospedagem.uuid_publico,
            "quarto_numero": hospedagem.acomodacao.numero if hospedagem.acomodacao else "-",
            "item_nome": c.item_servico.nome if c.item_servico else "-",
            "item_codigo": c.item_servico.codigo if c.item_servico else "-",
            "item_categoria": c.item_servico.categoria if c.item_servico else "-",
            "quantidade": c.quantidade,
            "preco_unitario_aplicado": float(c.preco_unitario_aplicado),
            "valor_total": float(c.valor_total),
            "status": c.status,
            "motivo_estorno": c.motivo_estorno,
            "operador_nome": c.operador.nome if c.operador else "-",
            "created_at": c.created_at
        })

    return {
        "success": True,
        "data": {
            "uuid_hospedagem": hospedagem.uuid_publico,
            "quarto_numero": hospedagem.acomodacao.numero if hospedagem.acomodacao else "-",
            "quarto_categoria": hospedagem.acomodacao.categoria if hospedagem.acomodacao else "-",
            "hospede_nome": hospedagem.hospede.nome if hospedagem.hospede else "-",
            "hospede_cpf": hospedagem.hospede.cpf if hospedagem.hospede else "-",
            "data_checkin": hospedagem.data_checkin,
            "data_prevista_checkout": hospedagem.data_prevista_checkout,
            "total_consumos": total_confirmado,
            "itens": lista_itens
        },
        "error": None
    }

@router.post("/api/v1/consumos/{uuid_consumo}/estorno", response_model=EnvelopeResponse[ConsumoResponseSchema])
def estornar_consumo(
    uuid_consumo: str,
    payload: ConsumoEstornoSchema,
    request: Request,
    db: Session = Depends(get_db),
    operador_atual: OperadorModel = Depends(require_role(["ADMIN", "GERENTE"]))
):
    """Realiza o estorno seguro de um lançamento de consumo com justificativa (Apenas Gerente/Admin)."""
    consumo = db.query(ConsumoModel).filter_by(uuid_publico=uuid_consumo).first()
    if not consumo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lançamento de consumo não localizado."
        )

    if consumo.status == "ESTORNADO":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este lançamento já foi estornado anteriormente."
        )

    consumo.status = "ESTORNADO"
    consumo.motivo_estorno = payload.motivo

    log = AuditLogModel(
        id_operador=operador_atual.id,
        acao="ESTORNO_CONSUMO",
        tabela_afetada="tb_consumos",
        registro_id=consumo.uuid_publico,
        detalhes_json=json.dumps({
            "item": consumo.item_servico.nome if consumo.item_servico else "-",
            "motivo": payload.motivo,
            "valor": float(consumo.valor_total)
        }),
        ip_origem=request.client.host if request.client else None
    )
    db.add(log)
    db.commit()
    db.refresh(consumo)

    return {
        "success": True,
        "data": {
            "uuid_publico": consumo.uuid_publico,
            "uuid_hospedagem": consumo.hospedagem.uuid_publico if consumo.hospedagem else "-",
            "quarto_numero": consumo.hospedagem.acomodacao.numero if (consumo.hospedagem and consumo.hospedagem.acomodacao) else "-",
            "item_nome": consumo.item_servico.nome if consumo.item_servico else "-",
            "item_codigo": consumo.item_servico.codigo if consumo.item_servico else "-",
            "item_categoria": consumo.item_servico.categoria if consumo.item_servico else "-",
            "quantidade": consumo.quantidade,
            "preco_unitario_aplicado": float(consumo.preco_unitario_aplicado),
            "valor_total": float(consumo.valor_total),
            "status": consumo.status,
            "motivo_estorno": consumo.motivo_estorno,
            "operador_nome": operador_atual.nome,
            "created_at": consumo.created_at
        },
        "error": None
    }
