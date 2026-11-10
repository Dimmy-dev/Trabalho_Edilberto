"""
ROUTER DE HOSPEDAGENS, ACOMODAÇÕES E RACK HOTELEIRO (RF-004)
Grand Plaza Hotel Management System — Core Unificado
Diretrizes: regras/back.md e OWASP Top 10 (A04 Insecure Design - Concorrência e Transações)
"""

import json
import math
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from database import get_db, DB_DIAGNOSTICS
from models import (
    AcomodacaoModel,
    HospedagemModel,
    HospedeModel,
    OperadorModel,
    AuditLogModel,
    ConsumoModel,
    ItemServicoModel
)
from schemas import (
    AcomodacaoResponseSchema,
    AcomodacaoStatusSchema,
    CheckinCreateSchema,
    CheckoutSchema,
    HospedagemResponseSchema,
    EnvelopeResponse
)
from routers.auth import get_current_active_operator

router = APIRouter(tags=["Hospedagens & Rack Hoteleiro (RF-004)"])

@router.get("/api/v1/acomodacoes", response_model=EnvelopeResponse[List[AcomodacaoResponseSchema]])
def listar_acomodacoes(
    categoria: Optional[str] = Query(None, description="Filtrar por STANDARD, LUXO, PRESIDENCIAL"),
    status_filtro: Optional[str] = Query(None, alias="status", description="Filtrar por DISPONIVEL, OCUPADO, LIMPEZA, MANUTENCAO"),
    db: Session = Depends(get_db)
):
    """
    Retorna o inventário completo de acomodações para montagem do Rack Hoteleiro.
    Enriquece acomodações ocupadas com os dados resumidos do hóspede e estadia em curso.
    """
    query = db.query(AcomodacaoModel).filter(AcomodacaoModel.is_ativo == 1)

    if categoria:
        query = query.filter(AcomodacaoModel.categoria == categoria.strip().upper())
    if status_filtro:
        query = query.filter(AcomodacaoModel.status == status_filtro.strip().upper())

    quartos = query.order_by(AcomodacaoModel.numero.asc()).all()

    resultado = []
    for q in quartos:
        hospedagem_info = None
        if q.status == "OCUPADO":
            hosp_ativa = db.query(HospedagemModel).filter(
                HospedagemModel.id_acomodacao == q.id,
                HospedagemModel.status == "ATIVA"
            ).first()
            if hosp_ativa and hosp_ativa.hospede:
                acomp_lista = []
                if hosp_ativa.acompanhantes_json:
                    try:
                        acomp_lista = json.loads(hosp_ativa.acompanhantes_json)
                    except Exception:
                        pass
                
                hospedagem_info = {
                    "uuid_hospedagem": hosp_ativa.uuid_publico,
                    "hospede_nome": hosp_ativa.hospede.nome,
                    "acompanhantes": acomp_lista,
                    "data_checkin": hosp_ativa.data_checkin,
                    "data_prevista_checkout": hosp_ativa.data_prevista_checkout,
                    "tarifa_aplicada": float(hosp_ativa.tarifa_diaria_aplicada)
                }

        resultado.append({
            "uuid_publico": q.uuid_publico,
            "numero": q.numero,
            "categoria": q.categoria,
            "capacidade": q.capacidade,
            "tarifa_base": float(q.tarifa_base),
            "status": q.status,
            "andar": q.andar,
            "descricao": q.descricao,
            "is_ativo": q.is_ativo,
            "hospedagem_ativa": hospedagem_info
        })

    return {
        "success": True,
        "data": resultado,
        "error": None
    }

