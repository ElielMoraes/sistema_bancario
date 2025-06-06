from pydantic import BaseModel
from datetime import datetime

class AnaliseFraudeRequest(BaseModel):
    id_transacao: str
    id_cartao: str
    id_usuario: str
    valor: float
    data_transacao: datetime
    local_transacao: str

class RegraML(BaseModel):
    nome_regra: str
    parâmetros: str