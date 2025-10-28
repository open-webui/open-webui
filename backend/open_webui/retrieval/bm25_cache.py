from __future__ import annotations

import copy
import hashlib
import json
import threading
from collections import OrderedDict
from typing import Any, Callable, Iterable, Mapping, MutableMapping, Optional, Sequence

__all__ = ["get_or_build_bm25_retriever", "clear_cache"]


Builder = Callable[[Sequence[str], Sequence[Mapping[str, Any]], Optional[MutableMapping[str, Any]]], Any]


class _BM25LRUCache:
    """
    Cache for the lanchain BM25 retriever
    """
    def __init__(self, max_items: int = 128):
        self._max_items = max_items
        self._store: OrderedDict[str, Any] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            value = self._store.get(key)
            if value is not None:
                self._store.move_to_end(key)
            return value

    def put(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = value
            while len(self._store) > self._max_items:
                self._store.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


_cache = _BM25LRUCache(max_items=32)
_build_lock = threading.Lock()


def _json_default(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, (set, tuple)):
        return list(value)
    return str(value)


def _to_bytes(value: Any) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    try:
        return json.dumps(value, sort_keys=True, default=_json_default).encode("utf-8")
    except (TypeError, ValueError):
        return str(value).encode("utf-8")


def _compute_content_hash(texts: Sequence[str], metadatas: Sequence[Mapping[str, Any]]) -> str:
    hasher = hashlib.sha256()
    for text, metadata in zip(texts, metadatas):
        hasher.update(_to_bytes(text))
        hasher.update(b"\x00")
        hasher.update(_to_bytes(metadata))
        hasher.update(b"\x00")
    return hasher.hexdigest()


def _make_cache_key(
    collection_name: str,
    texts: Sequence[str],
    metadatas: Sequence[Mapping[str, Any]],
    bm25_params: Optional[Mapping[str, Any]],
    tokenizer_tag: str,
    chunking_params: Optional[Mapping[str, Any]],
) -> str:
    """
    This still take some time to compute the hash of all the content of the collection
    We could speed up the computation of hash if we make the assumption of a static knowledge base (collection
    """
    content_hash = _compute_content_hash(texts, metadatas)
    bm25_dump = json.dumps(bm25_params or {}, sort_keys=True, default=_json_default)
    chunk_dump = json.dumps(chunking_params or {}, sort_keys=True, default=_json_default)
    return "|".join(
        [
            collection_name or "",
            tokenizer_tag or "default",
            content_hash,
            bm25_dump,
            chunk_dump,
        ]
    )


def get_or_build_bm25_retriever(
    collection_name: str,
    texts: Iterable[str],
    metadatas: Iterable[Mapping[str, Any]],
    *,
    bm25_params: Optional[MutableMapping[str, Any]] = None,
    tokenizer_tag: str = "default",
    chunking_params: Optional[Mapping[str, Any]] = None,
    builder: Optional[Builder] = None,
):
    if builder is None:
        raise ValueError("A builder callable must be provided to build the BM25 retriever.")

    texts_list = list(texts or [])
    metadatas_list = list(metadatas or [])

    # Compute key of the retriever
    key = _make_cache_key(
        collection_name,
        texts_list,
        metadatas_list,
        bm25_params,
        tokenizer_tag,
        chunking_params,
    )

    cached = _cache.get(key)
    if cached is not None:
        return cached
        # return _clone_retriever(cached)  # cloning involve deep-copy and takes a long time - may be unsafe

    with _build_lock:
        kwargs = {"texts": texts_list, "metadatas": metadatas_list}
        if bm25_params is not None:
            kwargs["bm25_params"] = bm25_params

        retriever = builder(**kwargs)
        _cache.put(key, retriever)
        return retriever
        # return _clone_retriever(retriever) # cloning involve deep-copy and takes a long time - may be unsafe


def clear_cache() -> None:
    _cache.clear()

# Could be deleted if we return the objet and not a clone/deep-copy
def _clone_retriever(retriever: Any) -> Any:
    if hasattr(retriever, "copy"):
        copy_method = getattr(retriever, "copy")
        if callable(copy_method):
            try:
                return copy_method(deep=True)  # type: ignore[arg-type]
            except TypeError:
                return copy_method()  # type: ignore[call-arg]
    return copy.deepcopy(retriever)