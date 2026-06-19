"""Abstracao de fila de jobs do modulo editorial.

Fatia 1: somente o modo INLINE (executa na hora, no proprio processo). Nao
depende de Redis nem de arq, entao a Fatia 1 roda e e testavel sem nenhuma
infraestrutura externa.

Fatia 2: sera adicionado o backend "arq" (fila assincrona sobre Redis, em um
worker separado), atras desta MESMA interface. A escolha vem de
EDITORIAL_JOB_BACKEND (inline|arq) e o import do arq e LAZY (so acontece quando
o backend arq e realmente selecionado), para nunca exigir Redis no modo inline.
"""

import inspect
import logging
import os
from typing import Any, Awaitable, Callable

log = logging.getLogger(__name__)


class JobQueue:
    """Interface comum. enqueue agenda a execucao de `func(*args, **kwargs)`."""

    async def enqueue(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError


class InlineJobQueue(JobQueue):
    """Executa o job imediatamente, no mesmo processo. Aceita funcoes sincronas
    ou assincronas. Ideal para desenvolvimento, testes e baixa carga."""

    async def enqueue(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        result = func(*args, **kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result


_queue_singleton: JobQueue | None = None


def get_job_queue() -> JobQueue:
    """Fabrica do backend de jobs conforme EDITORIAL_JOB_BACKEND (default: inline)."""
    global _queue_singleton
    if _queue_singleton is not None:
        return _queue_singleton

    backend = os.environ.get("EDITORIAL_JOB_BACKEND", "inline").strip().lower()
    if backend == "arq":
        # Import LAZY: so puxa arq/redis quando o backend arq e selecionado.
        from open_webui.editorial.arq_queue import ArqJobQueue  # noqa: WPS433

        log.info("Editorial job queue: backend=arq")
        _queue_singleton = ArqJobQueue()
    else:
        log.info("Editorial job queue: backend=inline")
        _queue_singleton = InlineJobQueue()
    return _queue_singleton
