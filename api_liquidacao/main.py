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
    
class LiquidacaoRequest(BaseModel):
    id_transacao: str
    valor: float
    id_autorizacao: str

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id_usuario: str = payload.get("sub")
        if id_usuario is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
        return id_usuario
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    
async def gerar_id_lote_serial(conn) -> str:
    resultado = await conn.fetchval("""
        SELECT MAX(CAST(SUBSTRING(id_lote FROM '[0-9]+$') AS INTEGER))
        FROM liquidacoes.lotes 
    """)
    proximo_id = (resultado or 0) + 1
    return f"lote_{proximo_id}"

async def gerar_id_liquidacao_serial(conn) -> str:
    resultado = await conn.fetchval("""
        SELECT MAX(CAST(SUBSTRING(liquidacao FROM '[0-9]+$') AS INTEGER))
        FROM liquidacoes.liquidacoes 
    """)
    proximo_id = (resultado or 0) + 1
    return f"liquidacao_{proximo_id}"

@app.post("/api/liquidacao")
async def liquidacao(
    id_transacao: str,
    valor: float
):
    async with pool.acquire() as conn:
        try:
          
            async with conn.transaction():
                data_liquidacao = datetime.now()
                id_liquidacao = await gerar_id_liquidacao_serial(conn)
                
               
                current_date = data_liquidacao.date()
                lote_result = await conn.fetchrow(
                    """
                    SELECT id_lote 
                    FROM liquidacoes.lotes 
                    WHERE data_criacao = $1
                    """,
                    current_date
                )
                
                if not lote_result:
                  
                    id_lote = await gerar_id_lote_serial(conn)
                    await conn.execute(
                        """
                        INSERT INTO liquidacoes.lotes 
                        (id_lote, data_criacao, status_lote, valor_total_lote)
                        VALUES ($1, $2, $3, $4)
                        """,
                        id_lote,
                        current_date,
                        'aberto',
                        0  
                    )
                else:
                    id_lote = lote_result['id_lote']

           
                await conn.execute(
                    """
                    INSERT INTO liquidacoes.liquidacoes 
                    (id_liquidacao, id_lote, valor_total, data_liquidacao, status_liquidacao)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    id_liquidacao,
                    id_lote,
                    valor,
                    data_liquidacao,
                    'aprovada'
                )

             
                await conn.execute(
                    """
                    UPDATE liquidacoes.lotes 
                    SET valor_total = valor_total + $1
                    WHERE id_lote = $2
                    """,
                    valor,
                    id_lote
                )

                return {
                    "id_liquidacao": id_liquidacao,
                    "id_lote": id_lote,
                    "status": "aprovada",
                    "data_liquidacao": data_liquidacao.isoformat()
                }

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Erro no processamento da liquidação: {str(e)}"
            )