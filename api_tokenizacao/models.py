from pydantic import BaseModel

class TokenRequest(BaseModel):
    id_cartao: str