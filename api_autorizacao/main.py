from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from datetime import datetime, timedelta
import asyncpg
import jwt
import uuid
import json
import os
import requests
import logging

app = FastAPI(title="Autenticação Service")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://api_autenticacao:1234@db:5432/sistema_bancario")
SECRET_KEY = os.getenv("JWT_SECRET_KEY")  
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable not set")
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

logger = logging.getLogger("autenticacao")
logging.basicConfig(level=logging.INFO)
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
    
class AuthorizationRequest(BaseModel):
    id_transacao: str
    id_cartao: str
    id_usuario: str
    valor: float

class AuthorizationResponse(BaseModel):
    id_transacao: str
    status: str
    mensagem: str

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id_usuario: str = payload.get("sub")
        if id_usuario is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
        return id_usuario
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    
async def gerar_id_autorizacao_serial(conn) -> str:
    resultado = await conn.fetchval("""
        SELECT MAX(CAST(SUBSTRING(id_autorizacao FROM '[0-9]+$') AS INTEGER))
        FROM autenticacao.autorizacoes
    """)
    proximo_id = (resultado or 0) + 1
    return f"autorizacao_{proximo_id}"

@app.post("/token")
async def login(id_usuario: str):
    token_expires = timedelta(minutes=30)
    token = jwt.encode({"sub": id_usuario, "exp": datetime.utcnow() + token_expires}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}

@app.post("/api/autorizacao", response_model=AuthorizationResponse)
async def transaction(
    id_transacao: str,
    id_cartao: str,
    id_usuario: str,
    valor: float,
    data_transacao: str,
    local_transacao: str
):
    
    async with pool.acquire() as conn:
        try:
         
            card_result = await conn.fetchrow(
                """
                SELECT status_cartao
                FROM autenticacao.cartoes 
                WHERE id_cartao = $1 AND id_usuario = $2
                """,
                id_cartao,
                id_usuario
            )
            if not card_result:
                raise HTTPException(status_code=404, detail="Cartão não encontrado")

            if card_result['status_cartao'] != 'ativo':
                raise HTTPException(status_code=400, detail="Cartão inativo")

           
            limit_result = await conn.fetchrow(
                """
                SELECT limite_disponivel 
                FROM autenticacao.limites 
                WHERE id_cartao = $1
                """,
                id_cartao
            )
            if not limit_result or limit_result['limite_disponivel'] < valor:
                status_autorizacao = "negada"
            else:
                fraud_response = requests.post(
                    "http://antifraude:8003/api/analise",
                    params={
                        "id_usuario": id_usuario,
                        "id_transacao": id_transacao,
                        "id_cartao": id_cartao,
                        "valor": valor,
                        "data_transacao": datetime.now().isoformat(),
                        "local_transacao": local_transacao
                    },
                    timeout=5
                )
                fraud_response.raise_for_status()
                fraud_result = fraud_response.json()

                data_autorizacao = datetime.now()
                status_autorizacao = "negada" if fraud_result.get('status') == 'suspeita' else "aprovada"
          
            

            id_autorizacao = await gerar_id_autorizacao_serial(conn)

            await conn.execute(
                """
                INSERT INTO autenticacao.autorizacoes 
                (id_autorizacao, id_transacao, id_cartao, valor, status_autorizacao, data_autorizacao)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                id_autorizacao,
                id_transacao,
                id_cartao,
                valor,
                status_autorizacao,
                data_autorizacao
            )

           
            if status_autorizacao == "autorizada":
                await conn.execute(
                    """
                    UPDATE autenticacao.limites 
                    SET limite_disponivel = limite_disponivel - $1
                    WHERE id_cartao = $2
                    """,
                    valor,
                    id_cartao
                )


         
            try:
                if status_autorizacao == "autorizada":
                    autorizacao_response = requests.post(
                        "http://liquidacao:8005/api/liquidacao",
                        params={
                            "id_transacao": id_transacao,
                            "valor": valor,
                        },
                        timeout=5
                    )
                else:
                    autorizacao_response = requests.post(
                        "http://negacao:8006/api/negacao",
                        params={
                            "id_transacao": id_transacao,
                            "motivo": "Transação não autorizada"
                        },
                        timeout=5
                    )
                
                autorizacao_response.raise_for_status()
                autorizacao_result = autorizacao_response.json()
            except requests.RequestException:
                
                pass

            return AuthorizationResponse(
                id_transacao=id_transacao,
                status= autorizacao_result.get('status'),
                mensagem="Transação processada com sucesso"
            )

        except Exception as e:
            logger.exception(f"Erro na autorização: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Erro na autorização: {str(e)}"
            )
