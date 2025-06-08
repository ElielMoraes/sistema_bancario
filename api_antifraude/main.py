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
async def analyze_transaction(transaction: FraudAnalysisRequest):
    async with pool.acquire() as conn:
        try:
            suspicious_factors = []
            
          
            if transaction.valor >= 10000:  
                suspicious_factors.append("valor_alto")

          
            recent_transactions = await conn.fetch(
                """
                SELECT COUNT(*) as count, SUM(valor) as total
                FROM antifraude.transacoes 
                WHERE id_cartao = $1 
                AND data_transacao >= $2
                """,
                transaction.id_cartao,
                datetime.fromisoformat(transaction.data_transacao) - timedelta(hours=1)
            )
            
            if recent_transactions[0]['count'] >= 5: 
                suspicious_factors.append("frequencia_alta")
            
            if recent_transactions[0]['total'] and \
               recent_transactions[0]['total'] + transaction.valor >= 15000:  
                suspicious_factors.append("volume_alto_periodo")

          
            avg_transaction = await conn.fetchrow(
                """
                SELECT AVG(valor) as media
                FROM antifraude.transacoes 
                WHERE id_cartao = $1 
                AND data_transacao >= $2
                """,
                transaction.id_cartao,
                datetime.fromisoformat(transaction.data_transacao) - timedelta(days=30)
            )
            
            if avg_transaction and avg_transaction['media']:
                if transaction.valor >= (avg_transaction['media'] * 5):  
                    suspicious_factors.append("padrao_valor_anomalo")

           
            last_transaction = await conn.fetchrow(
                """
                SELECT data_transacao
                FROM antifraude.transacoes 
                WHERE id_cartao = $1 
                ORDER BY data_transacao DESC 
                LIMIT 1
                """,
                transaction.id_cartao
            )
            
            if last_transaction:
                time_diff = datetime.fromisoformat(transaction.data_transacao) - \
                           last_transaction['data_transacao']
                if time_diff.total_seconds() < 30: 
                    suspicious_factors.append("transacoes_rapidas")

           
            await conn.execute(
                """
                INSERT INTO antifraude.transacoes 
                (id_transacao, id_cartao, valor, data_transacao)
                VALUES ($1, $2, $3, $4)
                """,
                transaction.id_transacao,
                transaction.id_cartao,
                transaction.valor,
                datetime.fromisoformat(transaction.data_transacao)
            )

           
            is_suspicious = len(suspicious_factors) >= 1  

          
            await conn.execute(
                """
                INSERT INTO antifraude.analises 
                (id_transacao, status, fatores_suspeitos, data_analise)
                VALUES ($1, $2, $3, $4)
                """,
                transaction.id_transacao,
                'suspeita' if is_suspicious else 'normal',
                json.dumps(suspicious_factors) if suspicious_factors else None,
                datetime.now()
            )

            return {
                "id_transacao": transaction.id_transacao,
                "status": "suspeita" if is_suspicious else "normal",
                "fatores": suspicious_factors,
                "data_analise": datetime.now().isoformat()
            }

        except Exception as e:
          
            await conn.execute(
                """
                INSERT INTO antifraude.analises 
                (id_transacao, status, erro, data_analise)
                VALUES ($1, $2, $3, $4)
                """,
                transaction.id_transacao,
                'erro',
                str(e),
                datetime.now()
            )
            
            raise HTTPException(
                status_code=500,
                detail=f"Erro na análise antifraude: {str(e)}"
            )