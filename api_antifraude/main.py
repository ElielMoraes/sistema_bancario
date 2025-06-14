from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
import asyncpg
import jwt
import uuid
import json
import os
import logging

app = FastAPI(title="Antifraude Service")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://api_antifraude:senha_antifraude@db:5432/sistema_bancario")
SECRET_KEY = os.getenv("JWT_SECRET_KEY")  
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable not set")
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

logger = logging.getLogger("antifraude")
logging.basicConfig(level=logging.INFO)

def gerar_id_uuid():
    return str(uuid.uuid4())

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

class FraudAnalysisRequest(BaseModel):
    id_transacao: str
    id_cartao: str
    valor: float
    data_transacao: str

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id_usuario: str = payload.get("sub")
        if id_usuario is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
        return id_usuario
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

@app.post("/api/analise")
async def transaction(
    id_usuario: str,
    id_transacao: str,
    id_cartao: str,
    valor: float,
    data_transacao: str,
    local_transacao: str
):
    async with pool.acquire() as conn:
        try:
            suspicious_factors = []
            
          
            if valor >= 10000:  
                suspicious_factors.append("valor_alto")

          
            recent_transactions = await conn.fetch(
                """
                SELECT COUNT(*) as count, SUM(valor) as total
                FROM antifraude.transacoes 
                WHERE id_cartao = $1 
                AND data_transacao >= $2
                """,
                id_cartao,
                datetime.fromisoformat(data_transacao) - timedelta(hours=1)
            )
            
            if recent_transactions[0]['count'] >= 5: 
                suspicious_factors.append("frequencia_alta")
            
            total = float(recent_transactions[0]['total'] or 0)
            if total + valor >= 15000:
                suspicious_factors.append("volume_alto_periodo")

          
            avg_transaction = await conn.fetchrow(
                """
                SELECT AVG(valor) as media
                FROM antifraude.transacoes 
                WHERE id_cartao = $1 
                AND data_transacao >= $2
                """,
                id_cartao,
                datetime.fromisoformat(data_transacao) - timedelta(days=30)
            )
            
            if avg_transaction and avg_transaction['media']:
                if valor >= (avg_transaction['media'] * 5):  
                    suspicious_factors.append("padrao_valor_anomalo")

           
            last_transaction = await conn.fetchrow(
                """
                SELECT data_transacao
                FROM antifraude.transacoes 
                WHERE id_cartao = $1 
                ORDER BY data_transacao DESC 
                LIMIT 1
                """,
                id_cartao
            )
            
            if last_transaction:
                time_diff = datetime.fromisoformat(data_transacao) - \
                           last_transaction['data_transacao']
                if time_diff.total_seconds() < 30: 
                    suspicious_factors.append("transacoes_rapidas")

           
            is_suspicious = len(suspicious_factors) >= 1  
           
            await conn.execute(
                """
                INSERT INTO antifraude.transacoes 
                (id_transacao, id_cartao, id_usuario, valor, data_transacao, status_transacao, local_transacao)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                id_transacao,
                id_cartao,
                id_usuario,
                valor,
                datetime.fromisoformat(data_transacao),
                'rejeitada' if is_suspicious else 'aprovada',
                local_transacao
            )

           
            

            id_analise = gerar_id_uuid()
          
            await conn.execute(
                """
                INSERT INTO antifraude.analise_fraude 
                (id_analise, id_transacao, resultado_analise, score_fraude, data_analise)
                VALUES ($1, $2, $3, $4, $5)
                """,
                id_analise,
                id_transacao,
                'suspeita' if is_suspicious else 'segura',
                float(len(suspicious_factors)),
                datetime.fromisoformat(data_transacao)
            )

            return {
                "id_transacao": id_transacao,
                "status": "suspeita" if is_suspicious else "normal",
                "fatores": len(suspicious_factors),
                "data_analise": datetime.now().isoformat()
            }

        except Exception as e:
            
            try:
                id_analise = gerar_id_uuid()
                await conn.execute(
                    """
                    INSERT INTO antifraude.analise_fraude 
                    (id_analise, id_transacao, resultado_analise, score_fraude, data_analise)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    id_analise,
                    id_transacao,
                    'erro',
                    0,
                    datetime.now()
                )
            
            except Exception as log_error:
                print(f"Erro ao registrar falha: {log_error}")
            logger.exception(f"Erro na aintifraude: {str(e)}")
            raise HTTPException(
                
                status_code=500,
                detail=f"Erro na análise antifraude: {str(e)}"
            )