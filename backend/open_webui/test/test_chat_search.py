"""Standalone tests for the GOATED chat-search machinery.

Loads ``open_webui.models.chats`` directly from its file path, with all
heavyweight transitive imports (``open_webui.env``, ``tags``, ``folders``,
``internal.db``) replaced by lightweight stubs. That way the tests run on a
plain ``sqlalchemy + pydantic + pytest`` install and don't need the full
backend dependency stack.

Run with: ``pytest backend/open_webui/test/test_chat_search.py -v``
"""
import importlib.util
import json
import os
import sys
import time
import types
import uuid
from contextlib import contextmanager

import pytest

CHATS_PY_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "models", "chats.py")
)


def _install_stubs(get_db_callable):
    """Mount stub modules so ``chats.py`` imports cleanly without the real
    backend environment. ``get_db_callable`` should be a contextmanager-style
    ``get_db`` that yields the test's SQLAlchemy session."""
    from sqlalchemy.orm import declarative_base
    from pydantic import BaseModel

    # open_webui package skeleton
    if "open_webui" not in sys.modules:
        sys.modules["open_webui"] = types.ModuleType("open_webui")
    if "open_webui.internal" not in sys.modules:
        pkg_internal = types.ModuleType("open_webui.internal")
        pkg_internal.__path__ = []
        sys.modules["open_webui.internal"] = pkg_internal
    if "open_webui.models" not in sys.modules:
        pkg_models = types.ModuleType("open_webui.models")
        pkg_models.__path__ = []
        sys.modules["open_webui.models"] = pkg_models

    # env stub
    env_stub = types.ModuleType("open_webui.env")
    env_stub.SRC_LOG_LEVELS = {"MODELS": 20}
    sys.modules["open_webui.env"] = env_stub

    # internal.db stub
    db_stub = types.ModuleType("open_webui.internal.db")
    db_stub.Base = declarative_base()
    db_stub.get_db = get_db_callable
    sys.modules["open_webui.internal.db"] = db_stub

    # tags stub
    tags_stub = types.ModuleType("open_webui.models.tags")

    class TagModel(BaseModel):
        id: str
        name: str = ""
        user_id: str = ""

    class _Tags:
        @staticmethod
        def get_tag_by_name_and_user_id(*a, **kw):
            return None

        @staticmethod
        def delete_tag_by_name_and_user_id(*a, **kw):
            return None

        @staticmethod
        def insert_new_tag(*a, **kw):
            return None

        @staticmethod
        def get_tags_by_ids_and_user_id(*a, **kw):
            return []

    tags_stub.TagModel = TagModel
    tags_stub.Tag = type("Tag", (), {})
    tags_stub.Tags = _Tags
    sys.modules["open_webui.models.tags"] = tags_stub

    # folders stub
    folders_stub = types.ModuleType("open_webui.models.folders")

    class _Folders:
        @staticmethod
        def search_folders_by_names(user_id, names):
            return []

    folders_stub.Folders = _Folders
    sys.modules["open_webui.models.folders"] = folders_stub