@router.patch("/api/v1/acomodacoes/{uuid_quarto}/status", response_model=EnvelopeResponse[AcomodacaoResponseSchema])
def alterar_status_quarto(
    uuid_quarto: str,
    payload: AcomodacaoStatusSchema,
    request: Request,
    db: Session = Depends(get_db),
    operador: OperadorModel = Depends(get_current_active_operator)
):
    """Atualiza o status operacional do quarto (ex: após limpeza ou manutenção)."""
    quarto = db.query(AcomodacaoModel).filter_by(uuid_publico=uuid_quarto).first()
    if not quarto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Acomodação não localizada.")

    status_antigo = quarto.status
    quarto.status = payload.status

    log = AuditLogModel(
        id_operador=operador.id,
        acao="STATUS_QUARTO",
        tabela_afetada="tb_acomodacoes",
        registro_id=quarto.uuid_publico,
        detalhes_json=json.dumps({"de": status_antigo, "para": quarto.status}),
        ip_origem=request.client.host if request.client else None
    )
    db.add(log)
    db.commit()
    db.refresh(quarto)

    return {
        "success": True,
        "data": {
            "uuid_publico": quarto.uuid_publico,
            "numero": quarto.numero,
            "categoria": quarto.categoria,
            "capacidade": quarto.capacidade,
            "tarifa_base": float(quarto.tarifa_base),
            "status": quarto.status,
            "andar": quarto.andar,
            "descricao": quarto.descricao,
            "is_ativo": quarto.is_ativo,
            "hospedagem_ativa": None
        },
        "error": None
    }

@router.post("/api/v1/hospedagens/checkin", response_model=EnvelopeResponse[HospedagemResponseSchema], status_code=status.HTTP_201_CREATED)
def realizar_checkin(
    payload: CheckinCreateSchema,
    request: Request,
    db: Session = Depends(get_db),
    operador: OperadorModel = Depends(get_current_active_operator)
):
    """Realiza check-in atômico com congelamento de tarifa diária e trava contra overbooking."""
    quarto = db.query(AcomodacaoModel).filter_by(uuid_publico=payload.uuid_acomodacao).first()
    if not quarto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quarto não localizado.")

    if quarto.status != "DISPONIVEL":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Quarto {quarto.numero} não está disponível para check-in (Status atual: {quarto.status})."
        )

    hospede = db.query(HospedeModel).filter_by(uuid_publico=payload.uuid_hospede, is_ativo=1).first()
    if not hospede:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hóspede titular não localizado ou inativo.")

    total_pessoas = 1 + len(payload.acompanhantes)
    if total_pessoas > quarto.capacidade:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Quarto {quarto.numero} suporta até {quarto.capacidade} pessoa(s). Foram informadas {total_pessoas}."
        )

    nova_estadia = HospedagemModel(
        id_hospede=hospede.id,
        id_acomodacao=quarto.id,
        id_operador=operador.id,
        data_checkin=datetime.utcnow(),
        data_prevista_checkout=payload.data_prevista_checkout,
        status="ATIVA",
        tarifa_diaria_aplicada=quarto.tarifa_base,
        acompanhantes_json=json.dumps(payload.acompanhantes),
        observacoes=payload.observacoes
    )
    db.add(nova_estadia)
    quarto.status = "OCUPADO"

    log = AuditLogModel(
        id_operador=operador.id,
        acao="CHECKIN_REALIZADO",
        tabela_afetada="tb_hospedagens",
        registro_id=nova_estadia.uuid_publico,
        detalhes_json=json.dumps({
            "quarto": quarto.numero,
            "hospede": hospede.nome,
            "tarifa": float(quarto.tarifa_base)
        }),
        ip_origem=request.client.host if request.client else None
    )
    db.add(log)
    db.commit()
    db.refresh(nova_estadia)

    return {
        "success": True,
        "data": {
            "uuid_publico": nova_estadia.uuid_publico,
            "quarto_numero": quarto.numero,
            "quarto_categoria": quarto.categoria,
            "hospede_nome": hospede.nome,
            "hospede_cpf": hospede.cpf,
            "data_checkin": nova_estadia.data_checkin,
            "data_prevista_checkout": nova_estadia.data_prevista_checkout,
            "data_checkout": None,
            "status": nova_estadia.status,
            "tarifa_diaria_aplicada": float(nova_estadia.tarifa_diaria_aplicada),
            "num_diarias": None,
            "valor_total": None,
            "observacoes": nova_estadia.observacoes
        },
        "error": None
    }

