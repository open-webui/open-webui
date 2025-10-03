from fastapi import FastAPI, Request, APIRouter
from fastapi.routing import APIRoute
import asyncio
import httpx
import os
from pydantic import BaseModel


class CallbackPayload(BaseModel):
    path: str
    method: str
    response_content: dict
    status_code: int | None = None


CALLBACK_URL = os.environ.get("CALLBACK_URL")
CALLBACK_TOKEN = os.environ.get("CALLBACK_TOKEN")


async def send_callback(payload: CallbackPayload):
    if not CALLBACK_URL or not CALLBACK_TOKEN:
        return
    async with httpx.AsyncClient() as client:
        await client.post(
            CALLBACK_URL,
            json=payload.model_dump_json(),
            headers={"authorization": f"Bearer {CALLBACK_TOKEN}"},
        )


class CallbackRoute(APIRoute):
    def get_route_handler(self) -> callable:
        original_handler = super().get_route_handler()

        async def custom_handler(request: Request, *args, **kwargs) -> httpx.Response:
            response: httpx.Response = await original_handler(request, *args, **kwargs)
            status_code = response.status_code
            try:
                response.raise_for_status()
                response_json = await response.json()
            except httpx.HTTPError:
                response_json = {}

            _ = asyncio.create_task(
                send_callback(
                    CallbackPayload(
                        path=request.url.path,
                        method=request.method,
                        response_content=response_json,
                        status_code=status_code,
                    )
                )
            )
            return response

        return custom_handler
