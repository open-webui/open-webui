from fastapi import APIRouter, HTTPException
import requests

router = APIRouter()

RAG_SERVER_URL = "http://localhost:8001/alfred-oi/api/query"  #

@router.post("/alfred-oi/query")
async def query_rag(payload: dict):
    try:
        response = requests.post(RAG_SERVER_URL, json=payload)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

