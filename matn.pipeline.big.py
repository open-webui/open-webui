"""
title: Chat Management Pipeline
author: open-webui
date: 2024-05-30
version: 1.0
license: MIT
description: A pipeline that manages chat using an external API.
requirements: requests
"""

from typing import List, Optional
import os
import uuid
import requests
import json
from logging import getLogger, basicConfig, INFO
from pydantic import BaseModel

# Configure logging
basicConfig(level=INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = getLogger(__name__)

class Pipeline:
    class Valves(BaseModel):
        pipelines: List[str] = []
        api_url: str = "http://127.0.0.1:5000/dashboard/manage_chat"

    def __init__(self):
        self.type = "filter"
        self.name = "Chat Management Filter"
        self.valves = self.Valves(
            **{
                "pipelines": ["*"],
                "api_url": os.getenv("CHAT_MANAGEMENT_API_URL", "http://127.0.0.1:5000/dashboard/manage_chat"),
            }
        )
        logger.info(f"Initialized {self.name} with API URL: {self.valves.api_url}")

    async def on_startup(self):
        logger.info("on_startup called")

    async def on_shutdown(self):
        logger.info("on_shutdown called")

    async def on_valves_updated(self):
        logger.info("on_valves_updated called")

    def get_last_user_message(self, messages: List[dict]) -> str:
        logger.debug("Retrieving last user message")
        for message in reversed(messages):
            if message["role"] == "user":
                if isinstance(message["content"], list):
                    for item in message["content"]:
                        if item["type"] == "text":
                            logger.debug(f"Found last user message: {item['text']}")
                            return item["text"]
                logger.debug(f"Found last user message: {message['content']}")
                return message["content"]
        return None

    def get_last_assistant_message(self, messages: List[dict]) -> str:
        logger.debug("Retrieving last assistant message")
        for message in reversed(messages):
            if message["role"] == "assistant":
                if isinstance(message["content"], list):
                    for item in message["content"]:
                        if item["type"] == "text":
                            logger.debug(f"Found last assistant message: {item['text']}")
                            return item["text"]
                logger.debug(f"Found last assistant message: {message['content']}")
                return message["content"]
        return None

    def get_system_message(self, messages: List[dict]) -> dict:
        logger.debug("Retrieving system message")
        for message in messages:
            if message["role"] == "system":
                logger.debug(f"Found system message: {message}")
                return message
        return None

    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        logger.info(f"inlet called")
        logger.debug(f"Received body: {body}")
        logger.debug(f"User: {user}")

        # Extract the last assistant message
        ai_message = self.get_last_assistant_message(body["messages"])
        request = {
            "words": len(str(ai_message).split()),
            "chat_user_id": user["id"] if user else None,
            "model": body["model"]
        }
        logger.debug(f"AI message: {ai_message}")
        logger.debug(f"Request payload: {request}")

        # Prepare payload for the API call
        payload = json.dumps(request)
        headers = {'Content-Type': 'application/json'}

        try:
            response = requests.post(self.valves.api_url, headers=headers, data=payload)
            response.raise_for_status()
            logger.info(f"API Response: {response.text}")
            
            # You can process the API response here if needed
            # For now, we'll just pass the original body through

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling the API: {e}")

        return body

    async def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        logger.info(f"outlet called")
        return body