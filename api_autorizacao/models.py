from pydantic import BaseModel
from datetime import date

class AutorizacaoRequest(BaseModel):
    id_transacao: str
    id_cartao: str
    valor: float

class Usuario(BaseModel):
    nome: str
    cpf: str

class Cartao(BaseModel):
    id_usuario: str
    numero_cartao: str
    data_validade: date

class Regra(BaseModel):
    nome_regra: str
    condicao: str
    acao: str