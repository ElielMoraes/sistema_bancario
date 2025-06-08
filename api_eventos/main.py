from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
import asyncpg
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
import json
import os
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504])
session.mount("http://", HTTPAdapter(max_retries=retries))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://api_data_lake:1234@db:5432/sistema_bancario")


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

class TransacaoIniciada(BaseModel):
    id_transacao: str
    id_cartao: str
    id_usuario: str
    valor: float
    data_transacao: str
    local_transacao: str
    status_transacao: str

class TransacaoStatus(BaseModel):
    id_transacao: str
    status: str
    detalhes: Dict[str, Any]
    data_atualizacao: datetime

@app.post("/eventos/transacao-iniciada")
async def handle_transacao_iniciada(
    id_transacao: str,
    id_cartao: str,
    id_usuario: str,
    valor: float,
    data_transacao: str,
    local_transacao: str,
    status_transacao: str
):
    async with pool.acquire() as conn:
        try:
            
            response = session.get(
                f"http://bacen:8008/bacen/clientes/{id_usuario}",
                timeout=5
            )
            response.raise_for_status()
            
           
            await conn.execute(
                """
                INSERT INTO data_lake.logs_completos (data_log, log)
                VALUES ($1, $2)
                """,
                datetime.now(),
                json.dumps({
                    "event": "cliente_consultado",
                    "id_cliente": id_usuario,
                    "status": "sucesso"
                })
            )
            
           
            auth_response = session.post(
                "http://autorizacao:8003/api/autorizacao",
                params={
                    "id_transacao": id_transacao,
                    "id_cartao": id_cartao,
                    "id_usuario": id_usuario,
                    "valor": valor
                },
                timeout=5
            )
            auth_response.raise_for_status()
            
          
            await conn.execute(
                """
                INSERT INTO data_lake.logs_completos (data_log, log)
                VALUES ($1, $2)
                """,
                datetime.now(),
                json.dumps({
                    "event": "autorizacao_solicitada",
                    "id_transacao": id_transacao
                })
            )

          
            token_response = session.post(
                "http://tokenizacao:8002/api/tokenizacao",
                params={
                    "id_transacao": id_transacao,
                    "id_cartao": id_cartao,
                    "valor": valor
                },
                timeout=5
            )
            token_response.raise_for_status()
            
        
            await conn.execute(
                """
                INSERT INTO data_lake.logs_completos (data_log, log)
                VALUES ($1, $2)
                """,
                datetime.now(),
                json.dumps({
                    "event": "tokenizacao_solicitada",
                    "id_transacao": id_transacao
                })
            )

            return {
                "status": "processando",
                "id_transacao": id_transacao
            }

        except requests.RequestException as e:
         
            await conn.execute(
                """
                INSERT INTO data_lake.logs_completos (data_log, log)
                VALUES ($1, $2)
                """,
                datetime.now(),
                json.dumps({
                    "event": "erro_processamento",
                    "id_transacao": id_transacao,
                    "error": str(e)
                })
            )
            raise HTTPException(
                status_code=500,
                detail=f"Erro no processamento da transação: {str(e)}"
            )
            