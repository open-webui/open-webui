from __future__ import annotations

import copy
import hashlib
import json
import logging
import pickle
import threading
from collections import OrderedDict
from itertools import zip_longest
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, MutableMapping, Optional, Sequence

from open_webui.config import CACHE_DIR

__all__ = [
    "get_or_build_bm25_retriever",
    "clear_cache",
    "invalidate_cache",
    "invalidate_collection_cache",
    "get_cache_metadata",
    "compute_collection_digest",
]


log = logging.getLogger(__name__)


Builder = Callable[[Sequence[str], Sequence[Mapping[str, Any]], Optional[MutableMapping[str, Any]]], Any]


class _BM25LRUCache:
    """
    Cache for the langchain BM25 retriever
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

    def delete(self, key: str) -> bool:
        with self._lock:
            return self._store.pop(key, None) is not None

    def delete_prefix(self, prefix: str) -> int:
        with self._lock:
            keys_to_remove = [key for key in self._store if key.startswith(prefix)]
            for key in keys_to_remove:
                self._store.pop(key, None)
            return len(keys_to_remove)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


_cache = _BM25LRUCache(max_items=32)
_build_lock = threading.Lock()

_PERSISTENT_CACHE_DIR = Path(CACHE_DIR) / "retrieval" / "bm25"
_PERSISTENT_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _json_default(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, (set, tuple)):
        return list(value)
    return str(value)


def _make_cache_key(
    collection_name: str,
    bm25_params: Optional[Mapping[str, Any]],
    tokenizer_tag: str,
    chunking_params: Optional[Mapping[str, Any]],
) -> str:
    bm25_dump = json.dumps(bm25_params or {}, sort_keys=True, default=_json_default)
    chunk_dump = json.dumps(chunking_params or {}, sort_keys=True, default=_json_default)
    return "|".join(
        [
            collection_name or "",
            tokenizer_tag or "default",
            bm25_dump,
            chunk_dump,
        ]
    )


def compute_collection_digest(
    documents: Sequence[Any],
    metadatas: Sequence[Mapping[str, Any]],
) -> str:
    """Return a deterministic hash for the provided collection payload."""

    hasher = hashlib.sha256()

    for document, metadata in zip_longest(documents or [], metadatas or [], fillvalue=None):
        if document is None:
            document = ""
        if not isinstance(document, str):
            document = str(document)

        hasher.update(b"\x00")
        hasher.update(document.encode("utf-8"))

        metadata_dump = json.dumps(metadata or {}, sort_keys=True, default=_json_default)
        hasher.update(b"\x00")
        hasher.update(metadata_dump.encode("utf-8"))

    return hasher.hexdigest()


def _sanitize_collection_name(collection_name: str) -> str:
    sanitized = "".join(
        ch if ch.isalnum() or ch in {"-", "_", "."} else "_"
        for ch in (collection_name or "default")
    ).strip("._")
    if not sanitized:
        sanitized = "default"
    return sanitized[:64]


def _cache_file_path(collection_name: str, key: str) -> Path:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    prefix = _sanitize_collection_name(collection_name)
    return _PERSISTENT_CACHE_DIR / f"{prefix}-{digest}.pkl"


def _metadata_file_path(collection_name: str, key: str) -> Path:
    return _cache_file_path(collection_name, key).with_suffix(".meta.json")


def _load_from_disk(collection_name: str, key: str) -> Any | None:
    path = _cache_file_path(collection_name, key)
    if not path.exists():
        return None
    try:
        with path.open("rb") as file:
            payload = pickle.load(file)
        if isinstance(payload, dict) and "retriever" in payload:
            return payload["retriever"]
        return payload
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("Failed to load BM25 retriever cache from %s: %s", path, exc)
        try:
            path.unlink()
        except OSError:
            pass
        return None


def _load_metadata_from_disk(collection_name: str, key: str) -> dict[str, Any] | None:
    meta_path = _metadata_file_path(collection_name, key)
    if meta_path.exists():
        try:
            with meta_path.open("r", encoding="utf-8") as file:
                metadata = json.load(file)
            if isinstance(metadata, dict):
                metadata.setdefault("key", key)
                return metadata
        except (OSError, json.JSONDecodeError) as exc:  # pragma: no cover - defensive
            log.warning("Failed to load BM25 retriever cache metadata %s: %s", meta_path, exc)

    path = _cache_file_path(collection_name, key)
    if not path.exists():
        return None

    try:
        with path.open("rb") as file:
            payload = pickle.load(file)
        if isinstance(payload, dict):
            metadata = {k: v for k, v in payload.items() if k != "retriever"}
            metadata.setdefault("key", key)
            return metadata
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("Failed to read BM25 cache metadata from %s: %s", path, exc)
    return None


def _save_to_disk(
    collection_name: str,
    key: str,
    retriever: Any,
    *,
    metadata: Optional[Mapping[str, Any]] = None,
) -> None:
    path = _cache_file_path(collection_name, key)
    tmp_path = path.with_suffix(".tmp")
    meta_path = _metadata_file_path(collection_name, key)
    tmp_meta_path = meta_path.with_suffix(".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tmp_path.open("wb") as file:
            pickle.dump({"key": key, "retriever": retriever}, file, protocol=pickle.HIGHEST_PROTOCOL)
        tmp_path.replace(path)

        metadata_payload: dict[str, Any] = {"key": key}
        if metadata:
            metadata_payload.update(metadata)
        with tmp_meta_path.open("w", encoding="utf-8") as file:
            json.dump(metadata_payload, file, sort_keys=True, default=_json_default)
        tmp_meta_path.replace(meta_path)
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("Failed to persist BM25 retriever cache to %s: %s", path, exc)
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        try:
            if tmp_meta_path.exists():
                tmp_meta_path.unlink()
        except OSError:
            pass


def _delete_from_disk(collection_name: str, key: str) -> bool:
    path = _cache_file_path(collection_name, key)
    meta_path = _metadata_file_path(collection_name, key)
    removed = False
    try:
        path.unlink()
        removed = True
    except FileNotFoundError:
        pass
    except OSError as exc:  # pragma: no cover - defensive
        log.warning("Failed to delete BM25 retriever cache %s: %s", path, exc)

    try:
        meta_path.unlink()
        removed = True
    except FileNotFoundError:
        pass
    except OSError as exc:  # pragma: no cover - defensive
        log.warning("Failed to delete BM25 retriever cache metadata %s: %s", meta_path, exc)
    return removed


def _delete_all_from_disk(collection_name: str) -> int:
    prefix = _sanitize_collection_name(collection_name)
    removed = 0
    for path in _PERSISTENT_CACHE_DIR.glob(f"{prefix}-*.pkl"):
        try:
            path.unlink()
            removed += 1
        except FileNotFoundError:
            continue
        except OSError as exc:  # pragma: no cover - defensive
            log.warning("Failed to delete BM25 retriever cache %s: %s", path, exc)
            continue

        meta_path = path.with_suffix(".meta.json")
        try:
            meta_path.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:  # pragma: no cover - defensive
            log.warning("Failed to delete BM25 retriever cache metadata %s: %s", meta_path, exc)
    return removed


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

    # Compute key of the retriever
    key = _make_cache_key(
        collection_name,
        bm25_params,
        tokenizer_tag,
        chunking_params,
    )

    cached = _cache.get(key)
    if cached is not None:
        return cached
        # return _clone_retriever(cached)  # cloning involve deep-copy and takes a long time - may be unsafe

    persistent_cached = _load_from_disk(collection_name, key)
    if persistent_cached is not None:
        _cache.put(key, persistent_cached)
        return persistent_cached

    with _build_lock:
        # Another worker may have satisfied the cache while we waited for the
        # build lock, so check again before doing any heavier work.
        cached = _cache.get(key)
        if cached is not None:
            return cached

        persistent_cached = _load_from_disk(collection_name, key)
        if persistent_cached is not None:
            _cache.put(key, persistent_cached)
            return persistent_cached

        texts_list = list(texts or [])
        metadatas_list = list(metadatas or [])

        kwargs = {"texts": texts_list, "metadatas": metadatas_list}
        if bm25_params is not None:
            kwargs["bm25_params"] = bm25_params

        retriever = builder(**kwargs)
        _cache.put(key, retriever)

        metadata = None
        try:
            metadata = {
                "data_digest": compute_collection_digest(texts_list, metadatas_list),
                "tokenizer_tag": tokenizer_tag,
            }
            if bm25_params:
                metadata["bm25_params"] = bm25_params
            if chunking_params:
                metadata["chunking_params"] = chunking_params
        except Exception as exc:  # pragma: no cover - defensive
            log.warning(
                "Failed to compute BM25 cache metadata for collection %s: %s",
                collection_name,
                exc,
            )
            metadata = None

        _save_to_disk(collection_name, key, retriever, metadata=metadata)
        return retriever
        # return _clone_retriever(retriever) # cloning involve deep-copy and takes a long time - may be unsafe


def invalidate_cache(
    collection_name: str,
    *,
    bm25_params: Optional[Mapping[str, Any]] = None,
    tokenizer_tag: str = "default",
    chunking_params: Optional[Mapping[str, Any]] = None,
) -> dict[str, int]:
    key = _make_cache_key(
        collection_name,
        bm25_params,
        tokenizer_tag,
        chunking_params,
    )
    memory_removed = 1 if _cache.delete(key) else 0
    disk_removed = 1 if _delete_from_disk(collection_name, key) else 0
    return {"memory": memory_removed, "disk": disk_removed}


def invalidate_collection_cache(collection_name: str) -> dict[str, int]:
    memory_removed = _cache.delete_prefix(f"{collection_name or ''}|")
    disk_removed = _delete_all_from_disk(collection_name)
    return {"memory": memory_removed, "disk": disk_removed}


def clear_cache() -> None:
    _cache.clear()
    try:
        for path in _PERSISTENT_CACHE_DIR.glob("*.pkl"):
            path.unlink()
            meta_path = path.with_suffix(".meta.json")
            try:
                meta_path.unlink()
            except FileNotFoundError:
                pass
    except FileNotFoundError:
        pass
    except OSError as exc:  # pragma: no cover - defensive
        log.warning("Failed to clear BM25 retriever cache directory %s: %s", _PERSISTENT_CACHE_DIR, exc)

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


def get_cache_metadata(
    collection_name: str,
    *,
    bm25_params: Optional[Mapping[str, Any]] = None,
    tokenizer_tag: str = "default",
    chunking_params: Optional[Mapping[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    key = _make_cache_key(
        collection_name,
        bm25_params,
        tokenizer_tag,
        chunking_params,
    )
    metadata = _load_metadata_from_disk(collection_name, key)
    if metadata is None:
        return None
    metadata.setdefault("collection_name", collection_name)
    return metadata
