import json
import logging
import os
from typing import List, Optional
from fastapi import Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from open_webui.config import (
    CORS_ALLOW_ORIGIN,
    RAGAS_EVAL_FILE_PATH,
    RAGAS_EVAL_LOGS_PATH,
    ENABLE_RAGAS,
    AppConfig,
)
from fastapi import (APIRouter)
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.auth  import get_admin_user, get_verified_user
#from open_webui.ragas.utils import evaluate_and_save_results_from_json, clear_qa_section
from open_webui.ragas.utils import clear_qa_section

# Créer un router pour RAGAS
router = APIRouter()

# Configuration du logger
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAGAS"])

# Configuration de l'application
app_config = AppConfig()
app_config.RAGAS_EVAL_FILE_PATH = RAGAS_EVAL_FILE_PATH
app_config.RAGAS_EVAL_LOGS_PATH = RAGAS_EVAL_LOGS_PATH
app_config.ENABLE_RAGAS = ENABLE_RAGAS

# Routes pour RAGAS
@router.get("/")
async def get_status():
    return {
        "ENABLE_RAGAS": app_config.ENABLE_RAGAS,
        "ragas_eval_file_path": app_config.RAGAS_EVAL_FILE_PATH,
        "ragas_eval_logs_path": app_config.RAGAS_EVAL_LOGS_PATH,
    }

@router.get("/config")
async def get_ragas_config():
    return {
        "ENABLE_RAGAS": app_config.ENABLE_RAGAS,
        "ragas_eval_file_path": app_config.RAGAS_EVAL_FILE_PATH,
        "ragas_eval_logs_path": app_config.RAGAS_EVAL_LOGS_PATH,
    }

@router.get("/erase_qa")
async def erase_qa():
    file_path = app_config.RAGAS_EVAL_FILE_PATH
    clear_qa_section(file_path)
    return {"message": "QA section cleared successfully"}

@router.get("/eval_config")
async def get_eval_config():
    file_path = app_config.RAGAS_EVAL_FILE_PATH
    log.info("Loading " + file_path)
    try:
        if not os.path.isfile(file_path):
            return JSONResponse(status_code=404, content={"error": "Fichier non trouvé:"+file_path})
        
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        
        return data
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

class EvalSettings(BaseModel):
    question: Optional[List[str]] = None
    ground_truth: Optional[List[str]] = None
    documentId: Optional[List[str]] = None
    modelId: Optional[List[str]] = None
    answer: Optional[List[str]] = None

@router.post("/config/update_eval")
async def update_eval_config(settings: EvalSettings):
    file_path = app_config.RAGAS_EVAL_FILE_PATH
    log.info(f"Updating {file_path} with {settings}")
    try:
        data = {}
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
        
        data.update(settings.dict())

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
        
        return {"message": "Fichier mis à jour avec succès"}
    except Exception as e:
        log.error(f"Erreur lors de la mise à jour : {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour du fichier")

class ConfigUpdateForm(BaseModel):
    ENABLE_RAGAS: bool = False
    ragas_eval_file_path: Optional[str] = None
    ragas_eval_logs_path: Optional[str] = None

@router.post("/config/update")
async def update_ragas_config(form_data: ConfigUpdateForm, user=Depends(get_admin_user)):
    log.info(f"form_data {form_data}")

    app_config.RAGAS_EVAL_FILE_PATH = (
        form_data.ragas_eval_file_path
        if form_data.ragas_eval_file_path is not None
        else app_config.RAGAS_EVAL_FILE_PATH
    )

    app_config.RAGAS_EVAL_LOGS_PATH = (
        form_data.ragas_eval_logs_path
        if form_data.ragas_eval_logs_path is not None
        else app_config.RAGAS_EVAL_LOGS_PATH
    )

    app_config.ENABLE_RAGAS = (
        form_data.ENABLE_RAGAS
        if form_data.ENABLE_RAGAS is not None
        else app_config.ENABLE_RAGAS
    )

    return {
        "ENABLE_RAGAS": app_config.ENABLE_RAGAS,
        "ragas_eval_file_path": app_config.RAGAS_EVAL_FILE_PATH,
        "ragas_eval_logs_path": app_config.RAGAS_EVAL_LOGS_PATH,
    }
'''
@router.get("/eval/ragas")
async def eval_ragas():
    file_path = app_config.RAGAS_EVAL_FILE_PATH
    output_path = app_config.RAGAS_EVAL_LOGS_PATH
    log.info("Eval Ragas " + str(file_path))
    try:
        if not os.path.isfile(file_path):
            return JSONResponse(status_code=404, content={"error": "Fichier non trouvé."})
        
        res = evaluate_and_save_results_from_json(file_path, output_path)
        return res
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
'''