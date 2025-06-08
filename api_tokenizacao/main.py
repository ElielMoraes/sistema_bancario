from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from datetime import datetime, timedelta
import asyncpg
import jwt
import uuid
import json
import os
import secrets
import hashlib

app = FastAPI(title="Tokenização Service")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://api_tokenizacao:1234@db:5432/sistema_bancario")
SECRET_KEY = os.getenv("JWT_SECRET_KEY") 
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

class Tokenizacao(BaseModel):
    id_token: str
    id_cartao: str
    valor_token: str
    data_criacao: datetime
    data_expiracao: datetime
    status_token: str
    
class TokenizationRequest(BaseModel):
    id_transacao: str
    id_cartao: str
    valor: float

class TokenResponse(BaseModel):
    id_transacao: str
    token: str
    data_expiracao: str
    status: str

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id_usuario: str = payload.get("sub")
        if id_usuario is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
        return id_usuario
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

@app.post("/api/tokenizacao", response_model=TokenResponse)
async def transaction(
    id_transacao: str,
    id_cartao: str,
    valor: float
):
    async with pool.acquire() as conn:
        try:
     
            id_token = str(uuid.uuid4())
            raw_token = f"{id_transacao}{id_cartao}{secrets.token_hex(16)}"
            valor_token = hashlib.sha256(raw_token.encode()).hexdigest()[:32]
            
        
            data_criacao = datetime.now()
            data_expiracao = data_criacao + timedelta(minutes=15)
            
         
            await conn.execute(
                """
                INSERT INTO tokenizacao.tokens 
                (id_token, id_cartao, valor_token, data_criacao, data_expiracao, status_token)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                id_token,
                id_cartao,
                valor_token,
                data_criacao,
                data_expiracao,
                'ativo'
            )
            
        
            await conn.execute(
                """
                INSERT INTO tokenizacao.manutencao_tokens 
                (id_manutencao, id_token, acao, data_manutencao)
                VALUES ($1, $2, $3, $4)
                """,
                str(uuid.uuid4()),
                id_token,
                'criacao',
                data_criacao
            )

            return TokenResponse(
                id_transacao=id_transacao,
                token=valor_token,
                data_expiracao=data_expiracao.isoformat(),
                status="criado"
            )

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Erro na tokenização: {str(e)}"
            )