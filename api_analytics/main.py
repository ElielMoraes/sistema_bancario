from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import date, datetime
import asyncpg
import uuid
import logging
import os
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

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

class ConsolidadoRequest(BaseModel):
    data: date

class BackupRequest(BaseModel):
    data_backup: date
    nome_arquivo: str
    tipo_banco: str

@app.post("/analytics/consolidado")
async def criar_consolidado(request: ConsolidadoRequest):
    async with pool.acquire() as conn:
        try:
            result = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) as total_transacoes, 
                    COALESCE(SUM(valor), 0) as valor_total
                FROM data_lake.historico_transacoes
                WHERE DATE(data_transacao) = $1
                """,
                request.data
            )
            total_transacoes = result["total_transacoes"]
            valor_total = float(result["valor_total"])  

            id_consolidado = str(uuid.uuid4())
            await conn.execute(
                """
                INSERT INTO data_lake.consolidados (
                    id, data_arquivo, total_transacoes, valor_total_transacoes
                ) VALUES ($1, $2, $3, $4)
                """,
                id_consolidado, request.data, total_transacoes, valor_total
            )

            await conn.execute(
                """
                INSERT INTO data_lake.logs_completos (data_log, log)
                VALUES ($1, $2)
                """,
                datetime.now(),
                json.dumps({
                    "event": "consolidado_criado",
                    "id_consolidado": id_consolidado,
                    "data": str(request.data),
                    "total_transacoes": total_transacoes,
                    "valor_total": valor_total,
                    "status": "sucesso"
                })
            )

            return {"id_consolidado": id_consolidado, "total_transacoes": total_transacoes}
        except Exception as e:
            await conn.execute(
                """
                INSERT INTO data_lake.logs_completos (data_log, log)
                VALUES ($1, $2)
                """,
                datetime.now(),
                json.dumps({
                    "event": "erro_consolidado",
                    "data": str(request.data),
                    "error": str(e)
                })
            )
            logger.error(f"Erro: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/analytics/backup")
async def criar_backup(backup: BackupRequest):
    async with pool.acquire() as conn:
        try:
            id_backup = str(uuid.uuid4())
            await conn.execute(
                """
                INSERT INTO data_lake.backup_sistema (
                    id_backup, data_backup, nome_arquivo, tipo_banco
                ) VALUES ($1, $2, $3, $4)
                """,
                id_backup, backup.data_backup, backup.nome_arquivo, backup.tipo_banco
            )

            await conn.execute(
                """
                INSERT INTO data_lake.logs_completos (data_log, log)
                VALUES ($1, $2)
                """,
                datetime.now(),
                json.dumps({
                    "event": "backup_criado",
                    "id_backup": id_backup,
                    "nome_arquivo": backup.nome_arquivo,
                    "tipo_banco": backup.tipo_banco,
                    "status": "sucesso"
                })
            )

            return {"id_backup": id_backup}
        except Exception as e:
            await conn.execute(
                """
                INSERT INTO data_lake.logs_completos (data_log, log)
                VALUES ($1, $2)
                """,
                datetime.now(),
                json.dumps({
                    "event": "erro_backup",
                    "id_backup": id_backup,
                    "error": str(e)
                })
            )
            logger.error(f"Erro: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))