from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from datetime import datetime
import asyncpg
import jwt
import uuid
import json
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Negação Service")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://api_autenticacao:1234@db:5432/sistema_bancario")
SECRET_KEY = os.getenv("JWT_SECRET_KEY")  
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable not set")
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


pool = None

@app.on_event("startup")
async def startup_event():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)

@app.on_event("shutdown")
async def shutdown_event():
    global pool
    if pool:
        await pool.close()

class NegacaoRequest(BaseModel):
    id_transacao: str
    motivo: str
    
class NegacaoRequest(BaseModel):
    id_transacao: str
    id_autorizacao: str
    motivo: str

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id_usuario: str = payload.get("sub")
        if id_usuario is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
        return id_usuario
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

@app.post("/api/negacao")
async def process_negacao(negacao: NegacaoRequest):
    async with pool.acquire() as conn:
        try:
            
            async with conn.transaction():
                data_negacao = datetime.now()
                id_negacao = str(uuid.uuid4())
                
                
                await conn.execute(
                    """
                    INSERT INTO autenticacao.negacoes 
                    (id_negacao, id_transacao, motivo, data_negacao)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    id_negacao,
                    negacao.id_autorizacao,
                    negacao.id_transacao,
                    negacao.motivo,
                    data_negacao
                )

                return {
                    "id_negacao": id_negacao,
                    "id_transacao": negacao.id_transacao,
                    "status": "negada",
                    "data_negacao": data_negacao.isoformat()
                }

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Erro no processamento da negação: {str(e)}"
            )