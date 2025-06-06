from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from datetime import datetime
import asyncpg
import jwt
import uuid
import json
import os

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

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id_usuario: str = payload.get("sub")
        if id_usuario is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
        return id_usuario
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

@app.post("/api/eventos/tokenizar")
async def registrar_tokenizacao(tokenizacao: Tokenizacao, current_user: str = Depends(get_current_user)):
    async with pool.acquire() as conn:
        try:
            
            result = await conn.fetchrow(
                "SELECT 1 FROM autenticacao.cartoes WHERE id_cartao = $1",
                tokenizacao.id_cartao
            )
            if not result:
                raise HTTPException(status_code=400, detail="Cartão inválido")

           
            await conn.execute(
                """
                INSERT INTO tokenizacao.tokens (id_token, id_cartao, valor_token, data_criacao, data_expiracao, status_token)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                tokenizacao.id_token,
                tokenizacao.id_cartao,
                tokenizacao.valor_token,
                tokenizacao.data_criacao,
                tokenizacao.data_expiracao,
                tokenizacao.status_token
            )

            
            await conn.execute(
                """
                INSERT INTO tokenizacao.manutencao_tokens (id_manutencao, id_token, acao, data_manutencao)
                VALUES ($1, $2, $3, $4)
                """,
                str(uuid.uuid4()), tokenizacao.id_token, "criacao", datetime.utcnow()
            )

            
            log = {
                "token_id": tokenizacao.id_token,
                "evento": "tokenizacao",
                "detalhes": f"Token criado para cartão {tokenizacao.id_cartao}",
                "status": "sucesso"
            }
            result = await conn.fetchrow(
                """
                INSERT INTO data_lake.logs_completos (data_log, log)
                VALUES ($1, $2)
                RETURNING id_log
                """,
                datetime.utcnow().date(), json.dumps(log)
            )
            evento_id = f"log_{result['id_log']}"

            return {"status": "success", "evento_id": evento_id, "mensagem": "Evento de tokenização registrado com sucesso."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))