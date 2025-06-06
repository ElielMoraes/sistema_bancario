from fastapi import FastAPI, HTTPException
import api_eventos.models as models
import api_eventos.database as database
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504])
session.mount("http://", HTTPAdapter(max_retries=retries))

@app.post("/eventos/transacao-iniciada")
async def handle_transacao_iniciada(event: models.TransacaoIniciada):
    try:
        response = session.get(
            f"http://bacen:8008/bacen/clientes/{event.id_usuario}",
            timeout=5
        )
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Erro ao consultar BACEN: {str(e)}")
        raise HTTPException(status_code=400, detail="Usuário não registrado no BACEN")

    try:
        with database.get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id_usuario FROM autenticacao.usuarios WHERE id_usuario = %s",
                    (event.id_usuario,)
                )
                if not cursor.fetchone():
                    raise HTTPException(status_code=404, detail="Usuário não encontrado")
                cursor.execute(
                    "SELECT id_cartao FROM autenticacao.cartoes WHERE id_cartao = %s AND status_cartao = 'ativo'",
                    (event.id_cartao,)
                )
                if not cursor.fetchone():
                    raise HTTPException(status_code=400, detail="Cartão inválido ou inativo")
                cursor.execute(
                    "INSERT INTO eventos.transacao_status (id_transacao, status, detalhes, data_atualizacao) VALUES (%s, %s, %s, NOW())",
                    (event.id_transacao, "iniciada", event.dict())
                )
                try:
                    response = session.post(
                        "http://tokenizacao:8002/eventos/tokenizar",
                        json=event.dict(),
                        timeout=5
                    )
                    response.raise_for_status()
                    cursor.execute(
                        "UPDATE eventos.transacao_status SET status = %s, data_atualizacao = NOW() WHERE id_transacao = %s",
                        ("tokenizada", event.id_transacao)
                    )
                except requests.RequestException as e:
                    cursor.execute(
                        "UPDATE eventos.transacao_status SET status = %s, data_atualizacao = NOW() WHERE id_transacao = %s",
                        ("erro", event.id_transacao)
                    )
                    conn.commit()
                    logger.error(f"Erro na tokenização: {str(e)}")
                    raise HTTPException(status_code=500, detail=f"Erro na tokenização: {str(e)}")
                conn.commit()
                return {"status": "tokenizada", "id_transacao": event.id_transacao}
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro de validação: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/eventos/transacao-autorizada")
async def handle_transacao_autorizada(event: models.TransacaoAutorizada):
    try:
        with database.get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO eventos.transacao_status (id_transacao, status, detalhes, data_atualizacao) VALUES (%s, %s, %s, NOW()) ON CONFLICT (id_transacao) DO UPDATE SET status = %s, detalhes = %s, data_atualizacao = NOW()",
                    (event.id_transacao, "autorizada", event.dict(), "autorizada", event.dict())
                )
                conn.commit()
                logger.info(f"Transação {event.id_transacao} autorizada")
                return {"status": "autorizada", "id_transacao": event.id_transacao}
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao processar transação autorizada: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/eventos/transacao-negada")
async def handle_transacao_negada(event: models.TransacaoNegada):
    try:
        with database.get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO eventos.transacao_status (id_transacao, status, detalhes, data_atualizacao) VALUES (%s, %s, %s, NOW()) ON CONFLICT (id_transacao) DO UPDATE SET status = %s, detalhes = %s, data_atualizacao = NOW()",
                    (event.id_transacao, "negada", event.dict(), "negada", event.dict())
                )
                conn.commit()
                logger.info(f"Transação {event.id_transacao} negada")
                return {"status": "negada", "id_transacao": event.id_transacao}
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao processar transação negada: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/eventos/transacao-liquidada")
async def handle_transacao_liquidada(event: models.TransacaoLiquidada):
    try:
        with database.get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO eventos.transacao_status (id_transacao, status, detalhes, data_atualizacao) VALUES (%s, %s, %s, NOW()) ON CONFLICT (id_transacao) DO UPDATE SET status = %s, detalhes = %s, data_atualizacao = NOW()",
                    (event.id_transacao, "liquidada", event.dict(), "liquidada", event.dict())
                )
                conn.commit()
                logger.info(f"Transação {event.id_transacao} liquidada")
                return {"status": "liquidada", "id_lote": event.id_lote}
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao processar transação liquidada: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/eventos/token-gerado")
async def handle_token_gerado(event: models.TokenGerado):
    try:
        with database.get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO eventos.transacao_status (id_transacao, status, detalhes, data_atualizacao) VALUES (%s, %s, %s, NOW()) ON CONFLICT (id_transacao) DO UPDATE SET status = %s, detalhes = %s, data_atualizacao = NOW()",
                    (event.id_transacao, "token_gerado", event.dict(), "token_gerado", event.dict())
                )
                conn.commit()
                logger.info(f"Token gerado para transação {event.id_transacao}")
                return {"status": "token_gerado", "id_token": event.id_token}
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao processar token gerado: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/eventos/status/{id_transacao}", response_model=models.TransacaoStatus)
async def get_status_transacao(id_transacao: str):
    try:
        with database.get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id_transacao, status, detalhes 
                    FROM eventos.transacao_status 
                    WHERE id_transacao = %s
                    """,
                    (id_transacao,)
                )
                status = cursor.fetchone()
                if not status:
                    raise HTTPException(status_code=404, detail="Transação não encontrada")
                return status
    except Exception as e:
        logger.error(f"Erro ao consultar status da transação {id_transacao}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))