from pydantic import BaseModel
from datetime import datetime, date

class InstituicaoFinanceira(BaseModel):
    id_instituicao: str
    nome: str
    cnpj: str
    codigo_banco: str
    data_registro: datetime

class Cliente(BaseModel):
    id_cliente: str
    nome: str
    cpf: str
    data: date

class Regulacao(BaseModel):
    id_regra: str
    nome: str
    descricao: str
    data_vigencia: date
    limite_valor: float | None

class TransacaoReportada(BaseModel):
    id_transacao: str
    id_instituicao: str
    valor: float
    data_transacao: datetime
    status: str

class ChaveCriptografica(BaseModel):
    id_chave: str
    valor_chave: str
    data_criacao: datetime
    data_expiracao: datetime