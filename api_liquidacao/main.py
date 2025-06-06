from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from datetime import datetime
import asyncpg
import jwt
import uuid
import json
import os

app = FastAPI(title="Liquidações Service")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://api_liquidacoes:1234@db:5432/sistema_bancario")
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

class Liquidacao(BaseModel):
    id_lote: str
    id_liquidacao: str
    valor_total: float
    status_liquidacao: str
    data_liquidacao: datetime

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id_usuario: str = payload.get("sub")
        if id_usuario is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
        return id_usuario
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

@app.post("/api/eventos/liquidacao")
async def registrar_liquidacao(liquidacao: Liquidacao, current_user: str = Depends(get_current_user)):
    async with pool.acquire() as conn:
        try:
            
            result = await conn.fetchrow(
                "SELECT 1 FROM liquidacoes.lotes WHERE id_lote = $1",
                liquidacao.id_lote
            )
            if not result:
                raise HTTPException(status_code=400, detail="Lote inválido")

            
            await conn.execute(
                """
                INSERT INTO liquidacoes.liquidacoes (id_liquidacao, id_lote, valor_total, data_liquidacao, status_liquidacao)
                VALUES ($1, $2, $3, $4, $5)
                """,
                liquidacao.id_liquidacao,
                liquidacao.id_lote,
                liquidacao.valor_total,
                liquidacao.data_liquidacao,
                liquidacao.status_liquidacao
            )

            
            log = {
                "liquidacao_id": liquidacao.id_liquidacao,
                "evento": "liquidacao",
                "detalhes": f"Liquidação registrada para lote {liquidacao.id_lote} com valor {liquidacao.valor_total}",
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

            return {"status": "success", "evento_id": evento_id, "mensagem": "Evento de liquidação registrado com sucesso."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))