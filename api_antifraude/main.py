from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import asyncpg
import jwt
import uuid
import json
import os

app = FastAPI(title="Antifraude Service")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://api_antifraude:senha_antifraude@db:5432/sistema_bancario")
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

class Transacao(BaseModel):
    id_transacao: str
    id_cartao: str
    id_usuario: str
    valor: float
    local_transacao: str
    status_transacao: str
    data_transacao: datetime

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id_usuario: str = payload.get("sub")
        if id_usuario is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
        return id_usuario
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

@app.post("/api/eventos/transacao")
async def registrar_transacao(transacao: Transacao, current_user: str = Depends(get_current_user)):
    async with pool.acquire() as conn:
        try:
            
            result = await conn.fetchrow(
                "SELECT 1 FROM autenticacao.cartoes WHERE id_cartao = $1",
                transacao.id_cartao
            )
            if not result:
                raise HTTPException(status_code=400, detail="Cartão inválido")

            
            result = await conn.fetchrow(
                "SELECT 1 FROM autenticacao.usuarios WHERE id_usuario = $1",
                transacao.id_usuario
            )
            if not result:
                raise HTTPException(status_code=400, detail="Usuário inválido")

          
            await conn.execute(
                """
                INSERT INTO antifraude.transacoes (id_transacao, id_cartao, id_usuario, valor, data_transacao, local_transacao, status_transacao)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                transacao.id_transacao,
                transacao.id_cartao,
                transacao.id_usuario,
                transacao.valor,
                transacao.data_transacao,
                transacao.local_transacao,
                transacao.status_transacao
            )

          
            score_fraude = round(float(__import__('random').random() * 100), 2)
            resultado_analise = "suspeita" if score_fraude > 70 else "segura"
            id_analise = str(uuid.uuid4())
            await conn.execute(
                """
                INSERT INTO antifraude.analise_fraude (id_analise, id_transacao, score_fraude, resultado_analise, data_analise)
                VALUES ($1, $2, $3, $4, $5)
                """,
                id_analise, transacao.id_transacao, score_fraude, resultado_analise, datetime.utcnow()
            )

           
            log = {
                "transacao_id": transacao.id_transacao,
                "evento": "transacao",
                "detalhes": f"Transação registrada com valor {transacao.valor}",
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

            return {"status": "success", "evento_id": evento_id, "mensagem": "Evento de transação registrado com sucesso."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/eventos/fraudes")
async def consultar_fraudes(
    score_minimo: Optional[float] = None,
    resultado_analise: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    async with pool.acquire() as conn:
        try:
            query = """
                SELECT af.id_analise, af.id_transacao, af.score_fraude, af.resultado_analise, af.data_analise
                FROM antifraude.analise_fraude af
                WHERE 1=1
            """
            params = []

            if score_minimo is not None:
                query += " AND af.score_fraude >= $1"
                params.append(score_minimo)
            if resultado_analise:
                query += f" AND af.resultado_analise = ${len(params) + 1}"
                params.append(resultado_analise)

            fraudes = await conn.fetch(query, *params)
            return [
                {
                    "id_analise": f["id_analise"],
                    "id_transacao": f["id_transacao"],
                    "score_fraude": f["score_fraude"],
                    "resultado_analise": f["resultado_analise"],
                    "data_analise": f["data_analise"]
                }
                for f in fraudes
            ]
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))