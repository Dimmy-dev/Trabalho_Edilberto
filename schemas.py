"""
SCHEMAS PYDANTIC V2 COM VALIDAÇÃO ESTRITA DE BORDA
Grand Plaza Hotel Management System — Core Unificado (RF-001 a RF-005)
Diretrizes: regras/back.md e OWASP Top 10 (A03 Injection, A07 Broken Auth)
"""

import re
import html
from typing import Optional, List, Generic, TypeVar
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict

T = TypeVar("T")

def valida_cpf_modulo11(cpf: str) -> bool:
    """Valida o CPF brasileiro utilizando o algoritmo matemático oficial Módulo 11."""
    cpf_limpo = re.sub(r'\D', '', str(cpf or ''))
    if len(cpf_limpo) != 11 or len(set(cpf_limpo)) == 1:
        return False
    # 1º dígito verificador
    soma = sum(int(cpf_limpo[i]) * (10 - i) for i in range(9))
    digito1 = (soma * 10 % 11) % 10
    if int(cpf_limpo[9]) != digito1:
        return False
    # 2º dígito verificador
    soma = sum(int(cpf_limpo[i]) * (11 - i) for i in range(10))
    digito2 = (soma * 10 % 11) % 10
    return int(cpf_limpo[10]) == digito2


class ErrorDetail(BaseModel):
    code: str
    message: str
    field: Optional[str] = None


class EnvelopeResponse(BaseModel, Generic[T]):
    """Envelope padrão de resposta REST (Envelope Pattern)."""
    success: bool
    data: Optional[T] = None
    error: Optional[ErrorDetail] = None


# ----------------------------------------------------------------------------
# AUTENTICAÇÃO E OPERADORES (RF-003)
# ----------------------------------------------------------------------------

class LoginSchema(BaseModel):
    email: EmailStr = Field(..., description="E-mail corporativo do operador")
    senha: str = Field(..., min_length=4, description="Senha de acesso")


class OperadorCreateSchema(BaseModel):
    nome: str = Field(..., min_length=3, max_length=120)
    email: EmailStr
    cargo: str = Field("FUNCIONARIO", pattern="^(ADMIN|GERENTE|FUNCIONARIO)$")
    senha: str = Field(..., min_length=6, max_length=100)
    confirmacao_senha: Optional[str] = None

    @field_validator("nome")
    @classmethod
    def sanitizar_nome(cls, v: str) -> str:
        return html.escape(v.strip())


class OperadorStatusSchema(BaseModel):
    is_ativo: int = Field(..., ge=0, le=1)


class OperadorResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid_publico: str
    nome: str
    email: str
    cargo: str
    is_ativo: int
    is_online: bool = False
    token: Optional[str] = None
    created_at: Optional[datetime] = None


# ----------------------------------------------------------------------------
# HÓSPEDES (RF-001 / RF-002)
# ----------------------------------------------------------------------------