def _load_chats_module():
    """Import open_webui.models.chats from its file path, after stubs are mounted."""
    spec = importlib.util.spec_from_file_location(
        "open_webui.models.chats_test_target", CHATS_PY_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_isolated_db():
    from sqlalchemy import create_engine, text as sql_text
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    sess = SessionLocal()

    sess.execute(
        sql_text(
            """
            CREATE TABLE chat (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                title TEXT,
                chat TEXT,
                created_at INTEGER,
                updated_at INTEGER,
                share_id TEXT,
                archived INTEGER DEFAULT 0,
                pinned INTEGER DEFAULT 0,
                meta TEXT DEFAULT '{}',
                folder_id TEXT,
                search_text TEXT
            )
            """
        )
    )
    sess.execute(
        sql_text(
            """
            CREATE TABLE folder (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                parent_id TEXT,
                name TEXT,
                items TEXT,
                meta TEXT,
                data TEXT,
                is_expanded INTEGER DEFAULT 0,
                created_at INTEGER,
                updated_at INTEGER
            )
            """
        )
    )
    TOK = "porter unicode61 remove_diacritics 2 tokenchars '_-'"
    sess.execute(
        sql_text(
            f"CREATE VIRTUAL TABLE chat_fts USING fts5("
            f"  id UNINDEXED, title, body,"
            f'  tokenize = "{TOK}", prefix = \'2 3 4\')'
        )
    )
    sess.execute(
        sql_text(
            f"CREATE VIRTUAL TABLE message_fts USING fts5("
            f"  chat_id UNINDEXED, message_id UNINDEXED, role UNINDEXED, content,"
            f'  tokenize = "{TOK}", prefix = \'2 3 4\')'
        )
    )
    sess.execute(
        sql_text(
            "CREATE VIRTUAL TABLE chat_fts_tri USING fts5("
            "  id UNINDEXED, content,"
            "  tokenize = 'trigram')"
        )
    )
    sess.execute(
        sql_text(
            "CREATE TRIGGER chat_fts_delete AFTER DELETE ON chat BEGIN "
            "  DELETE FROM chat_fts WHERE id = OLD.id; "
            "  DELETE FROM message_fts WHERE chat_id = OLD.id; "
            "  DELETE FROM chat_fts_tri WHERE id = OLD.id; "
            "END"
        )
    )
    sess.commit()
    return engine, sess


@pytest.fixture
def db_session():
    engine, sess = _make_isolated_db()

    @contextmanager
    def get_db():
        yield sess

    # Mount stubs before importing chats.py
    _install_stubs(get_db)
    chats_module = _load_chats_module()

    # Reset the FTS-support detection cache between tests
    chats_module._fts_supported_cache = None

    yield sess, chats_module

    sess.close()
    engine.dispose()
    chats_module._fts_supported_cache = None


def _insert_chat(
    sess,
    chats_module,
    *,
    chat_id=None,
    user_id="u1",
    title="",
    user_msgs=None,
    assistant_msgs=None,
    archived=False,
    pinned=False,
    meta=None,
    folder_id=None,
    updated_at=None,
):
    from sqlalchemy import text as sql_text

    chat_id = chat_id or str(uuid.uuid4())
    ts = updated_at or int(time.time())
    history_messages = {}
    msgs = []

    def add_msg(role, content):
        mid = f"m{len(history_messages)}"
        history_messages[mid] = {"id": mid, "role": role, "content": content}
        msgs.append({"id": mid, "role": role, "content": content})

    for c in user_msgs or []:
        add_msg("user", c)
    for c in assistant_msgs or []:
        add_msg("assistant", c)

    chat_data = {
        "title": title,
        "history": {
            "currentId": list(history_messages)[-1] if history_messages else None,
            "messages": history_messages,
        },
        "messages": msgs,
        "models": ["test-model"],
    }
    sess.execute(
        sql_text(
            "INSERT INTO chat (id, user_id, title, chat, created_at, updated_at, archived, pinned, meta, folder_id) "
            "VALUES (:id, :uid, :t, :c, :ca, :ua, :a, :p, :meta, :f)"
        ),
        {
            "id": chat_id,
            "uid": user_id,
            "t": title,
            "c": json.dumps(chat_data),
            "ca": ts,
            "ua": ts,
            "a": 1 if archived else 0,
            "p": 1 if pinned else 0,
            "meta": json.dumps(meta or {}),
            "f": folder_id,
        },
    )

    body = chats_module._build_search_text(title, chat_data)
    sess.execute(
        sql_text("UPDATE chat SET search_text = :s WHERE id = :id"),
        {"s": body, "id": chat_id},
    )
    sess.execute(sql_text("DELETE FROM chat_fts WHERE id = :id"), {"id": chat_id})
    sess.execute(
        sql_text("INSERT INTO chat_fts (id, title, body) VALUES (:id, :t, :b)"),
        {"id": chat_id, "t": title, "b": body},
    )
    sess.execute(sql_text("DELETE FROM message_fts WHERE chat_id = :id"), {"id": chat_id})
    for mid, msg in history_messages.items():
        if msg.get("content"):
            sess.execute(
                sql_text(
                    "INSERT INTO message_fts (chat_id, message_id, role, content) "
                    "VALUES (:cid, :mid, :role, :c)"
                ),
                {"cid": chat_id, "mid": mid, "role": msg["role"], "c": msg["content"]},
            )
    sess.execute(sql_text("DELETE FROM chat_fts_tri WHERE id = :id"), {"id": chat_id})
    sess.execute(
        sql_text("INSERT INTO chat_fts_tri (id, content) VALUES (:id, :c)"),
        {"id": chat_id, "c": body},
    )
    sess.commit()
    return chat_id


# ──────────────────────────────────────────────────────────────────────────


def test_search_case_insensitive(db_session):
    sess, chats = db_session
    _insert_chat(sess, chats, title="FastAPI Middleware", user_msgs=["hello world"])
    resp = chats.Chats.search_chats("u1", "fastapi")
    assert resp.total >= 1
    assert any("FastAPI" in h.title for h in resp.hits)


def test_search_diacritic_insensitive(db_session):
    sess, chats = db_session
    _insert_chat(sess, chats, title="Note", user_msgs=["I love café au lait"])
    resp = chats.Chats.search_chats("u1", "cafe")
    assert resp.total >= 1


def test_search_stemming(db_session):
    sess, chats = db_session
    _insert_chat(sess, chats, title="Test", user_msgs=["I went running tests yesterday"])
    resp = chats.Chats.search_chats("u1", "run")
    assert resp.total >= 1


def test_search_or_with_ranking(db_session):
    sess, chats = db_session
    _insert_chat(sess, chats, title="Both", user_msgs=["python and rust together"])
    _insert_chat(sess, chats, title="One", user_msgs=["python alone"])
    resp = chats.Chats.search_chats("u1", "python rust")
    assert resp.total >= 1
    assert resp.hits[0].title == "Both"


def test_search_typo_prefix_fallback(db_session):
    sess, chats = db_session
    _insert_chat(sess, chats, title="API guide", user_msgs=["fastapi middleware docs"])
    resp = chats.Chats.search_chats("u1", "fastap")
    assert resp.total >= 1


def test_search_typo_trigram_fallback(db_session):
    sess, chats = db_session
    _insert_chat(sess, chats, title="API guide", user_msgs=["fastapi middleware docs"])
    resp = chats.Chats.search_chats("u1", "fastpi")
    assert resp.total >= 1


def test_search_phrase_quoted(db_session):
    sess, chats = db_session
    _insert_chat(sess, chats, title="A", user_msgs=["middleware bug in production"])
    _insert_chat(sess, chats, title="B", user_msgs=["bug fix landed; middleware later"])
    resp = chats.Chats.search_chats("u1", '"middleware bug"')
    assert any(h.title == "A" for h in resp.hits)


def test_search_archived_included_by_default(db_session):
    sess, chats = db_session
    _insert_chat(sess, chats, title="Active", user_msgs=["needle"], archived=False)
    _insert_chat(sess, chats, title="Archived", user_msgs=["needle"], archived=True)
    resp = chats.Chats.search_chats("u1", "needle")
    assert resp.total == 2
    assert any(h.archived for h in resp.hits)


def test_search_archived_excluded_when_filter_false(db_session):
    sess, chats = db_session
    _insert_chat(sess, chats, title="Active", user_msgs=["needle"], archived=False)
    _insert_chat(sess, chats, title="Archived", user_msgs=["needle"], archived=True)
    resp = chats.Chats.search_chats("u1", "needle", archived=False)
    assert resp.total == 1
    assert not resp.hits[0].archived


def test_search_snippet_has_mark(db_session):
    sess, chats = db_session
    _insert_chat(sess, chats, title="Doc", user_msgs=["my fastapi project is awesome"])
    resp = chats.Chats.search_chats("u1", "fastapi")
    assert resp.hits
    snippet = resp.hits[0].snippet or ""
    assert "<mark>" in snippet


def test_search_match_count_per_chat(db_session):
    sess, chats = db_session
    _insert_chat(
        sess,
        chats,
        title="Multi",
        user_msgs=["fastapi here", "and again fastapi", "even more fastapi"],
    )
    _insert_chat(sess, chats, title="Single", user_msgs=["just fastapi once"])
    resp = chats.Chats.search_chats("u1", "fastapi")
    multi = next((h for h in resp.hits if h.title == "Multi"), None)
    assert multi is not None and multi.match_count == 3


def test_search_matched_message_id(db_session):
    sess, chats = db_session
    _insert_chat(sess, chats, title="X", user_msgs=["nothing here", "fastapi found"])
    resp = chats.Chats.search_chats("u1", "fastapi")
    assert resp.hits
    assert resp.hits[0].matched_message_id is not None


def test_search_body_only_match_ranks_well(db_session):
    sess, chats = db_session
    _insert_chat(
        sess,
        chats,
        title="New Chat",
        user_msgs=["fastapi middleware fastapi middleware fastapi"],
    )
    _insert_chat(
        sess,
        chats,
        title="Python notes",
        user_msgs=["today I made tea"],
    )
    resp = chats.Chats.search_chats("u1", "fastapi middleware")
    assert resp.hits
    assert resp.hits[0].title == "New Chat"


def test_search_generic_title_penalized(db_session):
    sess, chats = db_session
    _insert_chat(sess, chats, title="New Chat", user_msgs=["deploy script ready"])
    _insert_chat(
        sess,
        chats,
        title="Production deploy guide",
        user_msgs=["deploy script ready"],
    )
    resp = chats.Chats.search_chats("u1", "deploy")
    assert resp.total == 2
    assert resp.hits[0].title == "Production deploy guide"


def test_search_snippet_from_message_not_concat(db_session):
    sess, chats = db_session
    _insert_chat(
        sess,
        chats,
        title="Long",
        user_msgs=[
            "intro",
            "more intro",
            "the actual fastapi middleware section is here",
            "wrap up",
        ],
    )
    resp = chats.Chats.search_chats("u1", "fastapi")
    snippet = resp.hits[0].snippet or ""
    assert "<mark>" in snippet


def test_search_matched_role_returned(db_session):
    sess, chats = db_session
    _insert_chat(
        sess,
        chats,
        title="QA",
        user_msgs=["what is fastapi?"],
        assistant_msgs=["fastapi is a python web framework"],
    )
    resp = chats.Chats.search_chats("u1", "framework")
    assert resp.hits
    assert resp.hits[0].matched_role in ("user", "assistant")


def test_search_recency_decay(db_session):
    sess, chats = db_session
    very_old = int(time.time()) - 365 * 86400
    recent = int(time.time())
    _insert_chat(sess, chats, title="ZZ", user_msgs=["fastapi fastapi fastapi"], updated_at=very_old)
    _insert_chat(sess, chats, title="Other", user_msgs=["fastapi"], updated_at=recent)
    resp = chats.Chats.search_chats("u1", "fastapi")
    assert resp.hits[0].updated_at == recent


def test_search_html_escape_safety(db_session):
    sess, chats = db_session
    _insert_chat(
        sess,
        chats,
        title="Safe",
        user_msgs=['fastapi <script>alert("xss")</script> end'],
    )
    resp = chats.Chats.search_chats("u1", "fastapi")
    snippet = resp.hits[0].snippet or ""
    assert "<script>" not in snippet
    assert "&lt;script&gt;" in snippet


def test_search_no_results_yields_empty(db_session):
    sess, chats = db_session
    _insert_chat(sess, chats, title="X", user_msgs=["hello"])
    resp = chats.Chats.search_chats("u1", "definitelynothere")
    assert resp.total == 0
    assert resp.hits == []


def test_search_prefix_syntax_still_works(db_session):
    sess, chats = db_session
    _insert_chat(sess, chats, title="A", user_msgs=["needle"], pinned=True)
    _insert_chat(sess, chats, title="B", user_msgs=["needle"], pinned=False)
    resp = chats.Chats.search_chats("u1", "needle pinned:true")
    assert resp.total == 1
    assert resp.hits[0].pinned is True


def test_search_facets_have_counts(db_session):
    sess, chats = db_session
    from sqlalchemy import text as sql_text

    sess.execute(
        sql_text(
            "INSERT INTO folder (id, user_id, name, created_at, updated_at) "
            "VALUES (:i, :u, :n, :c, :c)"
        ),
        {"i": "f-1", "u": "u1", "n": "Backend", "c": int(time.time())},
    )
    sess.commit()
    _insert_chat(sess, chats, title="A", user_msgs=["needle"], folder_id="f-1")
    _insert_chat(sess, chats, title="B", user_msgs=["needle"], folder_id="f-1")
    resp = chats.Chats.search_chats("u1", "needle")
    assert any(f.id == "f-1" and f.count == 2 for f in resp.facets.folders)


def test_search_filtered_list_with_empty_query(db_session):
    sess, chats = db_session
    _insert_chat(sess, chats, title="One", user_msgs=["hello"], pinned=True)
    _insert_chat(sess, chats, title="Two", user_msgs=["world"], pinned=False)
    resp = chats.Chats.search_chats("u1", "", pinned=True)
    assert resp.total == 1
    assert resp.hits[0].pinned is True


def test_search_punctuation_in_query(db_session):
    """A user query containing FTS5 operator chars (`.`, `,`, `/`, `:`, ...)
    must NOT crash. ``vast.ai`` should be split into ``vast`` + ``ai`` and
    match documents containing both tokens."""
    sess, chats = db_session
    _insert_chat(sess, chats, title="GPU notes", user_msgs=["I ran on vast.ai with two RTX 5090"])
    resp = chats.Chats.search_chats("u1", "vast.ai")
    assert resp.total >= 1
    # Also try other special-char queries that previously crashed
    for q in ["foo.bar/baz", "name@example.com", "hello, world", "what?", "key:value-pair"]:
        chats.Chats.search_chats("u1", q)  # must not raise


def test_search_user_isolation(db_session):
    sess, chats = db_session
    _insert_chat(sess, chats, user_id="u1", title="Mine", user_msgs=["secret"])
    _insert_chat(sess, chats, user_id="u2", title="Theirs", user_msgs=["secret"])
    resp = chats.Chats.search_chats("u1", "secret")
    assert resp.total == 1
    assert resp.hits[0].title == "Mine"


# ──────────────────────────────────────────────────────────────────────────
# chat_message split (Unit 6)
# ──────────────────────────────────────────────────────────────────────────


def _make_db_with_chat_message_table():
    """Like ``_make_isolated_db`` but additionally creates the chat_message
    table + messages_migrated column so the dual-read path can be exercised."""
    from sqlalchemy import create_engine, text as sql_text
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    sess = SessionLocal()

    sess.execute(
        sql_text(
            """
            CREATE TABLE chat (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                title TEXT,
                chat TEXT,
                created_at INTEGER,
                updated_at INTEGER,
                share_id TEXT,
                archived INTEGER DEFAULT 0,
                pinned INTEGER DEFAULT 0,
                meta TEXT DEFAULT '{}',
                folder_id TEXT,
                search_text TEXT,
                messages_migrated INTEGER NOT NULL DEFAULT 0
            )
            """
        )
    )
    sess.execute(
        sql_text(
            """
            CREATE TABLE folder (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                parent_id TEXT,
                name TEXT,
                items TEXT,
                meta TEXT,
                data TEXT,
                is_expanded INTEGER DEFAULT 0,
                created_at INTEGER,
                updated_at INTEGER
            )
            """
        )
    )
    sess.execute(
        sql_text(
            """
            CREATE TABLE chat_message (
                chat_id TEXT NOT NULL,
                message_id TEXT NOT NULL,
                parent_id TEXT,
                role TEXT,
                content TEXT,
                content_is_json INTEGER DEFAULT 0,
                model TEXT,
                timestamp INTEGER,
                sequence INTEGER NOT NULL,
                status_history TEXT,
                meta TEXT,
                PRIMARY KEY (chat_id, message_id)
            )
            """
        )
    )
    sess.execute(
        sql_text(
            "CREATE INDEX chat_message_chat_seq_idx ON chat_message (chat_id, sequence)"
        )
    )
    TOK = "porter unicode61 remove_diacritics 2 tokenchars '_-'"
    sess.execute(
        sql_text(
            f"CREATE VIRTUAL TABLE chat_fts USING fts5("
            f"  id UNINDEXED, title, body,"
            f'  tokenize = "{TOK}", prefix = \'2 3 4\')'
        )
    )
    sess.execute(
        sql_text(
            f"CREATE VIRTUAL TABLE message_fts USING fts5("
            f"  chat_id UNINDEXED, message_id UNINDEXED, role UNINDEXED, content,"
            f'  tokenize = "{TOK}", prefix = \'2 3 4\')'
        )
    )
    sess.execute(
        sql_text(
            "CREATE VIRTUAL TABLE chat_fts_tri USING fts5("
            "  id UNINDEXED, content,"
            "  tokenize = 'trigram')"
        )
    )
    sess.execute(
        sql_text(
            "CREATE TRIGGER chat_fts_delete AFTER DELETE ON chat BEGIN "
            "  DELETE FROM chat_fts WHERE id = OLD.id; "
            "  DELETE FROM message_fts WHERE chat_id = OLD.id; "
            "  DELETE FROM chat_fts_tri WHERE id = OLD.id; "
            "END"
        )
    )
    sess.commit()
    return engine, sess


@pytest.fixture
def db_session_with_table():
    engine, sess = _make_db_with_chat_message_table()

    @contextmanager
    def get_db():
        yield sess

    _install_stubs(get_db)
    chats_module = _load_chats_module()

    chats_module._fts_supported_cache = None
    chats_module._chat_message_table_supported_cache = None

    yield sess, chats_module

    sess.close()
    engine.dispose()
    chats_module._fts_supported_cache = None
    chats_module._chat_message_table_supported_cache = None


def _insert_migrated_chat(
    sess,
    chats_module,
    *,
    chat_id=None,
    user_id="u1",
    title="",
    n_messages=50,
):
    """Insert a chat with messages_migrated=1 and populate chat_message rows."""
    from sqlalchemy import text as sql_text

    chat_id = chat_id or str(uuid.uuid4())
    ts = int(time.time())
    history_messages = {}
    for i in range(n_messages):
        mid = f"m{i}"
        role = "user" if i % 2 == 0 else "assistant"
        content = f"message-{i} body about fastapi" if i == 0 else f"message-{i} body"
        history_messages[mid] = {
            "id": mid,
            "role": role,
            "content": content,
            "parentId": f"m{i-1}" if i > 0 else None,
        }

    # The on-disk JSON for a migrated chat must NOT include the messages
    # (that's the whole point of the split). Keep only the scaffolding.
    scaffolding = {
        "title": title,
        "history": {
            "currentId": f"m{n_messages-1}" if n_messages else None,
        },
        "models": ["test-model"],
    }
    sess.execute(
        sql_text(
            "INSERT INTO chat (id, user_id, title, chat, created_at, updated_at, "
            " archived, pinned, meta, folder_id, messages_migrated) "
            "VALUES (:id, :uid, :t, :c, :ca, :ua, :a, :p, :meta, :f, 1)"
        ),
        {
            "id": chat_id,
            "uid": user_id,
            "t": title,
            "c": json.dumps(scaffolding),
            "ca": ts,
            "ua": ts,
            "a": 0,
            "p": 0,
            "meta": json.dumps({}),
            "f": None,
        },
    )
    for seq, (mid, msg) in enumerate(history_messages.items()):
        sess.execute(
            sql_text(
                "INSERT INTO chat_message "
                "(chat_id, message_id, parent_id, role, content, "
                " content_is_json, model, timestamp, sequence) "
                "VALUES (:cid, :mid, :pid, :role, :c, 0, NULL, NULL, :seq)"
            ),
            {
                "cid": chat_id,
                "mid": mid,
                "pid": msg.get("parentId"),
                "role": msg["role"],
                "c": msg["content"],
                "seq": seq,
            },
        )
        if msg["content"]:
            sess.execute(
                sql_text(
                    "INSERT INTO message_fts (chat_id, message_id, role, content) "
                    "VALUES (:cid, :mid, :role, :c)"
                ),
                {"cid": chat_id, "mid": mid, "role": msg["role"], "c": msg["content"]},
            )
    sess.commit()
    return chat_id, history_messages


def test_migrated_chat_hydrates_messages_on_read(db_session_with_table):
    sess, chats = db_session_with_table
    cid, msgs = _insert_migrated_chat(sess, chats, title="T", n_messages=5)

    out = chats.Chats.get_chat_by_id(cid)
    assert out is not None
    out_msgs = out.chat.get("history", {}).get("messages", {})
    assert len(out_msgs) == 5
    assert out_msgs["m0"]["role"] == "user"
    assert "fastapi" in out_msgs["m0"]["content"]


def test_migrated_upsert_does_not_rewrite_full_chat_json(db_session_with_table):
    """The whole point of Unit 6: per-message writes must NOT rewrite the
    100+ MB JSON blob. After an upsert, the on-disk chat.chat JSON should
    contain *only* the scaffolding (no messages dict)."""
    from sqlalchemy import text as sql_text

    sess, chats = db_session_with_table
    cid, msgs = _insert_migrated_chat(sess, chats, title="T", n_messages=50)

    # Snapshot the on-disk JSON before upsert.
    pre_row = sess.execute(
        sql_text("SELECT chat FROM chat WHERE id = :id"), {"id": cid}
    ).fetchone()
    pre_json = json.loads(pre_row[0])

    chats.Chats.upsert_message_to_chat_by_id_and_message_id(
        cid, "m0", {"content": "updated content for fastapi"}
    )

    # Check chat_message row was updated.
    row = sess.execute(
        sql_text("SELECT content FROM chat_message WHERE chat_id = :cid AND message_id = 'm0'"),
        {"cid": cid},
    ).fetchone()
    assert row is not None
    assert "updated content for fastapi" == row[0]

    # Check the on-disk JSON blob still has no messages dict.
    post_row = sess.execute(
        sql_text("SELECT chat FROM chat WHERE id = :id"), {"id": cid}
    ).fetchone()
    post_json = json.loads(post_row[0])
    history = post_json.get("history") or {}
    # The crucial assertion: even though we upserted m0, the JSON blob's
    # history.messages is still absent (table-stored) — only the currentId
    # pointer changed.
    assert "messages" not in history or not history.get("messages")
    assert history.get("currentId") == "m0"
    # Title and models scaffolding should be preserved.
    assert post_json.get("models") == pre_json.get("models")


def test_migrated_upsert_updates_message_fts(db_session_with_table):
    from sqlalchemy import text as sql_text

    sess, chats = db_session_with_table
    cid, msgs = _insert_migrated_chat(sess, chats, title="T", n_messages=5)

    # Upsert a new message
    chats.Chats.upsert_message_to_chat_by_id_and_message_id(
        cid, "m99", {"role": "user", "content": "freshly added needle keyword"}
    )

    rows = sess.execute(
        sql_text(
            "SELECT message_id, content FROM message_fts "
            "WHERE chat_id = :cid AND message_id = 'm99'"
        ),
        {"cid": cid},
    ).fetchall()
    assert rows
    assert "needle" in rows[0][1]


def test_migrated_status_history_appended(db_session_with_table):
    from sqlalchemy import text as sql_text

    sess, chats = db_session_with_table
    cid, msgs = _insert_migrated_chat(sess, chats, title="T", n_messages=3)

    chats.Chats.add_message_status_to_chat_by_id_and_message_id(
        cid, "m1", {"status": "running"}
    )
    chats.Chats.add_message_status_to_chat_by_id_and_message_id(
        cid, "m1", {"status": "done"}
    )

    row = sess.execute(
        sql_text(
            "SELECT status_history FROM chat_message "
            "WHERE chat_id = :cid AND message_id = 'm1'"
        ),
        {"cid": cid},
    ).fetchone()
    assert row is not None
    sh = json.loads(row[0])
    assert sh == [{"status": "running"}, {"status": "done"}]


def test_migrated_paginated_messages(db_session_with_table):
    sess, chats = db_session_with_table
    cid, msgs = _insert_migrated_chat(sess, chats, title="T", n_messages=50)

    page = chats.Chats.get_chat_messages_paginated(cid, skip=10, limit=5)
    assert len(page) == 5
    assert page[0]["id"] == "m10"
    assert page[-1]["id"] == "m14"


def test_legacy_chat_unmodified_by_migration_aware_code(db_session_with_table):
    """Unmigrated chats (messages_migrated=0) must keep working via the
    legacy JSON path — the dual-read shouldn't disturb them."""
    sess, chats = db_session_with_table
    cid = _insert_chat(sess, chats, title="Legacy", user_msgs=["hello world"])
    # Force messages_migrated to 0
    from sqlalchemy import text as sql_text

    sess.execute(
        sql_text("UPDATE chat SET messages_migrated = 0 WHERE id = :id"),
        {"id": cid},
    )
    sess.commit()

    out = chats.Chats.get_chat_by_id(cid)
    assert out is not None
    msgs = out.chat.get("history", {}).get("messages", {})
    assert "m0" in msgs
    # Upsert should fall back to legacy path (rewrites JSON).
    chats.Chats.upsert_message_to_chat_by_id_and_message_id(
        cid, "m0", {"content": "updated legacy content"}
    )
    out2 = chats.Chats.get_chat_by_id(cid)
    assert out2.chat["history"]["messages"]["m0"]["content"] == "updated legacy content"
    # Should still be unmigrated.
    row = sess.execute(
        sql_text("SELECT messages_migrated FROM chat WHERE id = :id"), {"id": cid}
    ).fetchone()
    assert row[0] == 0


def test_search_still_works_with_migrated_chat(db_session_with_table):
    """Search must continue to find messages in migrated chats."""
    sess, chats = db_session_with_table
    cid, _ = _insert_migrated_chat(sess, chats, title="Migrated Chat", n_messages=10)
    # Sync the chat_fts/chat_fts_tri rows manually because _insert_migrated_chat
    # only populates message_fts; chat-level FTS is needed for the title-match
    # path. The real migration runs alongside the FTS migration so we mimic
    # that ordering here for the test.
    from sqlalchemy import text as sql_text

    body = "Migrated Chat " + " ".join(
        f"message-{i} body" for i in range(10)
    ) + " fastapi"
    sess.execute(
        sql_text("INSERT INTO chat_fts (id, title, body) VALUES (:id, :t, :b)"),
        {"id": cid, "t": "Migrated Chat", "b": body},
    )
    sess.execute(
        sql_text("INSERT INTO chat_fts_tri (id, content) VALUES (:id, :c)"),
        {"id": cid, "c": body},
    )
    sess.commit()
    resp = chats.Chats.search_chats("u1", "fastapi")
    assert resp.total >= 1
    assert resp.hits[0].id == cid
