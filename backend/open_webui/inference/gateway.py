"""Neutral inference gateway used while the OpenDevin engine is prepared.

The previous Ollama/OpenAI provider implementations have intentionally been
removed. This module keeps a small explicit compatibility contract so that
Open WebUI's files, retrieval, tools, MCP and administration routes can still
start without silently invoking a model provider.
"""

from typing import Any

from fastapi import HTTPException, status

ENGINE_REMOVED_MESSAGE = (
    "Le moteur d’inférence OpenWebUI a été supprimé. "
    "Le moteur OpenDevin/OpenHands sera branché ultérieurement."
)


class InferenceEngineUnavailable(RuntimeError):
    """Raised by non-HTTP call sites when no inference engine is configured."""

    def __init__(self) -> None:
        super().__init__(ENGINE_REMOVED_MESSAGE)


def inference_engine_unavailable() -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=ENGINE_REMOVED_MESSAGE,
    )


class GenerateEmbedForm:
    """Legacy request shape kept until the OpenDevin adapter is installed."""

    def __init__(self, **_: Any) -> None:
        pass


async def generate_chat_completion(*_: Any, **__: Any) -> Any:
    inference_engine_unavailable()


async def embed(*_: Any, **__: Any) -> Any:
    inference_engine_unavailable()


async def embeddings(*_: Any, **__: Any) -> Any:
    inference_engine_unavailable()


async def get_all_models(*_: Any, **__: Any) -> dict[str, list[Any]]:
    raise InferenceEngineUnavailable()


async def get_all_models_responses(*_: Any, **__: Any) -> list[Any]:
    raise InferenceEngineUnavailable()


async def count_anthropic_tokens(*_: Any, **__: Any) -> int:
    raise InferenceEngineUnavailable()


async def get_anthropic_token_count_target(*_: Any, **__: Any) -> Any:
    raise InferenceEngineUnavailable()


async def get_openai_connection(*_: Any, **__: Any) -> tuple[str, str, dict[str, Any]]:
    raise InferenceEngineUnavailable()


async def publish_model_provider_request_failed(*_: Any, **__: Any) -> None:
    raise InferenceEngineUnavailable()


def _clean_proxy_headers(headers: Any) -> dict[str, Any]:
    return dict(headers)
