import json
import logging
import os
from decimal import Decimal
from typing import List, Union

import tiktoken
from fastapi import HTTPException
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from pydantic import BaseModel, ConfigDict
from tiktoken import Encoding

from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.credits import AddCreditForm, Credits
from open_webui.models.users import UserModel

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["MAIN"])


class MessageItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    role: str
    content: str


class Calculator:
    """
    Usage Calculator
    """

    _model_prefix_to_remove = ""
    _default_model_for_encoding = ""

    def __init__(self) -> None:
        self._encoder = {}
        self._model_prefix_to_remove = os.getenv("MODEL_PREFIX_TO_REMOVE", "")
        self._default_model_for_encoding = os.getenv("DEFAULT_MODEL_FOR_ENCODING", "gpt-4o")

    def get_encoder(self, model_id: str) -> Encoding:
        # remove prefix
        model_id_ops = model_id
        if self._model_prefix_to_remove:
            model_id_ops = model_id.lstrip(self._model_prefix_to_remove)
        # load from cache
        if model_id_ops in self._encoder:
            return self._encoder[model_id_ops]
        # load from tiktoken
        try:
            self._encoder[model_id_ops] = tiktoken.encoding_for_model(model_id_ops)
        except KeyError:
            return self.get_encoder(self._default_model_for_encoding)
        return self.get_encoder(model_id)

    def calculate_usage(
        self, model_id: str, messages: List[dict], response: Union[ChatCompletion, ChatCompletionChunk]
    ) -> (bool, CompletionUsage):
        try:
            # usage
            if response.usage is not None:
                return True, response.usage
            # init
            messages = [MessageItem.model_validate(message) for message in messages]
            # calculate
            encoder = self.get_encoder(model_id)
            usage = CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
            # prompt tokens
            for message in messages:
                usage.prompt_tokens += len(encoder.encode(message.content or ""))
            # completion tokens
            choices = response.choices
            if choices:
                choice = choices[0]
                if isinstance(response, ChatCompletion):
                    usage.completion_tokens = len(encoder.encode(choice.message.content or ""))
                elif isinstance(response, ChatCompletionChunk):
                    usage.completion_tokens = len(encoder.encode(choice.delta.content or ""))
            # total tokens
            usage.total_tokens = usage.prompt_tokens + usage.completion_tokens
            return False, usage
        except Exception as err:
            logger.exception("[calculate_usage] failed: %s", err)
            raise err


calculator = Calculator()


class CreditDeduct:
    """
    Deduct Credit
    """

    def __init__(self, user: UserModel, model: dict, body: dict, is_stream: bool) -> None:
        self.user = user
        self.model = model
        self.body = body
        self.is_stream = is_stream
        self.usage = CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
        self.prompt_unit_price, self.completion_unit_price = self.parse_model_price()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        prompt_price = self.prompt_unit_price * self.usage.prompt_tokens / 1000 / 1000
        completion_price = self.completion_unit_price * self.usage.completion_tokens / 1000 / 1000
        total_price = prompt_price + completion_price
        Credits.add_credit_by_user_id(
            form_data=AddCreditForm(
                user_id=self.user.id,
                amount=Decimal(-total_price),
                detail={
                    "prompt_unit_price": float(self.prompt_unit_price),
                    "completion_unit_price": float(self.completion_unit_price),
                    **self.usage.model_dump(),
                },
            )
        )
        logger.info(
            "[credit_deduct] user: %s; tokens: %d %d; cost: %s",
            self.user.id,
            self.usage.prompt_tokens,
            self.usage.completion_tokens,
            total_price,
        )

    def parse_model_price(self) -> (Decimal, Decimal):
        model_price = self.model.get("info", {}).get("price", {})
        return Decimal(model_price.get("prompt_price", "0")), Decimal(model_price.get("completion_price", "0"))

    def run(self, response: Union[dict, bytes]) -> None:
        if not isinstance(response, (dict, bytes)):
            logger.warning("[credit_deduct] response is type of %s", type(response))
            return
        # prompt messages
        messages = self.body.get("messages", [])
        if not messages:
            raise HTTPException(status_code=400, detail="prompt messages is empty")
        # stream
        if self.is_stream:
            _response = response.decode("utf-8").strip().lstrip("data: ")
            if not _response or _response.startswith("[DONE]"):
                return
            try:
                _response = json.loads(_response)
            except json.decoder.JSONDecodeError:
                logger.error("[credit_deduct] json decode error: %s", _response)
                return
            _response["object"] = "chat.completion.chunk"
            response = ChatCompletionChunk.model_validate(_response)
        else:
            response = ChatCompletion.model_validate(response)
        # usage
        is_official_usage, usage = calculator.calculate_usage(
            model_id=self.model["id"], messages=messages, response=response
        )
        if is_official_usage:
            self.usage = usage
            return
        if self.is_stream:
            self.usage.prompt_tokens = usage.prompt_tokens
            self.usage.completion_tokens += usage.completion_tokens
            self.usage.total_tokens = self.usage.prompt_tokens + self.usage.completion_tokens
            return
        self.usage = usage
