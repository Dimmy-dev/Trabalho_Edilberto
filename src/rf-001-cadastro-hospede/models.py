import uuid
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Date, Text, DateTime, Boolean, ForeignKey, Numeric, JSON
from sqlalchemy.orm import relationship
from database import Base

class HospedeModel(Base):
    __tablename__ = "tb_hospedes"

    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    uuid_publico = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), index=True)
    nome = Column(String(150), nullable=False, index=True)
    email = Column(String(180), unique=True, nullable=False, index=True)
    cpf = Column(String(11), unique=True, nullable=False, index=True)
    telefone = Column(String(20), nullable=False)
    data_nascimento = Column(Date, nullable=False)
    observacoes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    sessoes = relationship("SessaoModel", back_populates="hospede", cascade="all, delete-orphan")
    reservas = relationship("ReservaModel", back_populates="hospede")

class SessaoModel(Base):
    __tablename__ = "tb_sessoes"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    id_hospede = Column(BigInteger, ForeignKey("tb_hospedes.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    hospede = relationship("HospedeModel", back_populates="sessoes")

class QuartoModel(Base):
    __tablename__ = "tb_quartos"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    numero = Column(String(10), unique=True, nullable=False)
    categoria = Column(String(50), nullable=False)
    valor_diaria = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), default="DISPONIVEL", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    reservas = relationship("ReservaModel", back_populates="quarto")

class ReservaModel(Base):
    __tablename__ = "tb_reservas"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    uuid_publico = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    id_hospede = Column(BigInteger, ForeignKey("tb_hospedes.id", ondelete="RESTRICT"), nullable=False)
    id_quarto = Column(BigInteger, ForeignKey("tb_quartos.id", ondelete="RESTRICT"), nullable=False)
    data_checkin = Column(Date, nullable=False)
    data_checkout = Column(Date, nullable=False)
    valor_total = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), default="PENDENTE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    hospede = relationship("HospedeModel", back_populates="reservas")
    quarto = relationship("QuartoModel", back_populates="reservas")
    pagamentos_pix = relationship("PagamentoPixModel", back_populates="reserva")

class PagamentoPixModel(Base):
    __tablename__ = "tb_pagamentos_pix"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    uuid_publico = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    id_reserva = Column(BigInteger, ForeignKey("tb_reservas.id", ondelete="RESTRICT"), nullable=True)
    pix_webhook_id = Column(String(100), unique=True, nullable=True)
    end_to_end_id = Column(String(50), nullable=True)
    valor = Column(Numeric(10, 2), nullable=False)
    qr_code_copia_cola = Column(Text, nullable=False)
    qr_code_url = Column(String(500), nullable=True)
    qr_expires_at = Column(DateTime, nullable=False)
    status = Column(String(20), default="PENDING", nullable=False)
    pago_em = Column(DateTime, nullable=True)
    payload_bruto = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    reserva = relationship("ReservaModel", back_populates="pagamentos_pix")

class AuditLogModel(Base):
    __tablename__ = "tb_audit_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    id_hospede = Column(BigInteger, ForeignKey("tb_hospedes.id", ondelete="SET NULL"), nullable=True)
    acao = Column(String(60), nullable=False)
    tabela_afetada = Column(String(50), nullable=False)
    registro_id = Column(BigInteger, nullable=True)
    dados_anteriores = Column(JSON, nullable=True)
    dados_novos = Column(JSON, nullable=True)
    ip_origem = Column(String(45), nullable=False)
    user_agent = Column(String(300), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
