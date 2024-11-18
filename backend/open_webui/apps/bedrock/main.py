import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, List, Literal, Union, overload

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi import HTTPException
import aiohttp
from requests import Response
# Prepare AWS Signature V4 signing
from aws_requests_auth.aws_auth import AWSRequestsAuth
from botocore.credentials import Credentials
from langchain_community.chat_models import BedrockChat
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from datetime import datetime



# Configure logging
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize FastAPI app
app = FastAPI()

# CORS middleware (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to the appropriate origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration data class
class AppConfig(BaseModel):
    ENABLE_BEDROCK_API: bool = True
    BEDROCK_REGION: str = "us-east-1"
    ENABLE_MODEL_FILTER: bool = False
    MODEL_FILTER_LIST: List[str] = []

# Initialize application state
app.state.config = AppConfig()
app.state.MODELS = {}

# AWS Bedrock client initialization
def get_bedrock_client():
    try:
        bedrock_client = boto3.client(
            service_name="bedrock-runtime",
            region_name=app.state.config.BEDROCK_REGION,
        )
        return bedrock_client
    except (BotoCoreError, ClientError) as error:
        log.error(f"Failed to create Bedrock client: {error}")
        raise HTTPException(status_code=500, detail="Failed to initialize AWS Bedrock client")

# Dependency to get the Bedrock client
async def bedrock_client_dependency():
    return get_bedrock_client()

# User authentication dependencies (placeholders)
async def get_admin_user():
    # Implement your admin user authentication here
    pass

async def get_verified_user():
    # Implement your user authentication here
    pass

# Chat completion endpoint
@app.post("/chat/completions")
async def generate_chat_completion(form_data: dict, bedrock_client=Depends(bedrock_client_dependency), user=Depends(get_verified_user)):
    try:
        payload = {**form_data}
        if "metadata" in payload:
            del payload["metadata"]

        model_id = form_data.get("model")
        messages = payload["messages"]

        if not model_id:
            raise HTTPException(status_code=400, detail="Model ID not specified.")
        if not messages:
            raise HTTPException(status_code=400, detail="Messages not specified.")

        # Prepare the input text from messages
        input_text = ""
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            content = content.replace("{", "{{").replace("}", "}}")
            if role == "system":
                input_text += f"System: {content}\n"
            elif role == "assistant":
                input_text += f"Assistant: {content}\n"
            else:
                input_text += f"User: {content}\n"


        llm = BedrockChat(
            model_id=model_id,
            region_name=app.state.config.BEDROCK_REGION,        
            model_kwargs={"temperature": 0}
        )

        prompt_template = PromptTemplate(input_variables=[], template=input_text)
        chain = prompt_template | llm
        response = chain.invoke({})
        response_json = response.response_metadata
        # Construct the API response
        result = {
            "id": response_json['model_id'],
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": response_json['model_id'],
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response.content,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": response_json['usage']['prompt_tokens'],
                "completion_tokens": response_json['usage']['completion_tokens'],
                "total_tokens": response_json['usage']['total_tokens'],
            },
        }

        return result

    except (BotoCoreError, ClientError) as error:
        log.error(f"Bedrock invocation error: {error}")
        raise HTTPException(status_code=500, detail="Failed to generate completion with AWS Bedrock")
    except Exception as e:
        log.exception(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))