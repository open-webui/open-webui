import logging
from datetime import datetime
from json import dumps, loads
from operator import itemgetter
from time import sleep
from typing import Callable, Iterable, Literal, Optional
from uuid import uuid4

import requests
import tiktoken
from config import SRC_LOG_LEVELS
from openai import OpenAI
from openai.types import EmbeddingCreateParams
from openai.types.batch import Batch
from openai.types.file_object import FileObject
from tenacity import retry, stop_after_attempt, wait_exponential

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])
TEXT_LENGTH_THRESHOLD_FOR_BATCH_API: int = 500_000
MAX_CHUNK_SIZE_PER_REQUEST: int = 2048
BATCH_REQUEST_COMPLETION_WINDOW: Literal["24h"] = "24h"
TOKEN_LIMIT_PER_BATCH: int = (
    1_000_000  # Basic TPM for Tier 1, assuming one batch is processed per minute
)
BATCH_RETRIEVE_WAIT_INTERVAL: int = 60
TENAICITY_RETRY_ATTEMPTS: int = 5
TENAICITY_WAIT_MIN: int = 4
TENAICITY_WAIT_MAX: int = 10
TENAICITY_WAIT_MULTIPLIER: int = 1
FALLBACK_ENCODING: str = "cl100k_base"
FALLBACK_TOKEN_COUNTER: Callable[[str], int] = lambda text: len(text) // 4  # noqa: E731