@router.post("/api/v1/hospedagens/checkout", response_model=EnvelopeResponse[HospedagemResponseSchema])
def realizar_checkout(
    payload: CheckoutSchema,
    request: Request,
    db: Session = Depends(get_db),
    operador: OperadorModel = Depends(get_current_active_operator)
):
    """Encerra a estadia, calcula o total de diárias e move o quarto para LIMPEZA."""
    hospedagem = db.query(HospedagemModel).filter_by(
        uuid_publico=payload.uuid_hospedagem,
        status="ATIVA"
    ).first()

    if not hospedagem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estadia ativa não localizada para este check-out."
        )

    agora = datetime.utcnow()
    delta_segundos = max(0, (agora - hospedagem.data_checkin).total_seconds())
    diarias = max(1, math.ceil(delta_segundos / 86400))
    total_diarias = float(hospedagem.tarifa_diaria_aplicada) * diarias

    hospedagem.data_checkout = agora
    hospedagem.status = "FINALIZADA"
    hospedagem.num_diarias = diarias
    hospedagem.valor_total = total_diarias

    if hospedagem.acomodacao:
        hospedagem.acomodacao.status = "LIMPEZA"

    log = AuditLogModel(
        id_operador=operador.id,
        acao="CHECKOUT_REALIZADO",
        tabela_afetada="tb_hospedagens",
        registro_id=hospedagem.uuid_publico,
        detalhes_json=json.dumps({"diarias": diarias, "total": total_diarias}),
        ip_origem=request.client.host if request.client else None
    )
    db.add(log)
    db.commit()
    db.refresh(hospedagem)

    return {
        "success": True,
        "data": {
            "uuid_publico": hospedagem.uuid_publico,
            "quarto_numero": hospedagem.acomodacao.numero if hospedagem.acomodacao else "-",
            "quarto_categoria": hospedagem.acomodacao.categoria if hospedagem.acomodacao else "-",
            "hospede_nome": hospedagem.hospede.nome if hospedagem.hospede else "-",
            "hospede_cpf": hospedagem.hospede.cpf if hospedagem.hospede else "-",
            "data_checkin": hospedagem.data_checkin,
            "data_prevista_checkout": hospedagem.data_prevista_checkout,
            "data_checkout": hospedagem.data_checkout,
            "status": hospedagem.status,
            "tarifa_diaria_aplicada": float(hospedagem.tarifa_diaria_aplicada),
            "num_diarias": diarias,
            "valor_total": total_diarias,
            "observacoes": hospedagem.observacoes
        },
        "error": None
    }

@router.get("/api/v1/hospedagens/ativas", response_model=EnvelopeResponse[List[dict]])
def listar_hospedagens_ativas(
    db: Session = Depends(get_db),
    operador: OperadorModel = Depends(get_current_active_operator)
):
    """Retorna a lista resumida de estadias em curso para lançamentos de consumo e extrato."""
    ativas = db.query(HospedagemModel).filter_by(status="ATIVA").order_by(HospedagemModel.id_acomodacao.asc()).all()

    lista = []
    for h in ativas:
        total_consumos = sum(
            float(c.valor_total) for c in h.consumos if c.status == "CONFIRMADO"
        )
        lista.append({
            "uuid_publico": h.uuid_publico,
            "quarto_numero": h.acomodacao.numero if h.acomodacao else "-",
            "quarto_categoria": h.acomodacao.categoria if h.acomodacao else "-",
            "hospede_nome": h.hospede.nome if h.hospede else "-",
            "hospede_cpf": h.hospede.cpf if h.hospede else "-",
            "data_checkin": h.data_checkin.isoformat(),
            "data_prevista_checkout": h.data_prevista_checkout.isoformat(),
            "total_consumos": total_consumos
        })

    return {
        "success": True,
        "data": lista,
        "error": None
    }

@router.get("/api/v1/diagnostico/banco", response_model=EnvelopeResponse[dict], tags=["Sistema"])
def diagnostico_banco(db: Session = Depends(get_db)):
    """Diagnóstico unificado de integridade do banco de dados e contadores operacionais."""
    return {
        "success": True,
        "data": {
            "motor": DB_DIAGNOSTICS["engine_type"],
            "supabase_ativo": DB_DIAGNOSTICS["supabase_connected"],
            "total_quartos": db.query(AcomodacaoModel).count(),
            "hospedagens_ativas": db.query(HospedagemModel).filter_by(status="ATIVA").count(),
            "total_hospedes": db.query(HospedeModel).count(),
            "total_operadores": db.query(OperadorModel).count(),
            "total_itens_catalogo": db.query(ItemServicoModel).filter_by(is_ativo=1).count(),
            "total_consumos": db.query(ConsumoModel).count()
        },
        "error": None
    }
