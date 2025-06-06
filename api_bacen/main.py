from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import asyncpg
import uuid
import logging
import os
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://api_bacen:senha_bacen@bacen_db:5432/bacen_bancario")

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

class InstituicaoFinanceira(BaseModel):
    id_banco: str
    nome_banco: str
    codigo_banco: str
    data_cadastro: datetime

class Cliente(BaseModel):
    id_usuario: str
    nome: str
    cpf: str
    data_cadastro: datetime

class TransacaoReportada(BaseModel):
    id_instituicao: str
    valor: float
    data_transacao: datetime
    status: str

class Regulacao(BaseModel):
    nome: str
    descricao: str
    data_vigencia: datetime
    limite_valor: float

@app.get("/bacen/bancos/{codigo_banco}", response_model=InstituicaoFinanceira)
async def get_banco(codigo_banco: str):
    async with pool.acquire() as conn:
        try:
            banco = await conn.fetchrow(
                """
                SELECT id_banco, nome_banco, codigo_banco, data_cadastro 
                FROM bacen.bancos 
                WHERE codigo_banco = $1
                """,
                codigo_banco
            )
            if not banco:
                raise HTTPException(status_code=404, detail="Banco não encontrado")
            
            return InstituicaoFinanceira(**banco)
        except Exception as e:
            
            logger.error(f"Erro: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/bacen/clientes/{id_cliente}", response_model=Cliente)
async def get_cliente(id_cliente: str):
    async with pool.acquire() as conn:
        try:
            cliente = await conn.fetchrow(
                """
                SELECT id_usuario, nome, cpf, data_cadastro 
                FROM bacen.usuarios 
                WHERE id_usuario = $1
                """,
                id_cliente
            )
            if not cliente:
                raise HTTPException(status_code=404, detail="Cliente não encontrado")
            
            return Cliente(**cliente)
        except Exception as e:
          
            logger.error(f"Erro: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/bacen/transacoes")
async def registrar_transacao(transacao: TransacaoReportada):
    async with pool.acquire() as conn:
        try:
            id_transacao_reg = str(uuid.uuid4())
            await conn.execute(
                """
                INSERT INTO bacen.transacoes_reportadas (
                    id_transacao, id_instituicao, valor, data_transacao, status
                ) VALUES ($1, $2, $3, $4, $5)
                """,
                id_transacao_reg, transacao.id_instituicao, transacao.valor,
                transacao.data_transacao, transacao.status
            )
            await conn.execute(
                """
                INSERT INTO data_lake.logs_completos (data_log, log)
                VALUES ($1, $2)
                """,
                datetime.now(),
                json.dumps({
                    "event": "transacao_reportada",
                    "id_transacao": id_transacao_reg,
                    "id_instituicao": transacao.id_instituicao,
                    "valor": transacao.valor,
                    "status": transacao.status
                })
            )
            return {"id_transacao_reg": id_transacao_reg}
        except Exception as e:
            await conn.execute(
                """
                INSERT INTO data_lake.logs_completos (data_log, log)
                VALUES ($1, $2)
                """,
                datetime.now(),
                json.dumps({
                    "event": "erro_transacao_reportada",
                    "id_transacao": id_transacao_reg,
                    "error": str(e)
                })
            )
            logger.error(f"Erro: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/bacen/regras")
async def criar_regra(regra: Regulacao):
    async with pool.acquire() as conn:
        try:
            id_regra = str(uuid.uuid4())
            await conn.execute(
                """
                INSERT INTO bacen.regulacoes (
                    id_regra, nome, descricao, data_vigencia, limite_valor
                ) VALUES ($1, $2, $3, $4, $5)
                """,
                id_regra, regra.nome, regra.descricao, regra.data_vigencia, regra.limite_valor
            )
            await conn.execute(
                """
                INSERT INTO data_lake.logs_completos (data_log, log)
                VALUES ($1, $2)
                """,
                datetime.now(),
                json.dumps({
                    "event": "regra_criada",
                    "id_regra": id_regra,
                    "nome": regra.nome,
                    "limite_valor": regra.limite_valor
                })
            )
            return {"id_regra": id_regra}
        except Exception as e:
            await conn.execute(
                """
                INSERT INTO data_lake.logs_completos (data_log, log)
                VALUES ($1, $2)
                """,
                datetime.now(),
                json.dumps({
                    "event": "erro_regra_criada",
                    "id_regra": id_regra,
                    "error": str(e)
                })
            )
            logger.error(f"Erro: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))