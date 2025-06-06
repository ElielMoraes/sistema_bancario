from pydantic import BaseModel
from datetime import date

class ConsolidadoRequest(BaseModel):
    data: date

class BackupRequest(BaseModel):
    data_backup: date
    nome_arquivo: str
    tipo_banco: str