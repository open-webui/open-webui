import os
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict
import replicate
import logging
import asyncio

from config import AppConfig
from utils.utils import get_verified_user, get_admin_user

log = logging.getLogger(__name__)

app = FastAPI()
app.state.config = AppConfig()

# Add Replicate configuration to AppConfig
app.state.config.ENABLE_REPLICATE_API = os.environ.get("ENABLE_REPLICATE_API", "False").lower() == "true"
app.state.config.REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN", "")

# Replicate models configuration (you might want to load this from a config file or environment variable)
REPLICATE_MODELS = {
    "llama-2-70b": "meta/llama-2-70b:02e509c789964a7ea8736978a43525956ef40397be9033abf9fd2badfe68c9e3",
    "llama-3-70b": "meta/meta-llama-3.1-405b-instruct",
    # Add more models as needed
}

# Store active predictions
active_predictions: Dict[str, replicate.predictions.Prediction] = {}

class ReplicateConfigForm(BaseModel):
    enable_replicate_api: Optional[bool] = None

@app.post("/config/update")
async def update_config(form_data: ReplicateConfigForm, user=Depends(get_admin_user)):
    app.state.config.ENABLE_REPLICATE_API = form_data.enable_replicate_api
    return {"ENABLE_REPLICATE_API": app.state.config.ENABLE_REPLICATE_API}

class ReplicateChatMessage(BaseModel):
    role: str
    content: str

class ReplicateChatCompletionForm(BaseModel):
    model: str
    messages: List[ReplicateChatMessage]
    temperature: Optional[float] = 0.7
    max_length: Optional[int] = 500

async def stream_prediction(prediction_id: str):
    prediction = active_predictions[prediction_id]
    for output in prediction.output_iterator():
        yield f"data: {output}\n\n"
    yield "data: [DONE]\n\n"
    del active_predictions[prediction_id]

@app.post("/api/replicate/chat")
async def generate_replicate_chat_completion(
    form_data: ReplicateChatCompletionForm,
    background_tasks: BackgroundTasks,
    user=Depends(get_verified_user)
):
    if not app.state.config.ENABLE_REPLICATE_API:
        raise HTTPException(status_code=400, detail="Replicate API is not enabled")

    if not app.state.config.REPLICATE_API_TOKEN:
        raise HTTPException(status_code=400, detail="Replicate API token is not configured")

    if form_data.model not in REPLICATE_MODELS:
        raise HTTPException(status_code=400, detail=f"Model {form_data.model} not found")

    try:
        # Format messages for Replicate API
        prompt = ""
        for message in form_data.messages:
            prompt += f"{message.role}: {message.content}\n"
        prompt += "assistant: "

        # Create prediction
        prediction = replicate.predictions.create(
            version=REPLICATE_MODELS[form_data.model],
            input={
                "prompt": prompt,
                "temperature": form_data.temperature,
                "max_length": form_data.max_length,
            }
        )

        prediction_id = prediction.id
        active_predictions[prediction_id] = prediction

        # Return streaming response
        return StreamingResponse(stream_prediction(prediction_id), media_type="text/event-stream")

    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/replicate/cancel/{prediction_id}")
async def cancel_prediction(prediction_id: str, user=Depends(get_verified_user)):
    if prediction_id not in active_predictions:
        raise HTTPException(status_code=404, detail="Prediction not found")

    try:
        prediction = active_predictions[prediction_id]
        prediction.cancel()
        del active_predictions[prediction_id]
        return {"status": "cancelled", "prediction_id": prediction_id}
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/replicate/models")
async def get_replicate_models(user=Depends(get_verified_user)):
    if not app.state.config.ENABLE_REPLICATE_API:
        raise HTTPException(status_code=400, detail="Replicate API is not enabled")

    return {"models": list(REPLICATE_MODELS.keys())}