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
async def handle_transacao_iniciada(event: TransacaoIniciada):
    async with pool.acquire() as conn:
        try:
            response = session.get(
                f"http://bacen:8008/bacen/clientes/{event.id_usuario}",
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
                        "id_cliente": event.id_usuario,
                        "status": "sucesso"
                    })
                )
        except requests.RequestException as e:
            await conn.execute(
                    """
                    INSERT INTO data_lake.logs_completos (data_log, log)
                    VALUES ($1, $2)
                    """,
                    datetime.now(),
                    json.dumps({
                        "event": "erro_cliente_consulta",
                        "id_cliente": event.id_usuario,
                        "error": str(e)
                    })
                )
            raise HTTPException(status_code=400, detail="Usuário não registrado no BACEN")

    async with pool.acquire() as conn:
        try:
            
            user_exists = await conn.fetchval(
                "SELECT id_usuario FROM autenticacao.usuarios WHERE id_usuario = $1",
                event.id_usuario
            )
            if not user_exists:
                raise HTTPException(status_code=404, detail="Usuário não encontrado")

            
            card_exists = await conn.fetchval(
                "SELECT id_cartao FROM autenticacao.cartoes WHERE id_cartao = $1 AND status_cartao = 'ativo'",
                event.id_cartao
            )
            if not card_exists:
                raise HTTPException(status_code=400, detail="Cartão inválido ou inativo")

            
            await conn.execute(
                """
                INSERT INTO antifraude.transacoes (
                    id_transacao, id_cartao, id_usuario, valor, data_transacao, local_transacao, status_transacao
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                event.id_transacao, event.id_cartao, event.id_usuario, event.valor,
                event.data_transacao, event.local_transacao, event.status_transacao
            )

            
            await conn.execute(
                """
                INSERT INTO data_lake.logs_completos (data_log, log)
                VALUES ($1, $2)
                """,
                datetime.now(),
                json.dumps({"event": "transacao_iniciada", **event.dict()})
            )

            
            try:
                response = session.post(
                    "http://tokenizacao:8002/eventos/tokenizar",
                    json=event.dict(),
                    timeout=5
                )
                response.raise_for_status()

                await conn.execute(
                    """
                    INSERT INTO data_lake.logs_completos (data_log, log)
                    VALUES ($1, $2)
                    """,
                    datetime.now(),
                    json.dumps({"event": "transacao_tokenizada", "id_transacao": event.id_transacao})
                )
                return {"status": "tokenizada", "id_transacao": event.id_transacao}
            except requests.RequestException as e:
                await conn.execute(
                    """
                    INSERT INTO data_lake.logs_completos (data_log, log)
                    VALUES ($1, $2)
                    """,
                    datetime.now(),
                    json.dumps({"event": "erro_tokenizacao", "id_transacao": event.id_transacao, "error": str(e)})
                )
                raise HTTPException(status_code=500, detail=f"Erro na tokenização: {str(e)}")
        except Exception as e:
            await conn.execute(
                """
                INSERT INTO data_lake.logs_completos (data_log, log)
                VALUES ($1, $2)
                """,
                datetime.now(),
                json.dumps({"event": "erro_transacao", "id_transacao": event.id_transacao, "error": str(e)})
            )
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/eventos/transacao-autorizada")
async def handle_transacao_autorizada(event: Dict[str, Any]):
    async with pool.acquire() as conn:
        try:
            await conn.execute(
                """
                INSERT INTO autenticacao.autorizacoes (
                    id_autorizacao, id_transacao, id_cartao, valor, status_autorizacao, data_autorizacao
                ) VALUES ($1, $2, $3, $4, $5, NOW())
                """,
                f"auth_{event['id_transacao']}", event["id_transacao"], event.get("id_cartao", ""),
                event.get("valor", 0.0), "autorizada"
            )
            await conn.execute(
                """
                INSERT INTO data_lake.logs_completos (data_log, log)
                VALUES ($1, $2)
                """,
                datetime.now(),
                json.dumps({"event": "transacao_autorizada", **event})
            )
            return {"status": "autorizada", "id_transacao": event["id_transacao"]}
        except Exception as e:
            await conn.execute(
                """
                INSERT INTO data_lake.logs_completos (data_log, log)
                VALUES ($1, $2)
                """,
                datetime.now(),
                json.dumps({"event": "erro_autorizacao", "id_transacao": event.get("id_transacao", ""), "error": str(e)})
            )
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/eventos/transacao-negada")
async def handle_transacao_negada(event: Dict[str, Any]):
    async with pool.acquire() as conn:
        try:
            await conn.execute(
                """
                INSERT INTO autenticacao.negacoes (
                    id_negacao, id_transacao, motivo, data_negacao
                ) VALUES ($1, $2, $3, NOW())
                """,
                f"neg_{event['id_transacao']}", event["id_transacao"], event.get("motivo", "Não especificado")
            )
            await conn.execute(
                """
                INSERT INTO data_lake.logs_completos (data_log, log)
                VALUES ($1, $2)
                """,
                datetime.now(),
                json.dumps({"event": "transacao_negada", **event})
            )
            return {"status": "negada", "id_transacao": event["id_transacao"]}
        except Exception as e:
            await conn.execute(
                """
                INSERT INTO data_lake.logs_completos (data_log, log)
                VALUES ($1, $2)
                """,
                datetime.now(),
                json.dumps({"event": "erro_negacao", "id_transacao": event.get("id_transacao", ""), "error": str(e)})
            )
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/eventos/transacao-liquidada")
async def handle_transacao_liquidada(event: Dict[str, Any]):
    async with pool.acquire() as conn:
        try:
            await conn.execute(
                """
                INSERT INTO liquidacoes.liquidacoes (
                    id_liquidacao, id_lote, valor_total, data_liquidacao, status_liquidacao
                ) VALUES ($1, $2, $3, NOW(), $4)
                """,
                f"liq_{event['id_transacao']}", event["id_lote"], event.get("valor_total", 0.0), "concluída"
            )
            await conn.execute(
                """
                INSERT INTO data_lake.logs_completos (data_log, log)
                VALUES ($1, $2)
                """,
                datetime.now(),
                json.dumps({"event": "transacao_liquidada", **event})
            )
            return {"status": "liquidada", "id_lote": event["id_lote"]}
        except Exception as e:
            await conn.execute(
                """
                INSERT INTO data_lake.logs_completos (data_log, log)
                VALUES ($1, $2)
                """,
                datetime.now(),
                json.dumps({"event": "erro_liquidacao", "id_transacao": event.get("id_transacao", ""), "error": str(e)})
            )
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/eventos/token-gerado")
async def handle_token_gerado(event: Dict[str, Any]):
    async with pool.acquire() as conn:
        try:
            await conn.execute(
                """
                INSERT INTO tokenizacao.tokens (
                    id_token, id_cartao, valor_token, data_criacao, data_expiracao, status_token
                ) VALUES ($1, $2, $3, NOW(), $4, $5)
                """,
                event["id_token"], event["id_cartao"], event["valor_token"],
                datetime.now() + timedelta(days=30), "ativo"
            )
            await conn.execute(
                """
                INSERT INTO data_lake.logs_completos (data_log, log)
                VALUES ($1, $2)
                """,
                datetime.now(),
                json.dumps({"event": "token_gerado", **event})
            )
            return {"status": "token_gerado", "id_token": event["id_token"]}
        except Exception as e:
            await conn.execute(
                """
                INSERT INTO data_lake.logs_completos (data_log, log)
                VALUES ($1, $2)
                """,
                datetime.now(),
                json.dumps({"event": "erro_token_gerado", "id_token": event.get("id_token", ""), "error": str(e)})
            )
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/eventos/status/{id_transacao}", response_model=TransacaoStatus)
async def get_status_transacao(id_transacao: str):
    async with pool.acquire() as conn:
        try:
            status = await conn.fetchrow(
                """
                SELECT id_transacao, log->>'event' AS status, log AS detalhes, data_log AS data_atualizacao
                FROM data_lake.logs_completos
                WHERE log->>'id_transacao' = $1
                ORDER BY data_log DESC
                LIMIT 1
                """,
                id_transacao
            )
            if not status:
                raise HTTPException(status_code=404, detail="Transação não encontrada")
            return TransacaoStatus(**status)
        except Exception as e:
            logger.error(f"Erro: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))