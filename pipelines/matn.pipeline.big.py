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

# from utils.pipelines.main import get_last_user_message, get_last_assistant_message
from pydantic import BaseModel


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

    async def on_startup(self):
        print(f"on_startup:{__name__}")

    async def on_shutdown(self):
        print(f"on_shutdown:{__name__}")

    async def on_valves_updated(self):
        print(f"on_valves_updated:{__name__}")


    def get_last_user_message(self, messages: List[dict]) -> str:
        for message in reversed(messages):
            if message["role"] == "user":
                if isinstance(message["content"], list):
                    for item in message["content"]:
                        if item["type"] == "text":
                            return item["text"]
                return message["content"]
        return None


    def get_last_assistant_message(self, messages: List[dict]) -> str:
        for message in reversed(messages):
            if message["role"] == "assistant":
                if isinstance(message["content"], list):
                    for item in message["content"]:
                        if item["type"] == "text":
                            return item["text"]
                return message["content"]
        return None


    def get_system_message(self, messages: List[dict]) -> dict:
        for message in messages:
            if message["role"] == "system":
                return message
        return None


    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        print(f"inlet:{__name__}")
        print(f"Received body: {body}")
        print(f"User: {user}")


        # Extract the last user message
        ai_message = self.get_last_assistant_message(body["messages"])
        request = {
            "words": len(str(ai_message).split()),
            "chat_user_id": user["id"] if user else None,
            "model": body["model"]
        }
        print(ai_message)
        print(request)
        # Prepare payload for the API call
        payload = json.dumps(request)

        headers = {
            'Content-Type': 'application/json'
        }

        try:
            response = requests.post(self.valves.api_url, headers=headers, data=payload)
            response.raise_for_status()
            print(f"API Response: {response.text}")
            
            # You can process the API response here if needed
            # For now, we'll just pass the original body through
            
        except requests.exceptions.RequestException as e:
            print(f"Error calling the API: {e}")

        return body

    async def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        print(f"outlet:{__name__}")
        return body