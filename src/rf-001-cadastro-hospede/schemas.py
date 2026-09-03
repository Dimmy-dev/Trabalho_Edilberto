import re
from datetime import date, datetime
from typing import Optional, List, Generic, TypeVar
from pydantic import BaseModel, EmailStr, Field, field_validator

T = TypeVar("T")

def validar_cpf_modulo11(cpf: str) -> bool:
    cpf_limpo = re.sub(r'\D', '', cpf)
    if len(cpf_limpo) != 11 or len(set(cpf_limpo)) == 1:
        return False
    # 1º dígito verificador
    soma = sum(int(cpf_limpo[i]) * (10 - i) for i in range(9))
    d1 = (soma * 10 % 11) % 10
    if int(cpf_limpo[9]) != d1:
        return False
    # 2º dígito verificador
    soma = sum(int(cpf_limpo[i]) * (11 - i) for i in range(10))
    d2 = (soma * 10 % 11) % 10
    return int(cpf_limpo[10]) == d2

class HospedeCreateSchema(BaseModel):
    nome: str = Field(..., min_length=3, max_length=150, description="Nome completo do hóspede", example="João da Silva")
    email: EmailStr = Field(..., description="E-mail válido", example="joao.silva@email.com")
    cpf: str = Field(..., description="CPF válido de 11 dígitos", example="12345678901")
    telefone: str = Field(..., min_length=10, max_length=20, description="Telefone com DDD", example="11999998888")
    data_nascimento: date = Field(..., description="Data de nascimento (AAAA-MM-DD)", example="1990-03-15")
    observacoes: Optional[str] = Field(None, max_length=1000, description="Preferências ou notas VIP")

    @field_validator("nome", "observacoes")
    @classmethod
    def sanitizar_texto(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        # Remove tags HTML perigosas para prevenir Stored XSS (OWASP A03)
        limpo = re.sub(r'<[^>]*>', '', v)
        return limpo.strip()

    @field_validator("cpf")
    @classmethod
    def validar_cpf(cls, v: str) -> str:
        cpf_limpo = re.sub(r'\D', '', v)
        if not validar_cpf_modulo11(cpf_limpo):
            raise ValueError("CPF inválido segundo o algoritmo módulo 11.")
        return cpf_limpo

    @field_validator("data_nascimento")
    @classmethod
    def validar_data(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("A data de nascimento não pode ser uma data futura.")
        if v.year < 1900:
            raise ValueError("Data de nascimento inválida (anterior a 1900).")
        return v

class HospedeResponseSchema(BaseModel):
    uuid_publico: str
    nome: str
    email: str
    cpf: str
    telefone: str
    data_nascimento: date
    observacoes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    message: Optional[str] = None
