# NOTE: This vector database integration is community-supported and maintained on a best-effort basis.
# Requires Valkey core >= 9.0.1 with the valkey-search module >= 1.2.0 loaded.

import atexit
import json
import logging
import re
import struct
from urllib.parse import urlparse

from glide_sync import (
    Batch,
    DataType,
    DistanceMetricType,
    FtCreateOptions,
    FtSearchLimit,
    FtSearchOptions,
    GlideClient,
    GlideClientConfiguration,
    NodeAddress,
    RequestError,
    ReturnField,
    TagField,
    TextField,
    VectorAlgorithm,
    VectorField,
    VectorFieldAttributesFlat,
    VectorFieldAttributesHnsw,
    VectorType,
)
from glide_sync import (
    ft as glide_ft,
)
from open_webui.config import (
    VALKEY_COLLECTION_PREFIX,
    VALKEY_DISTANCE_METRIC,
    VALKEY_HNSW_EF_CONSTRUCTION,
    VALKEY_HNSW_EF_RUNTIME,
    VALKEY_HNSW_M,
    VALKEY_INDEX_TYPE,
    VALKEY_URL,
)
from open_webui.retrieval.vector.main import (
    GetResult,
    SearchResult,
    VectorDBBase,
    VectorItem,
)
from open_webui.retrieval.vector.utils import process_metadata

log = logging.getLogger(__name__)

# valkey-search 1.2.0 requires Valkey core 9.0.1+ per upstream release notes.
# Unlike RediSearch (dialects 1-4), valkey-search only implements DIALECT 2 — GLIDE's
# FtSearchOptions doesn't expose a dialect parameter because it's always dialect 2.
MIN_VALKEY_VERSION = (9, 0, 1)
MIN_SEARCH_MODULE_VERSION = (1, 2, 0)

_VALID_DISTANCE_METRICS = {'COSINE', 'L2', 'IP'}
_NEVER_MATCH_SENTINEL = '__open_webui_valkey_never_match__'

# Compile once at module load — includes `?` which is a single-char wildcard in TAG queries.
_TAG_SPECIAL_RE = re.compile(r'([,.<>{}\[\]"\':;!@#$%^&*()\-+=~?\\/| \t\n\r])')

_DISTANCE_METRIC_MAP = {
    'COSINE': DistanceMetricType.COSINE,
    'L2': DistanceMetricType.L2,
    'IP': DistanceMetricType.IP,
}

_SAFE_FIELD_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def _vector_to_bytes(vector: list[float | int]) -> bytes:
    """Pack a list of floats as a float32 little-endian binary blob."""
    return struct.pack(f'<{len(vector)}f', *vector)


def _escape_tag_value(value: str) -> str:
    """Escape special characters for RediSearch/Valkey-Search TAG field queries."""
    return _TAG_SPECIAL_RE.sub(r'\\\1', str(value))


def _build_filter_expression(filter: dict) -> str:
    """Translate a Chroma-style filter dict into a valkey-search filter expression.

    Supports simple equality, $in, $ne, and $eq. Multiple keys are ANDed together.
    Raises ValueError on unsupported operators rather than silently matching nothing.
    """
    parts = []
    for key, value in filter.items():
        if not _SAFE_FIELD_RE.match(key):
            raise ValueError(
                f'Invalid filter field name: {key!r}. '
                'Field names must start with a letter or underscore and contain only alphanumerics/underscores.'
            )
        if isinstance(value, dict):
            for op, operand in value.items():
                if op == '$in' and isinstance(operand, list):
                    if not operand:
                        # Empty $in → match nothing, not "match all".
                        parts.append(f'@{key}:{{{_NEVER_MATCH_SENTINEL}}}')
                        continue
                    escaped = [_escape_tag_value(str(v)) for v in operand]
                    parts.append(f'@{key}:{{{"|".join(escaped)}}}')
                elif op in ('$eq', '$ne'):
                    prefix = '-' if op == '$ne' else ''
                    parts.append(f'{prefix}@{key}:{{{_escape_tag_value(str(operand))}}}')
                else:
                    raise ValueError(
                        f'Unsupported filter operator {op!r} for key {key!r}. Supported operators: $in, $ne, $eq.'
                    )
        else:
            parts.append(f'@{key}:{{{_escape_tag_value(str(value))}}}')
    return ' '.join(parts)