class HospedeCreateSchema(BaseModel):
    nome: str = Field(..., min_length=3, max_length=150)
    email: EmailStr
    cpf: str = Field(..., description="CPF válido de 11 dígitos")
    telefone: str = Field(..., min_length=10, max_length=20)
    data_nascimento: date
    observacoes: Optional[str] = Field(None, max_length=1000)

    @field_validator("nome", "observacoes")
    @classmethod
    def sanitizar_texto(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return html.escape(v.strip())
        return v

    @field_validator("cpf")
    @classmethod
    def validar_cpf(cls, v: str) -> str:
        cpf_limpo = re.sub(r'\D', '', v)
        if not valida_cpf_modulo11(cpf_limpo):
            raise ValueError("CPF inválido segundo o algoritmo do Módulo 11.")
        return cpf_limpo

    @field_validator("data_nascimento")
    @classmethod
    def validar_nascimento(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Data de nascimento não pode ser futura.")
        return v


class HospedeUpdateSchema(BaseModel):
    nome: Optional[str] = Field(None, min_length=3, max_length=150)
    email: Optional[EmailStr] = None
    telefone: Optional[str] = Field(None, min_length=10, max_length=20)
    observacoes: Optional[str] = Field(None, max_length=1000)

    @field_validator("nome", "observacoes")
    @classmethod
    def sanitizar_texto(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return html.escape(v.strip())
        return v


class HospedeResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid_publico: str
    nome: str
    email: str
    cpf: str
    telefone: str
    data_nascimento: date
    observacoes: Optional[str] = None
    is_ativo: int
    esta_hospedado: bool = False
    quarto_atual: Optional[str] = None
    created_at: Optional[datetime] = None


# ----------------------------------------------------------------------------
# ACOMODAÇÕES E HOSPEDAGENS / RACK (RF-004)
# ----------------------------------------------------------------------------

class AcomodacaoStatusSchema(BaseModel):
    status: str = Field(..., pattern="^(DISPONIVEL|OCUPADO|LIMPEZA|MANUTENCAO)$")


class HospedagemAtivaInfoSchema(BaseModel):
    uuid_hospedagem: str
    hospede_nome: str
    acompanhantes: List[str] = []
    data_checkin: datetime
    data_prevista_checkout: datetime
    tarifa_aplicada: float


class AcomodacaoResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid_publico: str
    numero: str
    categoria: str
    capacidade: int
    tarifa_base: float
    status: str
    andar: int
    descricao: Optional[str] = None
    is_ativo: int
    hospedagem_ativa: Optional[HospedagemAtivaInfoSchema] = None


class CheckinCreateSchema(BaseModel):
    uuid_acomodacao: str
    uuid_hospede: str
    data_prevista_checkout: datetime
    acompanhantes: List[str] = []
    observacoes: Optional[str] = None

    @field_validator("observacoes")
    @classmethod
    def sanitizar_obs(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return html.escape(v.strip())
        return v


class CheckoutSchema(BaseModel):
    uuid_hospedagem: str


class HospedagemResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid_publico: str
    quarto_numero: str
    quarto_categoria: str
    hospede_nome: str
    hospede_cpf: str
    data_checkin: datetime
    data_prevista_checkout: datetime
    data_checkout: Optional[datetime] = None
    status: str
    tarifa_diaria_aplicada: float
    num_diarias: Optional[int] = None
    valor_total: Optional[float] = None
    observacoes: Optional[str] = None


# ----------------------------------------------------------------------------
# CATÁLOGO DE ITENS, SERVIÇOS E CONSUMO (RF-005)
# ----------------------------------------------------------------------------

class ItemServicoResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid_publico: str
    codigo: str
    nome: str
    categoria: str
    preco_unitario: float
    descricao: Optional[str] = None
    is_ativo: int


class ConsumoCreateSchema(BaseModel):
    uuid_hospedagem: str = Field(..., description="Identificador público da estadia ativa")
    uuid_item_servico: str = Field(..., description="Identificador do produto ou serviço")
    quantidade: int = Field(1, ge=1, le=50, description="Quantidade lançada (1 a 50)")
    observacoes: Optional[str] = Field(None, max_length=255)

    @field_validator("observacoes")
    @classmethod
    def sanitizar_obs(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return html.escape(v.strip())
        return v


class ConsumoEstornoSchema(BaseModel):
    motivo: str = Field(..., min_length=5, max_length=255, description="Justificativa obrigatória para o estorno")

    @field_validator("motivo")
    @classmethod
    def sanitizar_motivo(cls, v: str) -> str:
        return html.escape(v.strip())


class ConsumoResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid_publico: str
    uuid_hospedagem: str
    quarto_numero: Optional[str] = None
    item_nome: str
    item_codigo: str
    item_categoria: str
    quantidade: int
    preco_unitario_aplicado: float
    valor_total: float
    status: str
    motivo_estorno: Optional[str] = None
    operador_nome: Optional[str] = None
    created_at: datetime


class ExtratoHospedagemSchema(BaseModel):
    uuid_hospedagem: str
    quarto_numero: str
    quarto_categoria: str
    hospede_nome: str
    hospede_cpf: str
    data_checkin: datetime
    data_prevista_checkout: datetime
    total_consumos: float
    itens: List[ConsumoResponseSchema]


# ============================================================================
# RF-006: SCHEMAS DE GOVERNANÇA E ORDENS DE MANUTENÇÃO
# ============================================================================

class OrdemServicoCreateSchema(BaseModel):
    quarto_numero: str = Field(..., min_length=1, max_length=10)
    tipo: str = Field("LIMPEZA", pattern="^(LIMPEZA|MANUTENCAO|INSPECAO)$")
    prioridade: str = Field("MEDIA", pattern="^(BAIXA|MEDIA|ALTA)$")
    descricao: str = Field(..., min_length=3, max_length=500)
    responsavel: Optional[str] = Field("Equipe de Governança", max_length=120)

class OrdemServicoConcluirSchema(BaseModel):
    observacoes_conclusao: Optional[str] = Field("Serviço concluído", max_length=500)
    responsavel_conclusao: Optional[str] = Field("Governança Geral", max_length=120)

class OrdemServicoResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid_os: str
    codigo_os: str
    quarto_numero: str
    tipo: str
    prioridade: str
    status: str
    descricao: str
    responsavel: Optional[str] = None
    observacoes_conclusao: Optional[str] = None
    criado_em: datetime
    concluido_em: Optional[datetime] = None
