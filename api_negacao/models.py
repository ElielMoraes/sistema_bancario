from pydantic import BaseModel

class NegacaoRequest(BaseModel):
    id_transacao: str
    motivo: str