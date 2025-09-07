import uuid
import datetime
from enum import auto, StrEnum
from pydantic import BaseModel
from typing import Optional, Literal

from fastapi.encoders import jsonable_encoder
from starlette.websockets import WebSocket

from wisp.protobuf.common_pb2 import RiskLevel


class CommandRecord(BaseModel):
    input: Optional[str] = None
    output: Optional[str] = None
    risk_level: str = RiskLevel.Normal


class JMSState(BaseModel):
    id: str
    activate_review: Optional[bool] = None
    new_dialogue: Optional[bool] = None


class Conversation(BaseModel):
    id: str


class MessageType(StrEnum):
    message = auto()
    finish = auto()


class ChatGPTMessage(BaseModel):
    content: str
    id: uuid.UUID | str
    parent: Optional[uuid.UUID]
    create_time: Optional[datetime.datetime]
    type: MessageType = MessageType.message
    role: Literal['system', 'user', 'assistant'] = 'user'


class AskResponseType(StrEnum):
    waiting = auto()
    reject = auto()
    message = auto()
    error = auto()
    finish = auto()


class ResponseMeta(BaseModel):
    activate_review: bool = False


class AskResponse(BaseModel):
    type: AskResponseType
    conversation_id: Optional[str] = None
    message: Optional[ChatGPTMessage] = None
    system_message: str = None
    meta: ResponseMeta = ResponseMeta()

# TODO 肯定要删掉这个函数
async def reply(websocket: WebSocket, response: BaseModel):
    try:
        await websocket.send_json(jsonable_encoder(response))
    except Exception as e:
        print(f'Websocket send error: {e}')
