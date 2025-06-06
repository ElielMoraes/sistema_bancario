from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from datetime import datetime, timedelta
import asyncpg
import jwt
import uuid
import json
import os

app = FastAPI(title="Autenticação Service")

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

class Autorizacao(BaseModel):
    id_transacao: str
    id_cartao: str
    valor: float
    status_autorizacao: str
    data_autorizacao: datetime

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id_usuario: str = payload.get("sub")
        if id_usuario is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
        return id_usuario
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

@app.post("/token")
async def login(id_usuario: str):
    token_expires = timedelta(minutes=30)
    token = jwt.encode({"sub": id_usuario, "exp": datetime.utcnow() + token_expires}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}

@app.post("/api/eventos/autorizacao")
async def registrar_autorizacao(autorizacao: Autorizacao, current_user: str = Depends(get_current_user)):
    async with pool.acquire() as conn:
        try:
           
            result = await conn.fetchrow(
                "SELECT 1 FROM antifraude.transacoes WHERE id_transacao = $1",
                autorizacao.id_transacao
            )
            if not result:
                raise HTTPException(status_code=400, detail="Transação inválida")

          
            result = await conn.fetchrow(
                "SELECT 1 FROM autenticacao.cartoes WHERE id_cartao = $1",
                autorizacao.id_cartao
            )
            if not result:
                raise HTTPException(status_code=400, detail="Cartão inválido")

           
            result = await conn.fetchrow(
                "SELECT limite_disponivel FROM autenticacao.limites WHERE id_cartao = $1",
                autorizacao.id_cartao
            )
            if not result or result["limite_disponivel"] < autorizacao.valor:
                raise HTTPException(status_code=400, detail="Limite insuficiente")

          
            id_autorizacao = f"autorizacao_{uuid.uuid4()}"
            await conn.execute(
                """
                INSERT INTO autenticacao.autorizacoes (id_autorizacao, id_transacao, id_cartao, valor, status_autorizacao, data_autorizacao)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                id_autorizacao,
                autorizacao.id_transacao,
                autorizacao.id_cartao,
                autorizacao.valor,
                autorizacao.status_autorizacao,
                autorizacao.data_autorizacao
            )

            
            if autorizacao.status_autorizacao == "negada":
                await conn.execute(
                    """
                    INSERT INTO autenticacao.negacoes (id_negacao, id_transacao, motivo, data_negacao)
                    VALUES ($1, $2, $3, $4)
                    """,
                    f"negacao_{uuid.uuid4()}", autorizacao.id_transacao, "Limite excedido ou suspeita de fraude", datetime.utcnow()
                )

          
            log = {
                "transacao_id": autorizacao.id_transacao,
                "evento": "autorizacao",
                "detalhes": f"Autorização {autorizacao.status_autorizacao} para valor {autorizacao.valor}",
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

            return {"status": "success", "evento_id": evento_id, "mensagem": "Evento de autorização registrado com sucesso."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))