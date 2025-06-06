import requests
from fastapi import HTTPException

def publish_transacao_liquidada(event: dict):
    try:
        response = requests.post(
            "http://eventos:8001/eventos/transacao-liquidada",
            json=event,
            timeout=5
        )
        response.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Erro ao publicar evento: {str(e)}")