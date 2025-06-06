import psycopg2
import os
from psycopg2.extras import RealDictCursor
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "dbname": "sistema_bancario",
    "user": "api_tokenizacao",
    "password": os.getenv("DB_PASSWORD", "senha_tokenizacao"),
    "host": os.getenv("DB_HOST", "db"),
    "port": "5432"
}

def get_db_connection(max_retries=5, delay=5):
    attempt = 0
    while attempt < max_retries:
        try:
            conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
            logger.info("Conexão com o banco de dados estabelecida")
            return conn
        except Exception as e:
            attempt += 1
            logger.error(f"Tentativa {attempt}/{max_retries} falhou: {str(e)}")
            if attempt == max_retries:
                raise Exception(f"Falha ao conectar após {max_retries} tentativas: {str(e)}")
            time.sleep(delay)