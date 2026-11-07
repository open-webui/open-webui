# SPDX-License-Identifier: MIT
"""Unit tests for Open-WebUI `SiliciumOpenWebUIClient` integration."""

from __future__ import annotations

import contextlib
import importlib
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Final


def _load_client_cls() -> type:
    scratch_dir = Path(__file__).resolve().parent
    if str(scratch_dir) not in sys.path:
        sys.path.insert(0, str(scratch_dir))
    for mod_name in (
        'open_webui_silicium_db',
        'open_webui.retrieval.vector.dbs.silicium',
        'neo_training.benchmarks.silicium_sdk_common',
    ):
        with contextlib.suppress(ImportError, AttributeError):
            mod = importlib.import_module(mod_name)
            cls = getattr(mod, 'SiliciumOpenWebUIClient', None) or getattr(mod, 'SiliciumOpenWebUIVectorClient', None)
            if isinstance(cls, type):
                return cls
    raise RuntimeError('Unable to import SiliciumOpenWebUIClient')


def test_silicium_open_webui_client_full_cycle() -> None:
    client_cls: Final = _load_client_cls()
    client: Final = client_cls()

    # 1. has_collection on empty
    assert client.has_collection('test_col') is False

    # 2. insert
    docs_payload: Final = [
        {
            'id': '1',
            'vector': [1.0, 0.0, 0.0, 0.0],
            'text': 'First document regarding machine learning',
            'metadata': {'category': 'ml', 'tier': 'gold'},
        },
        {
            'id': '2',
            'vector': [0.0, 1.0, 0.0, 0.0],
            'text': 'Second document regarding silicon compilers',
            'metadata': {'category': 'silicon', 'tier': 'silver'},
        },
    ]
    client.insert('test_col', docs_payload)
    assert client.has_collection('test_col') is True

    # 3. upsert
    upsert_payload: Final = [
        {
            'id': '3',
            'vector': [0.0, 0.0, 1.0, 0.0],
            'text': 'Third document regarding zero copy simd',
            'metadata': {'category': 'simd', 'tier': 'gold'},
        }
    ]
    client.upsert('test_col', upsert_payload)

    # 4. search (dual attribute and dict access + metadata filter)
    search_res: Final = client.search('test_col', [[1.0, 0.0, 0.0, 0.0]], limit=2)
    assert search_res is not None
    assert search_res.ids[0][0] == '1'
    assert search_res['ids'][0][0] == '1'
    assert search_res.documents[0][0] == 'First document regarding machine learning'
    assert search_res.get('documents')[0][0] == 'First document regarding machine learning'
    assert search_res.metadatas[0][0].get('category') == 'ml'
    assert search_res['metadatas'][0][0].get('category') == 'ml'
    assert len(search_res.distances[0]) == 2

    filtered_search: Final = client.search(
        'test_col',
        [[1.0, 0.0, 0.0, 0.0]],
        filter={'category': 'silicon'},
        limit=2,
    )
    assert filtered_search is not None
    assert filtered_search.ids[0] == ['2']

    # 5. get
    all_res: Final = client.get('test_col')
    assert all_res is not None
    assert len(all_res.ids[0]) == 3

    # 6. query
    q_res: Final = client.query('test_col', filter={'category': 'silicon'})
    assert q_res is not None
    assert len(q_res.ids[0]) == 1
    assert q_res.ids[0][0] == '2'

    # 7. delete by id
    client.delete('test_col', ids=['2'])
    after_del: Final = client.get('test_col')
    assert after_del is not None
    assert len(after_del.ids[0]) == 2
    assert '2' not in after_del.ids[0]

    # 8. ingest_ndjson_zero_copy
    ndjson_data: Final = (
        b'{"id":1001,"text":"doc_ndjson_alpha","meta":{"score":0.95},"embedding":[0.0,0.0,0.0,1.0]}\n'
        b'{"id":1002,"text":"doc_ndjson_beta","meta":{"score":0.85},"embedding":[0.5,0.5,0.0,0.0]}\n'
    )
    bridge_res: Final = client.ingest_ndjson_zero_copy('ndjson_col', ndjson_data, dim=4)
    assert isinstance(bridge_res, Mapping)
    assert int(bridge_res.get('rows_ingested', 0)) >= 2
    assert client.has_collection('ndjson_col') is True
    ndjson_search: Final = client.search('ndjson_col', [[0.0, 0.0, 0.0, 1.0]], limit=1)
    assert ndjson_search is not None
    assert ndjson_search.ids[0][0] == '1001'

    # 9. delete_collection and reset
    assert client.delete_collection('ndjson_col') is True
    assert client.has_collection('ndjson_col') is False
    client.reset()
    assert client.has_collection('test_col') is False


if __name__ == '__main__':
    test_silicium_open_webui_client_full_cycle()
    print(
        json.dumps(
            {
                'status': 'PASS',
                'oracle_id': 'SILICIUM-OPEN-WEBUI-RAG-003',
                'vector_db': 'silicium',
                'zero_copy_rag_bridge': True,
                'operations_tested': [
                    'has_collection',
                    'insert',
                    'upsert',
                    'search',
                    'query',
                    'get',
                    'delete',
                    'ingest_ndjson_zero_copy',
                    'reset',
                ],
            }
        )
    )
