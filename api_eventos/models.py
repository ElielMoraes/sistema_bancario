from pydantic import BaseModel
from datetime import datetime

class TransacaoIniciada(BaseModel):
    id_transacao: str
    id_cartao: str
    id_usuario: str
    valor: float
    local_transacao: str
    data_transacao: datetime

class TransacaoStatus(BaseModel):
    id_transacao: str
    status: str
    detalhes: dict