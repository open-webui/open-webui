# backend/open_webui/routers/local.py
import logging
import base64
import struct
import numpy as np
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from open_webui.models.embeddings import OpenAIEmbeddingRequest, OpenAIEmbeddingResponse, EmbeddingObject, UsageObject
from open_webui.utils.auth import get_verified_user, UserModel
from open_webui.config import RAG_EMBEDDING_MODEL_AUTO_UPDATE # PersistentConfig
from open_webui.env import DEVICE_TYPE, RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE # PersistentConfig
from open_webui.retrieval.utils import get_model_path

log = logging.getLogger(__name__)
router = APIRouter()
loaded_local_models = {}

def get_sentence_transformer_model_internal(model_id: str): # Renamed to avoid conflict
    if model_id not in loaded_local_models:
        try:
            from sentence_transformers import SentenceTransformer
            log.info(f"Loading local SentenceTransformer model: {model_id}")
            resolved_model_path = get_model_path(model_id, RAG_EMBEDDING_MODEL_AUTO_UPDATE.value)
            loaded_local_models[model_id] = SentenceTransformer(
                resolved_model_path,
                device=DEVICE_TYPE.value, # Access PersistentConfig via .value
                trust_remote_code=RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE.value # Access PersistentConfig via .value
            )
            log.info(f"Successfully loaded local model: {model_id} from {resolved_model_path}")
        except Exception as e:
            log.exception(f"Failed to load local ST model {model_id}: {e}")
            raise RuntimeError(f"Could not load local model '{model_id}'. Error: {e}")
    return loaded_local_models[model_id]

async def generate_local_embeddings_v1(
    request_obj: Request, # Kept for consistency, may not be used if request_data has all info
    request_data: OpenAIEmbeddingRequest,
    user: UserModel # Kept for consistency
) -> OpenAIEmbeddingResponse:
    log.info(f"Local v1 embeddings request for model '{request_data.model}'")
    model_id_to_load = request_data.model

    try:
        model = get_sentence_transformer_model_internal(model_id_to_load)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    inputs_to_embed = [request_data.input] if isinstance(request_data.input, str) else request_data.input
    if not inputs_to_embed:
        raise HTTPException(status_code=400, detail="Input list/string cannot be empty.")

    try:
        # type: ignore
        raw_embeddings_np = model.encode(inputs_to_embed, convert_to_tensor=False) 
        # Ensure raw_embeddings is List[List[float]]
        if isinstance(raw_embeddings_np, np.ndarray):
            if raw_embeddings_np.ndim == 1: # Single embedding case
                 raw_embeddings = [raw_embeddings_np.tolist()]
            else: # Batch embedding case
                 raw_embeddings = [arr.tolist() for arr in raw_embeddings_np]
        elif isinstance(raw_embeddings_np, list) and all(isinstance(arr, np.ndarray) for arr in raw_embeddings_np):
            raw_embeddings = [arr.tolist() for arr in raw_embeddings_np]
        else:
            log.error(f"Unexpected embedding output format from model {model_id_to_load}: {type(raw_embeddings_np)}")
            raise HTTPException(status_code=500, detail=f"Embedding generation failed due to unexpected output format.")

    except Exception as e:
        log.exception(f"Error during local model encoding for {model_id_to_load}: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding generation failed. Error: {e}")

    output_embeddings_data: List[EmbeddingObject] = []
    prompt_tokens_total = 0 # Placeholder, or use tiktoken

    for index, vector in enumerate(raw_embeddings):
        embedding_vector = vector
        if request_data.encoding_format == "base64":
            byte_array = bytearray()
            for val in embedding_vector:
                byte_array.extend(struct.pack('f', val))
            embedding_vector = base64.b64encode(byte_array).decode('utf-8')
        
        output_embeddings_data.append(EmbeddingObject(embedding=embedding_vector, index=index))
        # Optional: Calculate prompt_tokens_total

    return OpenAIEmbeddingResponse(
        data=output_embeddings_data,
        model=request_data.model,
        usage=UsageObject(prompt_tokens=prompt_tokens_total, total_tokens=prompt_tokens_total)
    )

@router.post("/v1/embeddings", response_model=OpenAIEmbeddingResponse)
async def local_v1_embeddings_direct_endpoint( # Renamed for clarity
    request_data: OpenAIEmbeddingRequest,
    request: Request, # FastAPI Request object
    user=Depends(get_verified_user)
):
    return await generate_local_embeddings_v1(request, request_data, user) 