def _print_with_time(msg: str) -> None:
    log.info(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def _get_token_count(model: str) -> Callable[[str], int]:
    # Get the token count function for the model, or a rough estimate if not available
    try:
        func = tiktoken.encoding_for_model(model)
        return FALLBACK_TOKEN_COUNTER
    except Exception as e:
        log.exception(e)

    try:
        func: tiktoken.Encoding = tiktoken.get_encoding(FALLBACK_ENCODING)
        return lambda text: len(func.encode(text))

    except Exception as e:
        log.exception(e)

    return lambda text: int(len(text) / 4)  # rough estimate


def _texts_iterator(lst: list[str], chunk_size: int) -> Iterable[tuple[int, list[str]]]:
    # Yield chunks of texts, along with the index of the first text in the chunk
    # This is used to keep track of the order of the embeddings
    for i in range(0, len(lst), chunk_size):
        yield i, lst[i : i + chunk_size]


def _request_iterator(
    texts: list[str],
    model: str,
    uuid: str,
    batch_idx: int,
    chunk_size: int = MAX_CHUNK_SIZE_PER_REQUEST,
) -> Iterable[bytes]:
    # Yield individual requests for a chunk of texts
    # Each request is a JSON-encoded dictionary with the custom_id, method, url, and body
    # The custom_id is used to order the embeddings
    for request_idx, texts in _texts_iterator(texts, chunk_size):
        yield (
            dumps({
                "custom_id": f"batch_{uuid}_{batch_idx}_{request_idx}",
                "method": "POST",
                "url": "/v1/embeddings",
                "body": EmbeddingCreateParams(model=model, input=texts),
            }).encode()
        )


def _batch_iterator(
    texts: list[str],
    model: str,
    uuid: str,
    token_limit: int,
    chunk_size: int = MAX_CHUNK_SIZE_PER_REQUEST,
) -> Iterable[tuple[int, bytes]]:
    current_request: list[str] = []
    current_tokens = 0
    batch_idx: int = 0
    text2tokens: Callable[[str], int] = _get_token_count(model)
    for text in texts:
        tokens: int = text2tokens(text)
        if current_tokens + tokens > token_limit:
            yield (
                batch_idx,
                b"\n".join(
                    _request_iterator(
                        current_request, model, uuid, batch_idx, chunk_size
                    )
                ),
            )
            batch_idx += 1
            current_request = [text]
            current_tokens = tokens
        else:
            current_request.append(text)
            current_tokens += tokens
    if current_request:
        yield (
            batch_idx,
            b"\n".join(
                _request_iterator(current_request, model, uuid, batch_idx, chunk_size)
            ),
        )


@retry(
    stop=stop_after_attempt(TENAICITY_RETRY_ATTEMPTS),
    wait=wait_exponential(
        multiplier=TENAICITY_WAIT_MULTIPLIER,
        min=TENAICITY_WAIT_MIN,
        max=TENAICITY_WAIT_MAX,
    ),
)
def _process_one_batch(
    client: OpenAI,
    uuid: str,
    batch_idx: int,
    batch: bytes,
    completion_window: Literal["24h"],
    wait_interval: int,
) -> list[list[float]]:
    # Process a single batch of requests
    # This function creates a batch job, waits for it to complete, and returns the embeddings
    # The embeddings are sorted by the custom_id, which includes the batch index and request index
    # This ensures that the embeddings are returned in the same order as the input texts
    try:
        input_file: FileObject = client.files.create(
            file=(f"batch_{uuid}_{batch_idx}.jsonl", batch), purpose="batch"
        )
        batch_job: Batch = client.batches.create(
            input_file_id=input_file.id,
            endpoint="/v1/embeddings",
            completion_window=completion_window,
        )
        while True:
            batch_status: Batch = client.batches.retrieve(batch_job.id)
            status: Literal[
                "validating",
                "failed",
                "in_progress",
                "finalizing",
                "completed",
                "expired",
                "cancelling",
                "cancelled",
            ] = batch_status.status
            output_file_id = batch_status.output_file_id

            if output_file_id and status == "completed":
                log.info("Batch Job Completed")
                output_content: str = client.files.content(output_file_id).text
                raw_results = map(loads, output_content.strip().split("\n"))
                sorted_results = sorted(raw_results, key=itemgetter("custom_id"))
                return [
                    data["embedding"]
                    for result in sorted_results
                    for data in result["response"]["body"]["data"]
                ]

            elif status in ("failed", "expired", "cancelled"):
                raise RuntimeError(f"Batch Job Failed: {status}")

            _print_with_time(f"Batch Request Status: {status}")
            sleep(wait_interval)
    except Exception as e:
        log.exception(e)
        raise


def _request_async_embedding(
    model: str,
    texts: list[str],
    key: str,
    url: str,
    completion_window: Literal["24h"],
    wait_interval: int,
    token_limit: int,
) -> list[list[float]]:
    uuid: str = uuid4().hex
    client: OpenAI = OpenAI(api_key=key, base_url=url)
    return [
        embedding
        for batch_idx, batch in _batch_iterator(texts, model, uuid, token_limit)
        for embedding in _process_one_batch(
            client, uuid, batch_idx, batch, completion_window, wait_interval
        )
    ]


@retry(
    stop=stop_after_attempt(TENAICITY_RETRY_ATTEMPTS),
    wait=wait_exponential(
        multiplier=TENAICITY_WAIT_MULTIPLIER,
        min=TENAICITY_WAIT_MIN,
        max=TENAICITY_WAIT_MAX,
    ),
)
def _request_sync_embedding(url, key, texts, model):
    log.info("Using single processing for OpenAI embeddings")
    r = requests.post(
        f"{url}/embeddings",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        json={"input": texts, "model": model},
    )
    r.raise_for_status()
    data = r.json()
    if "data" in data:
        return [elem["embedding"] for elem in data["data"]]
    else:
        log.error(data)
        raise Exception("Something went wrong :/")


def generate_openai_batch_embeddings(
    model: str, texts: list[str], key: str, url: str = "https://api.openai.com/v1"
) -> Optional[list[list[float]]]:
    try:
        text_length: int = sum((len(text) for text in texts))
        log.info(
            f"len(texts): {len(texts)} / sum(len(text) for text in texts): {text_length}"
        )
        if text_length < TEXT_LENGTH_THRESHOLD_FOR_BATCH_API:
            log.info("Using single processing for OpenAI embeddings")
            return _request_sync_embedding(url, key, texts, model)
        else:
            log.info("Using batch processing for OpenAI embeddings")
            return _request_async_embedding(
                model,
                texts,
                key,
                url,
                BATCH_REQUEST_COMPLETION_WINDOW,
                BATCH_RETRIEVE_WAIT_INTERVAL,
                TOKEN_LIMIT_PER_BATCH,
            )

    except Exception as e:
        log.exception(e)
        return None
