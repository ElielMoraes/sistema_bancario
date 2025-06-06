from pydantic import BaseModel
from datetime import datetime

class TransacaoLote(BaseModel):
    id_transacao: str
    valor: float
    id_cartao: str
    codigo_banco: str
    data_transacao: datetime

class LoteRequest(BaseModel):
    transacoes: list[TransacaoLote]

class Ajuste(BaseModel):
    id_liquidacao: str
    valor_ajuste: float
    motivo: str