def _decode(value) -> str:
    """Decode bytes to str; pass through str unchanged."""
    if isinstance(value, (bytes, bytearray)):
        return value.decode()
    return str(value) if value is not None else ''


class ValkeyClient(VectorDBBase):
    def __init__(self):
        if not VALKEY_URL:
            raise ValueError(
                'VALKEY_URL is required when VECTOR_DB=valkey. '
                'Set it to your Valkey server URL (e.g., valkey://localhost:6379).'
            )

        # Validate distance metric at init — invalid values pass through to FT.CREATE
        # and fail with a cryptic server error.
        metric = VALKEY_DISTANCE_METRIC.upper()
        if metric not in _VALID_DISTANCE_METRICS:
            raise ValueError(
                f'Invalid VALKEY_DISTANCE_METRIC={VALKEY_DISTANCE_METRIC!r}. '
                f'Must be one of: {", ".join(sorted(_VALID_DISTANCE_METRICS))}.'
            )

        self.collection_prefix = VALKEY_COLLECTION_PREFIX
        self.index_type = VALKEY_INDEX_TYPE
        self.distance_metric = metric

        parsed = urlparse(VALKEY_URL)
        host = parsed.hostname or 'localhost'
        port = parsed.port or 6379
        db = int(parsed.path.lstrip('/') or 0)

        config = GlideClientConfiguration(
            addresses=[NodeAddress(host=host, port=port)],
            database_id=db if db else None,
            request_timeout=5000,
        )
        try:
            self.client: GlideClient = GlideClient.create(config)
        except Exception as e:
            raise ConnectionError(f'Failed to connect to Valkey at {host}:{port}: {e}') from e

        # Separate client for batch writes — large HSET payloads on the multiplexed
        # connection can starve concurrent reads.
        batch_config = GlideClientConfiguration(
            addresses=[NodeAddress(host=host, port=port)],
            database_id=db if db else None,
            request_timeout=10000,  # 10s — HNSW indexing can take 1-4s per vector
        )
        try:
            self.batch_client: GlideClient = GlideClient.create(batch_config)
        except Exception as e:
            raise ConnectionError(f'Failed to create batch write client for Valkey at {host}:{port}: {e}') from e

        try:
            self.client.ping()
        except Exception as e:
            raise ConnectionError(f'Failed to ping Valkey at {host}:{port}: {e}') from e

        # Catch misconfigured deployments at startup (e.g., valkey-bundle:9.0.1 ships
        # valkey-search 1.0.0 which lacks TEXT fields and filter-only FT.SEARCH).
        self._check_core_version()
        self._check_search_module()

        atexit.register(self.close)

    def close(self) -> None:
        """Close both GLIDE clients, flushing in-flight requests."""
        try:
            self.client.close()
        except Exception:
            pass
        try:
            self.batch_client.close()
        except Exception:
            pass

    # ----- version checks ----------------------------------------------------

    @staticmethod
    def _parse_semver(version_str: str) -> tuple[int, int, int] | None:
        if not version_str:
            return None
        m = re.match(r'^(\d+)\.(\d+)\.(\d+)', version_str)
        return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None

    @staticmethod
    def _format_version(v: tuple[int, int, int]) -> str:
        return f'{v[0]}.{v[1]}.{v[2]}'

    def _check_core_version(self) -> None:
        try:
            info_raw = self.client.info()
        except Exception as e:
            log.warning(f'Could not fetch Valkey INFO for version check, proceeding: {e}')
            return

        raw = None
        text = _decode(info_raw) if info_raw else ''
        redis_fallback = None
        for line in text.splitlines():
            if line.startswith('valkey_version:'):
                raw = line.split(':', 1)[1].strip()
                break
            if line.startswith('redis_version:') and redis_fallback is None:
                redis_fallback = line.split(':', 1)[1].strip()
        if raw is None:
            raw = redis_fallback
        version = self._parse_semver(raw) if raw else None

        if version is None:
            log.warning(
                f'Could not determine Valkey core version (raw={raw!r}); proceeding but '
                f'minimum {self._format_version(MIN_VALKEY_VERSION)} is required.'
            )
        elif version < MIN_VALKEY_VERSION:
            raise RuntimeError(
                f'Valkey core {self._format_version(version)} is below the minimum required version '
                f'{self._format_version(MIN_VALKEY_VERSION)}. valkey-search 1.2.0 requires Valkey core '
                '9.0.1 or later. Upgrade your server or use valkey-bundle:9.1.0-rc2+.'
            )
        log.info(f'Valkey core version: {self._format_version(version) if version else "unknown"}')

    def _check_search_module(self) -> None:
        try:
            modules = self.client.custom_command(['MODULE', 'LIST'])
        except Exception as e:
            log.warning(
                f'Could not list modules on the Valkey server ({e}); proceeding but '
                f'valkey-search >= {self._format_version(MIN_SEARCH_MODULE_VERSION)} is required.'
            )
            return

        # MODULE LIST returns [{b'name': b'search', b'ver': 66048, ...}]
        # ver encoding: major*10000 + minor*100 + patch
        search_version: tuple[int, int, int] | None = None
        module_present = False
        raw_ver = None
        for entry in modules or []:
            if isinstance(entry, dict):
                name = _decode(entry.get(b'name') or entry.get('name') or '')
                raw_ver = entry.get(b'ver') or entry.get('ver', 0)
            else:
                parsed = self._decode_kv_pairs(entry)
                name = parsed.get('name', '')
                raw_ver = parsed.get('ver', 0)
            if name.lower() == 'search':
                module_present = True
                try:
                    ver_int = int(raw_ver)
                    search_version = (ver_int // 10000, (ver_int % 10000) // 100, ver_int % 100)
                except (TypeError, ValueError):
                    search_version = None
                break

        if not module_present:
            raise RuntimeError(
                'The valkey-search module is not loaded on the Valkey server. '
                f'This backend requires valkey-search >= {self._format_version(MIN_SEARCH_MODULE_VERSION)}. '
                'Use valkey-bundle:9.1.0-rc2+ or load libsearch.so via --loadmodule on a Valkey 9.0.1+ server.'
            )
        if search_version is None:
            log.warning(
                f'valkey-search module is loaded but version could not be parsed (raw={raw_ver!r}); '
                f'proceeding but minimum {self._format_version(MIN_SEARCH_MODULE_VERSION)} is required.'
            )
        elif search_version < MIN_SEARCH_MODULE_VERSION:
            raise RuntimeError(
                f'valkey-search {self._format_version(search_version)} is below the minimum required '
                f'version {self._format_version(MIN_SEARCH_MODULE_VERSION)}. Earlier versions lack the '
                'TEXT field type and filter-only FT.SEARCH support required by this backend. '
                'Upgrade to valkey-bundle:9.1.0-rc2+ or load valkey-search 1.2.0+ as a module.'
            )
        log.info(f'valkey-search version: {self._format_version(search_version) if search_version else "unknown"}')

    def _index_name(self, collection_name: str) -> str:
        return f'idx:{self.collection_prefix}:{collection_name}'

    def _key_prefix(self, collection_name: str) -> str:
        return f'{self.collection_prefix}:{collection_name}:'

    def _item_key(self, collection_name: str, item_id: str) -> str:
        return f'{self.collection_prefix}:{collection_name}:{item_id}'

    def _create_index(self, collection_name: str, dimension: int) -> None:
        """Create an FT index for a collection with the given vector dimension."""
        index_name = self._index_name(collection_name)
        prefix = self._key_prefix(collection_name)
        distance_metric = _DISTANCE_METRIC_MAP[self.distance_metric]

        if self.index_type == 'HNSW':
            vector_attrs = VectorFieldAttributesHnsw(
                dimensions=dimension,
                distance_metric=distance_metric,
                type=VectorType.FLOAT32,
                number_of_edges=VALKEY_HNSW_M,
                vectors_examined_on_construction=VALKEY_HNSW_EF_CONSTRUCTION,
                vectors_examined_on_runtime=VALKEY_HNSW_EF_RUNTIME,
            )
            algo = VectorAlgorithm.HNSW
        else:
            if self.index_type != 'FLAT':
                log.warning(f'Unrecognized VALKEY_INDEX_TYPE={self.index_type!r}; falling back to FLAT.')
            vector_attrs = VectorFieldAttributesFlat(
                dimensions=dimension,
                distance_metric=distance_metric,
                type=VectorType.FLOAT32,
            )
            algo = VectorAlgorithm.FLAT

        schema = [
            VectorField(name='vector', algorithm=algo, attributes=vector_attrs),
            TextField(name='text'),
            TagField(name='id'),
            TextField(name='metadata_json'),
            TagField(name='hash'),
            TagField(name='file_id'),
            TagField(name='source'),
            TagField(name='knowledge_base_id'),
        ]

        options = FtCreateOptions(data_type=DataType.HASH, prefixes=[prefix])

        try:
            glide_ft.create(self.client, index_name, schema, options)
            log.info(
                f'Created Valkey index {index_name} with dimension={dimension}, '
                f'type={self.index_type}, metric={self.distance_metric}'
            )
        except RequestError as e:
            if 'already exists' in str(e).lower():
                log.debug(f'Index {index_name} already exists, skipping creation.')
            else:
                raise

    def _verify_collection_dimension(self, collection_name: str, dimension: int) -> None:
        index_name = self._index_name(collection_name)
        try:
            info = glide_ft.info(self.client, index_name)
        except Exception as e:
            log.warning(f'Could not FT.INFO {index_name} for dimension check, skipping: {e}')
            return

        # ft.info response has nested structure: b'attributes' → list of fields,
        # each field is [k1, v1, ...] with a nested 'index' sub-list containing 'dimensions'.
        existing = None
        attrs = None
        if isinstance(info, dict):
            attrs = info.get(b'attributes') or info.get('attributes')
        elif isinstance(info, (list, tuple)):
            attrs = self._find_in_kv_pairs(info, 'attributes', case_insensitive=True)

        for attr in attrs or []:
            if not isinstance(attr, (list, tuple)):
                continue
            field_type = self._find_in_kv_pairs(attr, 'type', case_insensitive=True)
            if _decode(field_type).upper() != 'VECTOR':
                continue
            index_params = self._find_in_kv_pairs(attr, 'index', case_insensitive=True)
            if index_params and isinstance(index_params, (list, tuple)):
                dim_raw = self._find_in_kv_pairs(index_params, 'dimensions', case_insensitive=True)
                if dim_raw is not None:
                    try:
                        existing = int(dim_raw)
                    except (ValueError, TypeError):
                        pass
            break

        if existing is None:
            log.warning(
                f'Could not determine vector dimension for {index_name} from FT.INFO response, '
                'skipping dimension check.'
            )
            return
        if existing != dimension:
            raise ValueError(
                f'Collection {collection_name!r} was created with dim={existing}, refusing to '
                f'insert vectors with dim={dimension}. Recreate the collection (e.g., via '
                'VECTOR_DB_CLIENT.delete_collection) if you intend to switch embedding models.'
            )

    def has_collection(self, collection_name: str) -> bool:
        index_name = self._index_name(collection_name)
        try:
            glide_ft.info(self.client, index_name)
            return True
        except RequestError as e:
            msg = str(e).lower()
            if 'no such index' in msg or 'unknown index' in msg or 'not found in database' in msg:
                return False
            log.warning(f'Unexpected FT.INFO response for collection {collection_name}: {e}')
            raise

    def delete_collection(self, collection_name: str):
        index_name = self._index_name(collection_name)
        try:
            glide_ft.dropindex(self.client, index_name)
            log.info(f'Dropped index {index_name}')
        except RequestError as e:
            log.debug(f'Could not drop index {index_name}: {e}')

        self._delete_keys_by_prefix(self._key_prefix(collection_name))

    def insert(self, collection_name: str, items: list[VectorItem]):
        if not items:
            return

        dimension = len(items[0]['vector'])
        if not self.has_collection(collection_name):
            self._create_index(collection_name, dimension)
        else:
            self._verify_collection_dimension(collection_name, dimension)

        # Individual HSET rather than Batch.exec() — each command gets its own timeout.
        # HNSW indexing can take 1-4s per vector (ef_construction=200), and Batch.exec()
        # applies a single timeout to ALL commands, causing all-or-nothing failures on
        # large inserts.
        for item in items:
            metadata = process_metadata(item['metadata']) if item.get('metadata') else {}
            mapping = {
                'id': item['id'],
                'vector': _vector_to_bytes(item['vector']),
                'text': item['text'],
                'metadata_json': json.dumps(metadata),
                # `or ''` prevents indexing literal 'None' as a TAG value, which would
                # poison $ne / equality queries.
                'hash': str(metadata.get('hash') or ''),
                'file_id': str(metadata.get('file_id') or ''),
                'source': str(metadata.get('source') or ''),
                'knowledge_base_id': str(metadata.get('knowledge_base_id') or ''),
            }
            self.batch_client.hset(self._item_key(collection_name, item['id']), mapping)

        log.debug(f'Inserted {len(items)} items into collection {collection_name}')

    def upsert(self, collection_name: str, items: list[VectorItem]):
        self.insert(collection_name, items)

    def search(
        self,
        collection_name: str,
        vectors: list[list[float | int]],
        filter: dict | None = None,
        limit: int = 10,
    ) -> SearchResult | None:
        if not vectors:
            return None
        if not self.has_collection(collection_name):
            return None

        filter_expr = _build_filter_expression(filter) if filter else ''
        query_str = (
            f'({filter_expr})=>[KNN {limit} @vector $query_vec]'
            if filter_expr
            else f'*=>[KNN {limit} @vector $query_vec]'
        )

        try:
            opts = FtSearchOptions(
                params={'query_vec': _vector_to_bytes(vectors[0])},
                limit=FtSearchLimit(offset=0, count=limit),
            )
            result = glide_ft.search(self.client, self._index_name(collection_name), query_str, opts)
        except RequestError as e:
            log.error(f'Valkey search error on collection {collection_name}: {e}')
            return None

        return self._parse_glide_search_response(result, include_score=True)

    def query(self, collection_name: str, filter: dict, limit: int | None = None) -> GetResult | None:
        if not self.has_collection(collection_name):
            return None
        if not filter:
            return self.get(collection_name, limit=limit)

        query_str = _build_filter_expression(filter)
        if not query_str:
            return self.get(collection_name, limit=limit)

        # Hard cap when no limit provided — FT.SEARCH requires a finite count.
        effective_limit = limit if limit and limit > 0 else 10000
        if not (limit and limit > 0):
            log.warning(
                f'query() called without a limit on collection {collection_name}; '
                f'capping at {effective_limit} results. Pass an explicit limit to avoid silent truncation.'
            )

        try:
            opts = FtSearchOptions(
                return_fields=[
                    ReturnField(field_identifier='id'),
                    ReturnField(field_identifier='text'),
                    ReturnField(field_identifier='metadata_json'),
                ],
                limit=FtSearchLimit(offset=0, count=effective_limit),
            )
            result = glide_ft.search(self.client, self._index_name(collection_name), query_str, opts)
        except RequestError as e:
            log.error(f'Valkey query error on collection {collection_name}: {e}')
            return None

        return self._parse_glide_search_response(result, include_score=False)

    def get(self, collection_name: str, limit: int | None = None) -> GetResult | None:
        if not self.has_collection(collection_name):
            return None

        # FT.SEARCH "*" wildcard not yet in a tagged valkey-search release (tracked in #957).
        # SCAN fallback is acceptable here — get() is not on the hot search path.
        prefix = self._key_prefix(collection_name)
        ids, documents, metadatas = [], [], []
        cursor = '0'
        while True:
            scan_result = self.client.scan(cursor=cursor, match=f'{prefix}*', count=500)
            cursor = _decode(scan_result[0])
            keys = scan_result[1]
            if keys:
                batch = Batch(is_atomic=False)
                for key in keys:
                    batch.hgetall(key)
                results = self.client.exec(batch, raise_on_error=False) or []
                for fields in results:
                    if not fields:
                        continue
                    ids.append(_decode(fields.get(b'id', b'')))
                    documents.append(_decode(fields.get(b'text', b'')))
                    try:
                        metadatas.append(json.loads(_decode(fields.get(b'metadata_json', b'{}'))))
                    except (json.JSONDecodeError, TypeError):
                        metadatas.append({})
                    if limit is not None and limit > 0 and len(ids) >= limit:
                        return GetResult(ids=[ids], documents=[documents], metadatas=[metadatas])
            if cursor == '0':
                break

        return GetResult(ids=[ids], documents=[documents], metadatas=[metadatas])

    def delete(
        self,
        collection_name: str,
        ids: list[str] | None = None,
        filter: dict | None = None,
    ):
        if ids:
            keys = [self._item_key(collection_name, item_id) for item_id in ids]
            try:
                self.batch_client.delete(keys)
            except RequestError as e:
                log.error(f'Valkey delete error on collection {collection_name}: {e}')
            return

        if not filter:
            return

        filter_expr = _build_filter_expression(filter)
        if not filter_expr:
            return

        index_name = self._index_name(collection_name)
        page_size = 10000
        while True:
            try:
                opts = FtSearchOptions(
                    return_fields=[ReturnField(field_identifier='id')],
                    limit=FtSearchLimit(offset=0, count=page_size),
                )
                result = glide_ft.search(self.client, index_name, filter_expr, opts)
            except RequestError as e:
                log.error(f'Valkey delete-by-filter error on collection {collection_name}: {e}')
                return

            if not result or result[0] == 0:
                return

            keys_map = result[1] if len(result) > 1 else {}
            keys = [_decode(k) for k in keys_map.keys()] if isinstance(keys_map, dict) else []
            if not keys:
                return
            self.batch_client.delete(keys)
            if len(keys) < page_size:
                return

    def reset(self):
        collections: list[str] = []
        try:
            indexes = glide_ft.list(self.client) or []
            idx_prefix = f'idx:{self.collection_prefix}:'
            for idx in indexes:
                name = _decode(idx)
                if name.startswith(idx_prefix):
                    collections.append(name[len(idx_prefix) :])
                    try:
                        glide_ft.dropindex(self.client, idx)
                        log.info(f'Dropped index: {name}')
                    except Exception as e:
                        log.error(f'Error dropping index {name}: {e}')
        except Exception as e:
            log.error(f'Error listing indexes during reset: {e}')

        for collection in collections:
            self._delete_keys_by_prefix(self._key_prefix(collection))
        log.info(f'Valkey vector store reset complete (prefix: {self.collection_prefix})')

    def _delete_keys_by_prefix(self, prefix: str) -> None:
        cursor = '0'
        while True:
            scan_result = self.client.scan(cursor=cursor, match=f'{prefix}*', count=500)
            cursor = _decode(scan_result[0])
            keys = scan_result[1]
            if keys:
                self.batch_client.delete(keys)
            if cursor == '0':
                break

    @staticmethod
    def _decode_kv_pairs(fields) -> dict:
        """Decode a flat [k1, v1, k2, v2, ...] wire array into a dict."""
        if not fields:
            return {}
        if len(fields) % 2 != 0:
            fields = fields[:-1]
        out = {}
        for k, v in zip(fields[::2], fields[1::2]):
            key = _decode(k)
            if isinstance(v, (bytes, bytearray)):
                try:
                    val = v.decode()
                except UnicodeDecodeError:
                    val = v
            else:
                val = v
            out[key] = val
        return out

    @staticmethod
    def _find_in_kv_pairs(pairs, target: str, case_insensitive: bool = False):
        """Look up a value in a flat [k1, v1, k2, v2, ...] array or dict."""
        if isinstance(pairs, dict):
            needle = target.lower() if case_insensitive else target
            for k, v in pairs.items():
                key = _decode(k)
                if (key.lower() if case_insensitive else key) == needle:
                    return v
            return None
        if not isinstance(pairs, (list, tuple)) or len(pairs) < 2:
            return None
        needle = target.lower() if case_insensitive else target
        for j in range(0, len(pairs) - 1, 2):
            key = _decode(pairs[j])
            if (key.lower() if case_insensitive else key) == needle:
                return pairs[j + 1]
        return None

    def _parse_glide_search_response(self, result, include_score: bool) -> SearchResult | GetResult | None:
        """Parse ft.search response: [total_count, {key: {field: value, ...}, ...}]"""
        empty_search = SearchResult(ids=[[]], distances=[[]], documents=[[]], metadatas=[[]])
        empty_get = GetResult(ids=[[]], documents=[[]], metadatas=[[]])
        if not result or result[0] == 0:
            return empty_search if include_score else empty_get

        docs_map = result[1] if len(result) > 1 else {}
        if not isinstance(docs_map, dict):
            return empty_search if include_score else empty_get

        ids, documents, metadatas, distances = [], [], [], []
        for _key, fields in docs_map.items():
            if not isinstance(fields, dict):
                continue
            ids.append(_decode(fields.get(b'id', b'')))
            documents.append(_decode(fields.get(b'text', b'')))
            try:
                metadatas.append(json.loads(_decode(fields.get(b'metadata_json', b'{}'))))
            except (json.JSONDecodeError, TypeError):
                metadatas.append({})

            if include_score:
                try:
                    raw_score = _decode(fields.get(b'__vector_score', b'0'))
                    distances.append(self._normalize_score(float(raw_score)))
                except (ValueError, TypeError):
                    distances.append(0.0)

        if not include_score:
            return GetResult(ids=[ids], documents=[documents], metadatas=[metadatas])

        return SearchResult(ids=[ids], distances=[distances], documents=[documents], metadatas=[metadatas])

    def _normalize_score(self, score: float) -> float:
        """Convert valkey-search __vector_score (a distance, lower = more similar) to [0, 1] similarity.

        All metrics return distance: COSINE/IP in [0, 2] for unit vectors, L2 in [0, ∞).
        """
        if self.distance_metric == 'COSINE':
            # COSINE distance: 0 (identical) → 2 (opposite).  Map to similarity [1, -1], clamp [0, 1].
            return max(0.0, min(1.0, 1.0 - score))
        if self.distance_metric == 'L2':
            # L2 distance: 0 (identical) → ∞.
            return 1.0 / (1.0 + score)
        # IP: distance = 1 - inner_product
        return max(0.0, min(1.0, 1.0 - score))
