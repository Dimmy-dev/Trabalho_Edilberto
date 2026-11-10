"""
MODELOS ORM SQLALCHEMY UNIFICADOS
Grand Plaza Hotel Management System — Core Unificado (RF-001 a RF-005)
Diretrizes: regras/DB.md, regras/back.md e OWASP Top 10

Entidades Mapeadas:
1. OperadorModel (tb_operadores): Funcionários, Gerentes e Administradores (RF-003)
2. SessaoModel (tb_sessoes): Sessões ativas de login via HttpOnly cookies (OWASP A07)
3. HospedeModel (tb_hospedes): Cadastro e gestão de hóspedes (RF-001/RF-002)
4. AcomodacaoModel (tb_acomodacoes): Quartos do hotel e status do Rack (RF-004)
5. HospedagemModel (tb_hospedagens): Check-in, estadia e faturamento (RF-004)
6. ItemServicoModel (tb_itens_servicos): Catálogo de frigobar e serviços (RF-005)
7. ConsumoModel (tb_consumos): Lançamentos de consumo em tempo real e estornos (RF-005)
8. AuditLogModel (tb_audit_logs): Trilha imutável de auditoria LGPD
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    BigInteger,
    Integer,
    String,
    Text,
    Date,
    DateTime,
    Numeric,
    ForeignKey
)
from sqlalchemy.orm import relationship
from database import Base

class OperadorModel(Base):
    """Representa os operadores e funcionários que acessam o sistema administrativo."""
    __tablename__ = "tb_operadores"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    uuid_publico = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), index=True)
    nome = Column(String(120), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    senha_hash = Column(String(255), nullable=False)
    cargo = Column(String(50), nullable=False, default="FUNCIONARIO", index=True)
    is_ativo = Column(Integer, nullable=False, default=1, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sessoes = relationship("SessaoModel", back_populates="operador", cascade="all, delete-orphan")
    logs = relationship("AuditLogModel", back_populates="operador")
    hospedagens = relationship("HospedagemModel", back_populates="operador")
    consumos = relationship("ConsumoModel", back_populates="operador")

    def __repr__(self):
        return f"<Operador {self.nome} ({self.cargo})>"


class SessaoModel(Base):
    """Representa a sessão ativa autenticada via HttpOnly Cookie seguro."""
    __tablename__ = "tb_sessoes"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    id_operador = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("tb_operadores.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    ip_origem = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    is_active = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    operador = relationship("OperadorModel", back_populates="sessoes")


class HospedeModel(Base):
    """Representa os hóspedes cadastrados no hotel (RF-001 e RF-002)."""
    __tablename__ = "tb_hospedes"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    uuid_publico = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), index=True)
    nome = Column(String(150), nullable=False)
    email = Column(String(180), unique=True, nullable=False, index=True)
    cpf = Column(String(11), unique=True, nullable=False, index=True)
    telefone = Column(String(20), nullable=False)
    data_nascimento = Column(Date, nullable=False)
    observacoes = Column(Text, nullable=True)
    is_ativo = Column(Integer, nullable=False, default=1, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hospedagens = relationship("HospedagemModel", back_populates="hospede")

    def __repr__(self):
        return f"<Hospede {self.nome} - CPF: {self.cpf}>"


class AcomodacaoModel(Base):
    """
    Representa as unidades habitacionais (quartos) do hotel (RF-004).
    Categorias: 'STANDARD', 'LUXO', 'PRESIDENCIAL'.
    Status operacional: 'DISPONIVEL', 'OCUPADO', 'MANUTENCAO', 'LIMPEZA'.
    """
    __tablename__ = "tb_acomodacoes"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    uuid_publico = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), index=True)
    numero = Column(String(10), unique=True, nullable=False, index=True)
    categoria = Column(String(30), nullable=False, index=True)
    capacidade = Column(Integer, nullable=False, default=2)
    tarifa_base = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), nullable=False, default="DISPONIVEL", index=True)
    andar = Column(Integer, nullable=False, default=1)
    descricao = Column(String(255), nullable=True)
    is_ativo = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hospedagens = relationship("HospedagemModel", back_populates="acomodacao")

    def __repr__(self):
        return f"<Acomodacao {self.numero} ({self.status})>"


class HospedagemModel(Base):
    """
    Representa a estadia do hóspede vinculada à acomodação (RF-004).
    Status: 'ATIVA', 'FINALIZADA', 'CANCELADA'.
    """
    __tablename__ = "tb_hospedagens"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    uuid_publico = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), index=True)
    id_hospede = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("tb_hospedes.id", ondelete="RESTRICT"), nullable=False, index=True)
    id_acomodacao = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("tb_acomodacoes.id", ondelete="RESTRICT"), nullable=False, index=True)
    id_operador = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("tb_operadores.id", ondelete="SET NULL"), nullable=True)
    
    data_checkin = Column(DateTime, nullable=False, default=datetime.utcnow)
    data_prevista_checkout = Column(DateTime, nullable=False)
    data_checkout = Column(DateTime, nullable=True)
    
    status = Column(String(20), nullable=False, default="ATIVA", index=True)
    num_diarias = Column(Integer, nullable=True)
    tarifa_diaria_aplicada = Column(Numeric(10, 2), nullable=False)
    valor_total = Column(Numeric(10, 2), nullable=True)
    acompanhantes_json = Column(Text, nullable=True)
    observacoes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hospede = relationship("HospedeModel", back_populates="hospedagens")
    acomodacao = relationship("AcomodacaoModel", back_populates="hospedagens")
    operador = relationship("OperadorModel", back_populates="hospedagens")
    consumos = relationship("ConsumoModel", back_populates="hospedagem", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Hospedagem {self.uuid_publico} - Quarto {self.id_acomodacao} ({self.status})>"


class ItemServicoModel(Base):
    """
    Catálogo de Itens de Frigobar e Serviços de Quarto (RF-005).
    Categorias: 'FRIGOBAR', 'RESTAURANTE', 'LAVANDERIA', 'SERVICO_QUARTO'.
    """
    __tablename__ = "tb_itens_servicos"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    uuid_publico = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), index=True)
    codigo = Column(String(20), unique=True, nullable=False, index=True)
    nome = Column(String(120), nullable=False)
    categoria = Column(String(40), nullable=False, index=True)
    preco_unitario = Column(Numeric(10, 2), nullable=False)
    descricao = Column(String(255), nullable=True)
    is_ativo = Column(Integer, nullable=False, default=1, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    consumos = relationship("ConsumoModel", back_populates="item_servico")

    def __repr__(self):
        return f"<ItemServico {self.codigo} - {self.nome} (R$ {self.preco_unitario})>"


class ConsumoModel(Base):
    """
    Lançamento de Consumo de Frigobar ou Serviço em Tempo Real (RF-005).
    Armazena snapshot imutável de preco_unitario_aplicado para auditoria fiscal e contábil.
    """
    __tablename__ = "tb_consumos"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    uuid_publico = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), index=True)
    id_hospedagem = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("tb_hospedagens.id", ondelete="RESTRICT"), nullable=False, index=True)
    id_item_servico = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("tb_itens_servicos.id", ondelete="RESTRICT"), nullable=False, index=True)
    id_operador = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("tb_operadores.id", ondelete="SET NULL"), nullable=True)
    
    quantidade = Column(Integer, nullable=False, default=1)
    preco_unitario_aplicado = Column(Numeric(10, 2), nullable=False)
    valor_total = Column(Numeric(10, 2), nullable=False)
    observacoes = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="CONFIRMADO", index=True) # 'CONFIRMADO', 'ESTORNADO'
    motivo_estorno = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hospedagem = relationship("HospedagemModel", back_populates="consumos")
    item_servico = relationship("ItemServicoModel", back_populates="consumos")
    operador = relationship("OperadorModel", back_populates="consumos")

    def __repr__(self):
        return f"<Consumo {self.uuid_publico} Item={self.id_item_servico} Total=R${self.valor_total}>"


class AuditLogModel(Base):
    """Trilha imutável de auditoria em conformidade com a LGPD e governança corporativa."""
    __tablename__ = "tb_audit_logs"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    uuid_publico = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), index=True)
    id_operador = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("tb_operadores.id", ondelete="SET NULL"), nullable=True)
    acao = Column(String(50), nullable=False)
    tabela_afetada = Column(String(50), nullable=False)
    registro_id = Column(String(36), nullable=False)
    detalhes_json = Column(Text, nullable=True)
    ip_origem = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    operador = relationship("OperadorModel", back_populates="logs")


class OrdemServicoModel(Base):
    """Representa uma Ordem de Serviço de Limpeza, Manutenção ou Inspeção (RF-006)."""
    __tablename__ = "tb_ordens_servico"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    uuid_os = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), index=True)
    codigo_os = Column(String(20), unique=True, nullable=False, index=True)
    quarto_numero = Column(String(10), nullable=False, index=True)
    tipo = Column(String(20), nullable=False, default="LIMPEZA")
    prioridade = Column(String(10), nullable=False, default="MEDIA")
    status = Column(String(20), nullable=False, default="PENDENTE")
    descricao = Column(Text, nullable=False)
    responsavel = Column(String(120), nullable=True)
    observacoes_conclusao = Column(Text, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    concluido_em = Column(DateTime, nullable=True)
