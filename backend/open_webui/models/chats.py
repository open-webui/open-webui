import copy
import logging
import json
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.models.tags import TagModel, Tag, Tags
from open_webui.models.folders import Folders
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, Integer, String, Text, JSON, Index
from sqlalchemy import or_, func, select, and_, text, case
from sqlalchemy.sql import exists
from sqlalchemy.sql.expression import bindparam

####################
# Chat DB Schema
####################

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


class Chat(Base):
    __tablename__ = "chat"

    id = Column(String, primary_key=True)
    user_id = Column(String)
    title = Column(Text)
    chat = Column(JSON)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    share_id = Column(Text, unique=True, nullable=True)
    archived = Column(Boolean, default=False)
    pinned = Column(Boolean, default=False, nullable=True)

    meta = Column(JSON, server_default="{}")
    folder_id = Column(Text, nullable=True)

    # 0 = messages still live in `chat.chat.history.messages` (legacy);
    # 1 = messages live in the `chat_message` table and are hydrated on read.
    # Default 0 keeps unmigrated chats on the legacy path.
    messages_migrated = Column(Integer, nullable=False, server_default="0", default=0)

    __table_args__ = (
        # Performance indexes for common queries
        # WHERE folder_id = ...
        Index("folder_id_idx", "folder_id"),
        # WHERE user_id = ... AND pinned = ...
        Index("user_id_pinned_idx", "user_id", "pinned"),
        # WHERE user_id = ... AND archived = ...
        Index("user_id_archived_idx", "user_id", "archived"),
        # WHERE user_id = ... ORDER BY updated_at DESC
        Index("updated_at_user_id_idx", "updated_at", "user_id"),
        # WHERE folder_id = ... AND user_id = ...
        Index("folder_id_user_id_idx", "folder_id", "user_id"),
    )


class ChatModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    chat: dict

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch

    share_id: Optional[str] = None
    archived: bool = False
    pinned: Optional[bool] = False

    meta: dict = {}
    folder_id: Optional[str] = None


class ChatMessage(Base):
    """One row per logical chat message, replacing the per-message entries
    embedded inside ``chat.chat.history.messages``. Only authoritative when
    the parent chat has ``messages_migrated = 1``.

    ``content_is_json = 1`` indicates that ``content`` is a JSON-encoded
    structure (e.g. multimodal parts list) and should be parsed on hydrate.
    ``meta`` stores any message-level fields that don't have dedicated
    columns (followUps, reasoning_details, error, selectedModelId, etc.) so
    round-tripping preserves the original message shape.
    """

    __tablename__ = "chat_message"

    chat_id = Column(String, primary_key=True)
    message_id = Column(String, primary_key=True)
    parent_id = Column(String, nullable=True)
    role = Column(String, nullable=True)
    content = Column(Text, nullable=True)
    content_is_json = Column(Integer, default=0)
    model = Column(String, nullable=True)
    timestamp = Column(BigInteger, nullable=True)
    sequence = Column(Integer, nullable=False)
    status_history = Column(Text, nullable=True)
    meta = Column(Text, nullable=True)

    __table_args__ = (
        Index("chat_message_chat_seq_idx", "chat_id", "sequence"),
        Index("chat_message_chat_parent_idx", "chat_id", "parent_id"),
    )


class ChatMessageModel(BaseModel):
    """Pydantic shape that mirrors the chat_message table for API responses."""

    model_config = ConfigDict(from_attributes=True)

    chat_id: str
    message_id: str
    parent_id: Optional[str] = None
    role: Optional[str] = None
    content: Optional[str] = None
    content_is_json: Optional[int] = 0
    model: Optional[str] = None
    timestamp: Optional[int] = None
    sequence: int = 0
    status_history: Optional[str] = None
    meta: Optional[str] = None


####################
# Forms
####################


class ChatForm(BaseModel):
    chat: dict
    folder_id: Optional[str] = None


class ChatImportForm(ChatForm):
    meta: Optional[dict] = {}
    pinned: Optional[bool] = False
    created_at: Optional[int] = None
    updated_at: Optional[int] = None


class ChatTitleMessagesForm(BaseModel):
    title: str
    messages: list[dict]


class ChatTitleForm(BaseModel):
    title: str


class ChatResponse(BaseModel):
    id: str
    user_id: str
    title: str
    chat: dict
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch
    share_id: Optional[str] = None  # id of the chat to be shared
    archived: bool
    pinned: Optional[bool] = False
    meta: dict = {}
    folder_id: Optional[str] = None


class ChatTitleIdResponse(BaseModel):
    id: str
    title: str
    updated_at: int
    created_at: int


class ChatSearchHit(BaseModel):
    id: str
    title: str
    updated_at: int
    created_at: int
    archived: bool = False
    pinned: bool = False
    folder_id: Optional[str] = None
    snippet: Optional[str] = None  # safe HTML, only <mark> tags allowed
    match_count: int = 0
    matched_message_id: Optional[str] = None
    matched_role: Optional[str] = None
    score: float = 0.0


class FacetBucket(BaseModel):
    id: str
    name: str
    count: int


class ChatSearchFacets(BaseModel):
    folders: list[FacetBucket] = []
    tags: list[FacetBucket] = []
    models: list[FacetBucket] = []


class ChatSearchResponse(BaseModel):
    total: int = 0
    hits: list[ChatSearchHit] = []
    facets: ChatSearchFacets = ChatSearchFacets()
    used_fuzzy: bool = False
    did_you_mean: Optional[str] = None


def _extract_content_text(content) -> str:
    """Extract plain text from a message content field (string or multimodal list)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        )
    return ""


def _build_search_text(title: str, chat_data: dict) -> str:
    """Build a flat lowercase string of title + all message content for fast LIKE search."""
    parts = [title or ""]

    history = chat_data.get("history") or {}
    history_messages = history.get("messages") if isinstance(history, dict) else None
    if history_messages and isinstance(history_messages, dict):
        for msg in history_messages.values():
            if isinstance(msg, dict):
                parts.append(_extract_content_text(msg.get("content", "")))
    elif "messages" in chat_data:
        for msg in chat_data.get("messages") or []:
            if isinstance(msg, dict):
                parts.append(_extract_content_text(msg.get("content", "")))

    # Limit to 64KB to keep DB size reasonable
    return " ".join(parts).lower()[:65536]


_search_col_exists_cache: Optional[bool] = None


def _search_text_column_exists(db) -> bool:
    """Check (with caching) whether the search_text column exists in the chat table."""
    global _search_col_exists_cache
    if _search_col_exists_cache is not None:
        return _search_col_exists_cache
    try:
        db.execute(text("SELECT search_text FROM chat LIMIT 0"))
        _search_col_exists_cache = True
    except Exception:
        _search_col_exists_cache = False
    return _search_col_exists_cache


_fts_supported_cache: Optional[bool] = None


def _fts_supported(db) -> bool:
    """SQLite + chat_fts virtual table present. Cached after first call."""
    global _fts_supported_cache
    if _fts_supported_cache is not None:
        return _fts_supported_cache
    try:
        if db.bind.dialect.name != "sqlite":
            _fts_supported_cache = False
            return False
        db.execute(text("SELECT 1 FROM chat_fts LIMIT 0"))
        _fts_supported_cache = True
    except Exception:
        _fts_supported_cache = False
    return _fts_supported_cache


def _iter_chat_messages(chat_data: dict):
    """Yield (message_id, role, content_text) for every message in a chat."""
    if not isinstance(chat_data, dict):
        return
    history = chat_data.get("history") or {}
    history_messages = history.get("messages") if isinstance(history, dict) else None
    if history_messages and isinstance(history_messages, dict):
        for mid, msg in history_messages.items():
            if isinstance(msg, dict):
                yield (
                    str(mid),
                    str(msg.get("role", "")),
                    _extract_content_text(msg.get("content", "")),
                )
    elif "messages" in chat_data:
        for idx, msg in enumerate(chat_data.get("messages") or []):
            if isinstance(msg, dict):
                yield (
                    str(msg.get("id", f"_{idx}")),
                    str(msg.get("role", "")),
                    _extract_content_text(msg.get("content", "")),
                )


def _upsert_chat_fts(db, chat_id: str, title: str, chat_data: dict) -> None:
    """Refresh all three FTS tables for one chat. No-op when FTS isn't present.

    Dual-read aware: if the chat is migrated to the ``chat_message`` table,
    we pull message text from there. Otherwise we fall back to iterating
    the messages embedded in ``chat_data['history']['messages']`` (legacy
    chats and freshly-inserted chats both go through this path)."""
    if not _fts_supported(db):
        return

    migrated = _is_chat_migrated(db, chat_id)
    if migrated:
        # Hydrate a shallow copy so _build_search_text sees the real messages.
        try:
            messages = _chat_messages_from_table(db, chat_id)
            chat_for_body = dict(chat_data) if isinstance(chat_data, dict) else {}
            history_for_body = (
                dict(chat_for_body.get("history") or {})
                if isinstance(chat_for_body.get("history"), dict)
                else {}
            )
            history_for_body["messages"] = messages
            chat_for_body["history"] = history_for_body
        except Exception:
            chat_for_body = chat_data
    else:
        chat_for_body = chat_data

    body = _build_search_text(title, chat_for_body)

    try:
        db.execute(text("DELETE FROM chat_fts WHERE id = :id"), {"id": chat_id})
        db.execute(
            text("INSERT INTO chat_fts (id, title, body) VALUES (:id, :t, :b)"),
            {"id": chat_id, "t": title or "", "b": body},
        )
        db.execute(text("DELETE FROM message_fts WHERE chat_id = :id"), {"id": chat_id})
        for mid, role, content in _iter_chat_messages(chat_for_body):
            if not content:
                continue
            db.execute(
                text(
                    "INSERT INTO message_fts (chat_id, message_id, role, content) "
                    "VALUES (:cid, :mid, :role, :content)"
                ),
                {
                    "cid": chat_id,
                    "mid": mid,
                    "role": role,
                    "content": content[:65536],
                },
            )
        db.execute(text("DELETE FROM chat_fts_tri WHERE id = :id"), {"id": chat_id})
        db.execute(
            text("INSERT INTO chat_fts_tri (id, content) VALUES (:id, :c)"),
            {"id": chat_id, "c": body},
        )
    except Exception:
        # FTS staleness is preferable to losing the underlying chat write.
        pass


def _upsert_message_fts(
    db, chat_id: str, message_id: str, role: Optional[str], content: Optional[str]
) -> None:
    """Refresh just the per-message FTS row for a single message. Used by the
    migrated write-path so we don't rebuild every chat_fts/message_fts row
    on every per-message upsert. We deliberately do NOT touch chat_fts or
    chat_fts_tri here — those get rebuilt by ``_upsert_chat_fts`` only when
    ``update_chat_by_id`` runs (i.e. when the underlying chat content
    actually changes)."""
    if not _fts_supported(db):
        return
    try:
        db.execute(
            text("DELETE FROM message_fts WHERE chat_id = :cid AND message_id = :mid"),
            {"cid": chat_id, "mid": message_id},
        )
        if content:
            db.execute(
                text(
                    "INSERT INTO message_fts (chat_id, message_id, role, content) "
                    "VALUES (:cid, :mid, :role, :c)"
                ),
                {
                    "cid": chat_id,
                    "mid": message_id,
                    "role": role or "",
                    "c": content[:65536],
                },
            )
    except Exception:
        # Staleness is preferable to losing the underlying chat write.
        pass


_chat_message_table_supported_cache: Optional[bool] = None


def _chat_message_table_supported(db) -> bool:
    """True when the new ``chat_message`` table + ``messages_migrated`` column
    are both present. Cached after first probe."""
    global _chat_message_table_supported_cache
    if _chat_message_table_supported_cache is not None:
        return _chat_message_table_supported_cache
    try:
        db.execute(text("SELECT messages_migrated FROM chat LIMIT 0"))
        db.execute(text("SELECT chat_id FROM chat_message LIMIT 0"))
        _chat_message_table_supported_cache = True
    except Exception:
        _chat_message_table_supported_cache = False
    return _chat_message_table_supported_cache


def _is_chat_migrated(db, chat_id: str) -> bool:
    """Probe whether one chat is migrated to the chat_message table.

    Cheap UPDATE/INSERT paths read this once per call; the table-presence
    check is cached so the only DB work is the per-chat lookup."""
    if not _chat_message_table_supported(db):
        return False
    try:
        row = db.execute(
            text("SELECT messages_migrated FROM chat WHERE id = :id"),
            {"id": chat_id},
        ).fetchone()
        return bool(row and row[0])
    except Exception:
        return False


# Column order used by every SELECT against chat_message — keep in sync
# with `_row_to_message_dict`.
_CHAT_MESSAGE_SELECT_COLS = (
    "message_id, parent_id, role, content, content_is_json, "
    "model, timestamp, status_history, meta"
)


def _row_to_message_dict(row) -> dict:
    """Convert one chat_message row tuple (matching _CHAT_MESSAGE_SELECT_COLS)
    into the JSON-shape message dict used by the API and the legacy
    ``history.messages`` map."""
    mid = row[0]
    parent_id = row[1]
    role = row[2]
    content_raw = row[3]
    is_json = row[4]
    model = row[5]
    ts = row[6]
    status_history_raw = row[7]
    meta_raw = row[8]

    if is_json and isinstance(content_raw, str):
        try:
            content = json.loads(content_raw)
        except Exception:
            content = content_raw
    else:
        content = content_raw if content_raw is not None else ""

    msg: dict = {
        "id": mid,
        "role": role or "",
        "content": content,
    }
    if parent_id is not None:
        msg["parentId"] = parent_id
    if model:
        msg["model"] = model
    if ts is not None:
        msg["timestamp"] = ts
    if status_history_raw:
        try:
            msg["statusHistory"] = json.loads(status_history_raw)
        except Exception:
            pass
    if meta_raw:
        try:
            extra = json.loads(meta_raw)
            if isinstance(extra, dict):
                # Don't let meta clobber the dedicated columns.
                for k, v in extra.items():
                    if k not in msg:
                        msg[k] = v
        except Exception:
            pass
    return msg


def _chat_messages_from_table(db, chat_id: str) -> dict:
    """Reconstruct ``{message_id: message_dict}`` from chat_message rows for
    the given chat. Ordered by ``sequence`` so the dict iteration order
    matches the original message order.

    Returns ``{}`` if the chat has no rows (or the table isn't there)."""
    if not _chat_message_table_supported(db):
        return {}
    try:
        rows = db.execute(
            text(
                f"SELECT {_CHAT_MESSAGE_SELECT_COLS} "
                "FROM chat_message WHERE chat_id = :cid ORDER BY sequence"
            ),
            {"cid": chat_id},
        ).fetchall()
    except Exception:
        return {}
    return {r[0]: _row_to_message_dict(r) for r in rows}


def _hydrate_chat_messages(db, chat_obj) -> None:
    """If ``chat_obj`` is migrated, populate
    ``chat_obj.chat['history']['messages']`` from the chat_message table so
    callers that read the JSON shape continue to work. No-op for unmigrated
    chats (their JSON blob still holds the messages)."""
    if chat_obj is None:
        return
    # `chat_obj` is a SQLAlchemy ORM row; the messages_migrated attribute
    # might be missing on older sessions, so check defensively.
    try:
        migrated = bool(getattr(chat_obj, "messages_migrated", 0))
    except Exception:
        migrated = False
    if not migrated:
        return
    try:
        msgs = _chat_messages_from_table(db, chat_obj.id)
    except Exception:
        return
    # Modify the dict in place. SQLAlchemy may flush this back on commit;
    # since the messages_migrated flag will gate further writes there's no
    # risk of stale data, but we only mutate the in-memory dict that's about
    # to be serialized for the caller.
    chat_dict = chat_obj.chat if isinstance(chat_obj.chat, dict) else {}
    history = chat_dict.get("history") if isinstance(chat_dict.get("history"), dict) else {}
    history["messages"] = msgs
    if "currentId" not in history and msgs:
        # Fall back to the last-inserted message_id if currentId is missing.
        history["currentId"] = next(reversed(msgs))
    chat_dict["history"] = history
    chat_obj.chat = chat_dict


def _peel_messages_off_chat_dict(
    chat_data: dict,
) -> tuple[dict, Optional[dict]]:
    """If ``chat_data['history']['messages']`` is a dict, return a copy of
    ``chat_data`` with that key removed along with the popped messages.
    Otherwise return ``(chat_data, None)``.

    Used by every write path that puts messages in the chat_message table
    so the on-disk JSON blob stays small."""
    if not isinstance(chat_data, dict):
        return chat_data, None
    history_in = chat_data.get("history") or {}
    msgs = history_in.get("messages") if isinstance(history_in, dict) else None
    if not isinstance(msgs, dict):
        return chat_data, None
    stored = dict(chat_data)
    stored_history = dict(history_in)
    stored_history.pop("messages", None)
    stored["history"] = stored_history
    return stored, msgs


def _next_sequence_for_chat(db, chat_id: str) -> int:
    """Return one past the current max(sequence) for the chat — the value to
    use for an INSERTed new message."""
    try:
        row = db.execute(
            text("SELECT COALESCE(MAX(sequence), -1) + 1 FROM chat_message WHERE chat_id = :cid"),
            {"cid": chat_id},
        ).fetchone()
        return int(row[0]) if row else 0
    except Exception:
        return 0


def _split_message_for_table(message: dict) -> dict:
    """Slice an incoming message dict into the column shape used by
    chat_message. Returns a kwargs dict ready for INSERT/UPDATE binds."""
    content = message.get("content", "")
    is_json = 0
    if not isinstance(content, str):
        try:
            content = json.dumps(content)
            is_json = 1
        except Exception:
            content = ""
            is_json = 0

    ts_raw = message.get("timestamp")
    try:
        ts = int(ts_raw) if ts_raw is not None and ts_raw != "" else None
    except (TypeError, ValueError):
        ts = None

    parent_id = message.get("parentId")
    if parent_id is not None:
        parent_id = str(parent_id)

    model = message.get("model")
    model_str = str(model) if model else None

    status_history = message.get("statusHistory")
    status_history_json = (
        json.dumps(status_history) if status_history is not None else None
    )

    meta = {
        k: v
        for k, v in message.items()
        if k
        not in (
            "id",
            "parentId",
            "role",
            "content",
            "model",
            "timestamp",
            "statusHistory",
        )
    }
    meta_json = json.dumps(meta) if meta else None

    return {
        "parent_id": parent_id,
        "role": str(message.get("role", "")) or None,
        "content": content,
        "content_is_json": is_json,
        "model": model_str,
        "timestamp": ts,
        "status_history": status_history_json,
        "meta": meta_json,
    }


# FTS query characters that need to be stripped to avoid breaking the parser.
# Keep `"` for quoted phrases and `-` for negation - those are handled by the
# parser below.
_FTS_SPECIAL = set('():\\*~^')

# Words shorter than this are dropped from FTS queries (FTS5 ignores them
# anyway but skipping client-side keeps the parser clean).
_FTS_MIN_TOKEN_LEN = 2

_GENERIC_TITLES = {
    "",
    "new chat",
    "untitled",
    "untitled chat",
}


def _tokenize_user_query(text: str) -> list[tuple[str, str]]:
    """Split user query into ('phrase'|'word', payload) tuples.

    Quoted phrases are preserved verbatim — FTS5's tokenizer handles
    in-phrase punctuation correctly. Unquoted text is split on whitespace
    *and* on FTS5's word-separator punctuation (`.`, `,`, `/`, `@`, ...), so
    `vast.ai` becomes the two tokens [`vast`, `ai`] rather than a
    syntactically-invalid FTS5 expression.
    """
    out: list[tuple[str, str]] = []
    cur: list[str] = []
    in_q = False
    for ch in text:
        if ch == '"':
            if cur:
                out.append(("phrase" if in_q else "word", "".join(cur)))
                cur = []
            in_q = not in_q
        elif not in_q and (ch.isspace() or ch in _FTS_WORD_SPLITTERS):
            if cur:
                out.append(("word", "".join(cur)))
                cur = []
        else:
            cur.append(ch)
    if cur:
        out.append(("phrase" if in_q else "word", "".join(cur)))
    return out


def _clean_fts_token(s: str) -> str:
    """Strip FTS5 operator chars from a token. For a *single* word; callers
    that need to split punctuation-bearing words into multiple tokens should
    go through _tokenize_user_query."""
    return "".join(c for c in s if c not in _FTS_SPECIAL).strip()


# Characters that FTS5's query parser treats as operators or that bear special
# meaning. We pre-split user queries on them so an innocuous user-typed string
# like ``vast.ai`` or ``key-value`` never reaches the parser as a bare ``.``
# or ``-`` (which would be a NOT operator). Underscore stays in — that's the
# one tokenchar we kept in the FTS schema for ``snake_case`` identifiers.
_FTS_WORD_SPLITTERS = set(".,;:!?'\"`/\\@#$%&|()[]{}<>=+~^*-")


def _build_fts_queries(search_text: str) -> tuple[str, str, str]:
    """Return (primary, prefix, fuzzy) FTS5-safe query strings.

    primary  - tokens joined with implicit AND, quoted phrases preserved
    prefix   - same but each unquoted token gets a `*` suffix
    fuzzy    - trigrams OR'd together for the trigram-tokenized index. We
               can't just pass the raw text because FTS5's trigram tokenizer
               treats the query as a *phrase* of trigrams - so `fastpi`
               (trigrams: fas, ast, stp, tpi) never matches `fastapi`
               (trigrams: fas, ast, sta, tap, api) even though the words are
               obviously similar. Decomposing into OR'd trigrams + BM25
               ranking gives the "did you mean" behaviour we want.
    """
    tokens = _tokenize_user_query(search_text)
    primary, prefix, fuzzy_words = [], [], []
    for kind, t in tokens:
        c = _clean_fts_token(t)
        if len(c) < _FTS_MIN_TOKEN_LEN:
            continue
        if kind == "phrase":
            quoted = f'"{c}"'
            primary.append(quoted)
            prefix.append(quoted)
            fuzzy_words.append(c)
        else:
            primary.append(c)
            prefix.append(f"{c}*")
            fuzzy_words.append(c)
    fuzzy_query = _build_trigram_or_query(" ".join(fuzzy_words))
    return (" ".join(primary), " ".join(prefix), fuzzy_query)


def _build_trigram_or_query(text: str) -> str:
    """Decompose ``text`` into unique trigrams joined with OR.

    Trigram matching in FTS5 normally requires the indexed value to contain
    *every* trigram of the query in order. That's too strict for the
    "did you mean" use case; OR'ing the trigrams lets BM25 rank by overlap."""
    grams: list[str] = []
    seen: set[str] = set()
    for word in (text or "").lower().split():
        # Strip FTS specials so the OR'd trigrams don't accidentally re-enter
        # the FTS5 query parser as operators.
        cleaned = _clean_fts_token(word)
        if not cleaned:
            continue
        if len(cleaned) < 3:
            if cleaned not in seen:
                grams.append(cleaned)
                seen.add(cleaned)
            continue
        for i in range(len(cleaned) - 2):
            g = cleaned[i : i + 3]
            if g not in seen:
                grams.append(g)
                seen.add(g)
    return " OR ".join(grams)


def _strip_prefix_syntax(search_text: str, user_id: str) -> tuple[
    list[str], list[str], Optional[bool], Optional[bool], Optional[bool], str
]:
    """Pull out hidden `tag:` / `folder:` / `pinned:` / `archived:` / `shared:`
    qualifiers from the raw text and return (tag_ids, folder_ids,
    pinned, archived, shared, remaining_text)."""
    words = search_text.split(" ")
    tag_ids = [
        w.replace("tag:", "").replace(" ", "_").lower()
        for w in words
        if w.startswith("tag:")
    ]
    folder_names = [w.replace("folder:", "") for w in words if w.startswith("folder:")]
    folders = Folders.search_folders_by_names(user_id, folder_names) if folder_names else []
    folder_ids = [f.id for f in folders]

    pinned: Optional[bool] = None
    if "pinned:true" in words:
        pinned = True
    elif "pinned:false" in words:
        pinned = False

    archived: Optional[bool] = None
    if "archived:true" in words:
        archived = True
    elif "archived:false" in words:
        archived = False

    shared: Optional[bool] = None
    if "shared:true" in words:
        shared = True
    elif "shared:false" in words:
        shared = False

    remaining = " ".join(
        w
        for w in words
        if not (
            w.startswith("tag:")
            or w.startswith("folder:")
            or w.startswith("pinned:")
            or w.startswith("archived:")
            or w.startswith("shared:")
        )
    ).strip()
    return (tag_ids, folder_ids, pinned, archived, shared, remaining)


def _escape_html_text(s: str) -> str:
    """HTML-escape user content for safe interpolation alongside <mark>."""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# FTS5 emits real `<mark>` and `</mark>` tags around hits. We HTML-escape
# everything else after the fact by splitting on the mark tags, escaping the
# segments, then re-joining. This is XSS-safe and trivial.
def _sanitize_snippet(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    parts = raw.split("<mark>")
    out: list[str] = []
    for i, part in enumerate(parts):
        if i == 0:
            out.append(_escape_html_text(part))
            continue
        inner, _, after = part.partition("</mark>")
        out.append("<mark>")
        out.append(_escape_html_text(inner))
        out.append("</mark>")
        out.append(_escape_html_text(after))
    return "".join(out)


def _apply_subagent_filter(query, db, include_subagents: bool):
    """Filter out chats whose ``meta`` carries ``subagent_of`` — those are
    research subagent chats spawned by the parent chat model and are hidden
    from the user's main chat list / search / pinned / archived views by
    default. Pass ``include_subagents=True`` to opt a query into seeing them
    (e.g. a future "Subagents" admin page)."""
    if include_subagents:
        return query
    dialect = db.bind.dialect.name
    if dialect == "sqlite":
        # json_extract returns NULL when the path doesn't exist; pre-existing
        # rows have no `subagent_of` key so they pass through cleanly.
        return query.filter(
            text("(json_extract(Chat.meta, '$.subagent_of') IS NULL)")
        )
    if dialect == "postgresql":
        return query.filter(text("(Chat.meta->>'subagent_of' IS NULL)"))
    raise NotImplementedError(
        f"Unsupported dialect for subagent filter: {dialect}"
    )


class ChatTable:
    def _enrich_chat_data(self, chat_data: dict) -> dict:
        """
        Enrich chat data with computed fields for better UX.
        - Auto-generate title from first user message if not provided
        - Populate model field on all messages in history
        """
        chat_data = chat_data.copy()

        # Auto-generate title from first user message if no title provided
        if not chat_data.get("title") or chat_data.get("title") == "New Chat":
            # Try to get title from messages
            messages = chat_data.get("messages", [])
            if messages:
                for msg in messages:
                    if msg.get("role") == "user":
                        content = msg.get("content", "")
                        if content:
                            # Take first 50 chars of first user message
                            if len(content) > 50:
                                chat_data["title"] = content[:50] + "..."
                            else:
                                chat_data["title"] = content
                            break

        # Populate model field on all messages if models array exists
        models = chat_data.get("models", [])
        if models and len(models) > 0:
            default_model = models[0]  # Use first model as default

            # Populate model in history messages
            if "history" in chat_data and "messages" in chat_data["history"]:
                for msg_id, msg in chat_data["history"]["messages"].items():
                    if "model" not in msg or not msg["model"]:
                        msg["model"] = default_model

            # Populate model in messages array (fallback structure)
            if "messages" in chat_data:
                for msg in chat_data["messages"]:
                    if msg.get("role") == "assistant" and ("model" not in msg or not msg["model"]):
                        msg["model"] = default_model

        return chat_data

    def insert_new_chat(self, user_id: str, form_data: ChatForm) -> Optional[ChatModel]:
        with get_db() as db:
            id = str(uuid.uuid4())

            # Enrich chat data before storing
            enriched_chat = self._enrich_chat_data(form_data.chat)

            title = enriched_chat.get("title", "New Chat")

            # New chats are born migrated when the new table is available so
            # all subsequent writes go through the fast row-level path.
            born_migrated = _chat_message_table_supported(db)
            if born_migrated:
                stored_chat, init_messages = _peel_messages_off_chat_dict(enriched_chat)
            else:
                stored_chat, init_messages = enriched_chat, None

            chat_kwargs = {
                "id": id,
                "user_id": user_id,
                "title": title,
                "chat": stored_chat,
                "folder_id": form_data.folder_id,
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
            }
            chat = ChatModel(**chat_kwargs)

            result = Chat(**chat.model_dump())
            if born_migrated:
                result.messages_migrated = 1
            db.add(result)
            db.commit()
            db.refresh(result)

            if born_migrated and init_messages:
                self._sync_messages_to_table(db, id, init_messages)
                try:
                    db.commit()
                except Exception:
                    pass

            # Update search_text via raw SQL (column not in ORM to avoid breaking queries before migration)
            try:
                db.execute(
                    text("UPDATE chat SET search_text = :st WHERE id = :id"),
                    {"st": _build_search_text(title, enriched_chat), "id": id},
                )
                db.commit()
            except Exception:
                pass  # Column doesn't exist yet (migration pending)

            _upsert_chat_fts(db, id, title, enriched_chat)
            try:
                db.commit()
            except Exception:
                pass

            _hydrate_chat_messages(db, result)
            return ChatModel.model_validate(result) if result else None

    def import_chat(
        self, user_id: str, form_data: ChatImportForm
    ) -> Optional[ChatModel]:
        with get_db() as db:
            id = str(uuid.uuid4())
            import_title = form_data.chat.get("title", "New Chat")

            born_migrated = _chat_message_table_supported(db)
            if born_migrated:
                stored_chat, init_messages = _peel_messages_off_chat_dict(form_data.chat)
            else:
                stored_chat, init_messages = form_data.chat, None

            chat = ChatModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "title": import_title,
                    "chat": stored_chat,
                    "meta": form_data.meta,
                    "pinned": form_data.pinned,
                    "folder_id": form_data.folder_id,
                    "created_at": (
                        form_data.created_at
                        if form_data.created_at
                        else int(time.time())
                    ),
                    "updated_at": (
                        form_data.updated_at
                        if form_data.updated_at
                        else int(time.time())
                    ),
                }
            )

            result = Chat(**chat.model_dump())
            if born_migrated:
                result.messages_migrated = 1
            db.add(result)
            db.commit()
            db.refresh(result)

            if born_migrated and init_messages:
                self._sync_messages_to_table(db, id, init_messages)
                try:
                    db.commit()
                except Exception:
                    pass

            try:
                db.execute(
                    text("UPDATE chat SET search_text = :st WHERE id = :id"),
                    {"st": _build_search_text(import_title, form_data.chat), "id": id},
                )
                db.commit()
            except Exception:
                pass

            _upsert_chat_fts(db, id, import_title, form_data.chat)
            try:
                db.commit()
            except Exception:
                pass

            _hydrate_chat_messages(db, result)
            return ChatModel.model_validate(result) if result else None

    def update_chat_by_id(self, id: str, chat: dict) -> Optional[ChatModel]:
        try:
            with get_db() as db:
                chat_item = db.get(Chat, id)

                # Enrich chat data before updating
                enriched_chat = self._enrich_chat_data(chat)

                migrated = bool(
                    _chat_message_table_supported(db)
                    and getattr(chat_item, "messages_migrated", 0)
                )

                # For migrated chats, sync the messages dict to the
                # chat_message table and strip them out of the on-disk JSON
                # so the blob stays small. The hydrate path will re-attach
                # them on read.
                stored_chat = enriched_chat
                if migrated:
                    peeled_chat, peeled_msgs = _peel_messages_off_chat_dict(enriched_chat)
                    if peeled_msgs is not None:
                        self._sync_messages_to_table(db, id, peeled_msgs)
                        stored_chat = peeled_chat

                title = enriched_chat.get("title", "New Chat")
                chat_item.chat = stored_chat
                chat_item.title = title
                chat_item.updated_at = int(time.time())
                db.commit()
                db.refresh(chat_item)

                try:
                    db.execute(
                        text("UPDATE chat SET search_text = :st WHERE id = :id"),
                        {"st": _build_search_text(title, enriched_chat), "id": id},
                    )
                    db.commit()
                except Exception:
                    pass

                _upsert_chat_fts(db, id, title, enriched_chat)
                try:
                    db.commit()
                except Exception:
                    pass

                _hydrate_chat_messages(db, chat_item)
                return ChatModel.model_validate(chat_item)
        except Exception:
            return None

    def _sync_messages_to_table(
        self, db, chat_id: str, messages: dict
    ) -> None:
        """Replace every chat_message row for ``chat_id`` with the given dict.

        Done as: DELETE then bulk INSERT, ordered by dict iteration order so
        ``sequence`` matches the on-disk layout. Keeping this O(N) is fine
        because ``update_chat_by_id`` is only a hot path for legacy callers;
        the per-message upsert path uses the fast row-level write.
        """
        if not _chat_message_table_supported(db):
            return
        try:
            db.execute(
                text("DELETE FROM chat_message WHERE chat_id = :cid"),
                {"cid": chat_id},
            )
            for seq, (mid, msg) in enumerate(messages.items()):
                if not isinstance(msg, dict):
                    continue
                cols = _split_message_for_table(msg)
                db.execute(
                    text(
                        "INSERT INTO chat_message "
                        "(chat_id, message_id, parent_id, role, content, "
                        " content_is_json, model, timestamp, sequence, "
                        " status_history, meta) "
                        "VALUES (:cid, :mid, :pid, :role, :c, :ij, "
                        ":model, :ts, :seq, :sh, :meta)"
                    ),
                    {
                        "cid": chat_id,
                        "mid": str(mid),
                        "pid": cols["parent_id"],
                        "role": cols["role"],
                        "c": cols["content"],
                        "ij": cols["content_is_json"],
                        "model": cols["model"],
                        "ts": cols["timestamp"],
                        "seq": seq,
                        "sh": cols["status_history"],
                        "meta": cols["meta"],
                    },
                )
        except Exception:
            # If anything goes wrong, let the JSON path retain the messages —
            # we don't disturb messages_migrated, just the table sync.
            pass

    def update_chat_title_by_id(self, id: str, title: str) -> Optional[ChatModel]:
        # Targeted title-only update: doesn't touch the messages table or
        # the on-disk JSON body beyond the title key, so it's O(1) regardless
        # of chat size.
        try:
            with get_db() as db:
                chat_item = db.get(Chat, id)
                if chat_item is None:
                    return None

                # Update the title on both the column and inside the JSON
                # blob so old code paths reading chat.chat['title'] keep
                # working.
                if db.bind.dialect.name == "sqlite":
                    db.execute(
                        text(
                            "UPDATE chat SET "
                            "  title = :t, "
                            "  chat = json_set(chat, '$.title', :t), "
                            "  updated_at = :ts "
                            "WHERE id = :id"
                        ),
                        {"t": title, "ts": int(time.time()), "id": id},
                    )
                    db.commit()
                    db.refresh(chat_item)
                else:
                    # Fall back to the legacy round-trip on dialects without
                    # json_set support; rare enough to not matter.
                    cur = (
                        copy.deepcopy(chat_item.chat)
                        if isinstance(chat_item.chat, dict)
                        else {}
                    )
                    cur["title"] = title
                    chat_item.chat = cur
                    chat_item.title = title
                    chat_item.updated_at = int(time.time())
                    db.commit()
                    db.refresh(chat_item)

                try:
                    db.execute(
                        text("UPDATE chat SET search_text = :st WHERE id = :id"),
                        {
                            "st": _build_search_text(
                                title,
                                chat_item.chat if isinstance(chat_item.chat, dict) else {},
                            ),
                            "id": id,
                        },
                    )
                    db.commit()
                except Exception:
                    pass

                # Title changes need an FTS refresh too (chat_fts.title column).
                _upsert_chat_fts(
                    db, id, title, chat_item.chat if isinstance(chat_item.chat, dict) else {}
                )
                try:
                    db.commit()
                except Exception:
                    pass

                _hydrate_chat_messages(db, chat_item)
                return ChatModel.model_validate(chat_item)
        except Exception:
            return None

    def update_chat_tags_by_id(
        self, id: str, tags: list[str], user
    ) -> Optional[ChatModel]:
        chat = self.get_chat_by_id(id)
        if chat is None:
            return None

        self.delete_all_tags_by_id_and_user_id(id, user.id)

        for tag in chat.meta.get("tags", []):
            if self.count_chats_by_tag_name_and_user_id(tag, user.id) == 0:
                Tags.delete_tag_by_name_and_user_id(tag, user.id)

        for tag_name in tags:
            if tag_name.lower() == "none":
                continue

            self.add_chat_tag_by_id_and_user_id_and_tag_name(id, user.id, tag_name)
        return self.get_chat_by_id(id)

    def get_chat_title_by_id(self, id: str) -> Optional[str]:
        chat = self.get_chat_by_id(id)
        if chat is None:
            return None

        return chat.chat.get("title", "New Chat")

    def get_messages_map_by_chat_id(self, id: str) -> Optional[dict]:
        chat = self.get_chat_by_id(id)
        if chat is None:
            return None

        return chat.chat.get("history", {}).get("messages", {}) or {}

    def get_message_by_id_and_message_id(
        self, id: str, message_id: str
    ) -> Optional[dict]:
        chat = self.get_chat_by_id(id)
        if chat is None:
            return None

        return chat.chat.get("history", {}).get("messages", {}).get(message_id, {})

    def upsert_message_to_chat_by_id_and_message_id(
        self, id: str, message_id: str, message: dict
    ) -> Optional[ChatModel]:
        # Sanitize message content for null characters before upserting
        if isinstance(message.get("content"), str):
            message["content"] = message["content"].replace("\x00", "")

        with get_db() as db:
            chat_obj = db.get(Chat, id)
            if chat_obj is None:
                return None

            migrated = bool(
                _chat_message_table_supported(db)
                and getattr(chat_obj, "messages_migrated", 0)
            )

            if migrated:
                # Fast path: write a single row to chat_message instead of a
                # full JSON read-modify-write. Look up the existing row (if
                # any) so we can spread the incoming partial dict on top —
                # same merge semantics as the legacy ``{**existing, **incoming}``.
                existing_row = db.execute(
                    text(
                        f"SELECT {_CHAT_MESSAGE_SELECT_COLS} "
                        "FROM chat_message WHERE chat_id = :cid AND message_id = :mid"
                    ),
                    {"cid": id, "mid": message_id},
                ).fetchone()

                if existing_row is None:
                    merged = dict(message)
                    merged["id"] = message_id
                    seq = _next_sequence_for_chat(db, id)
                    cols = _split_message_for_table(merged)
                    db.execute(
                        text(
                            "INSERT INTO chat_message "
                            "(chat_id, message_id, parent_id, role, content, "
                            " content_is_json, model, timestamp, sequence, "
                            " status_history, meta) "
                            "VALUES (:cid, :mid, :pid, :role, :c, :ij, "
                            ":model, :ts, :seq, :sh, :meta)"
                        ),
                        {
                            "cid": id,
                            "mid": message_id,
                            "seq": seq,
                            "pid": cols["parent_id"],
                            "role": cols["role"],
                            "c": cols["content"],
                            "ij": cols["content_is_json"],
                            "model": cols["model"],
                            "ts": cols["timestamp"],
                            "sh": cols["status_history"],
                            "meta": cols["meta"],
                        },
                    )
                else:
                    existing_msg = _row_to_message_dict(existing_row)
                    merged = {**existing_msg, **message}
                    merged["id"] = message_id
                    cols = _split_message_for_table(merged)
                    db.execute(
                        text(
                            "UPDATE chat_message SET "
                            "  parent_id = :pid, "
                            "  role = :role, "
                            "  content = :c, "
                            "  content_is_json = :ij, "
                            "  model = :model, "
                            "  timestamp = :ts, "
                            "  status_history = :sh, "
                            "  meta = :meta "
                            "WHERE chat_id = :cid AND message_id = :mid"
                        ),
                        {
                            "cid": id,
                            "mid": message_id,
                            "pid": cols["parent_id"],
                            "role": cols["role"],
                            "c": cols["content"],
                            "ij": cols["content_is_json"],
                            "model": cols["model"],
                            "ts": cols["timestamp"],
                            "sh": cols["status_history"],
                            "meta": cols["meta"],
                        },
                    )

                _upsert_message_fts(
                    db,
                    id,
                    message_id,
                    merged.get("role"),
                    _extract_content_text(merged.get("content", "")),
                )

                # Targeted JSON manipulation: only flip history.currentId so
                # the on-disk JSON stays consistent for the unmigrated read
                # path that might be re-enabled. Avoid touching the rest of
                # the 100+ MB JSON blob.
                try:
                    if db.bind.dialect.name == "sqlite":
                        db.execute(
                            text(
                                "UPDATE chat SET "
                                "  chat = json_set(chat, '$.history.currentId', :mid), "
                                "  updated_at = :ts "
                                "WHERE id = :id"
                            ),
                            {"mid": message_id, "ts": int(time.time()), "id": id},
                        )
                    else:
                        # Non-SQLite (or any dialect that doesn't support
                        # json_set in this exact form): fall back to a
                        # minimal read-modify-write of just the scaffolding.
                        cur_chat = chat_obj.chat if isinstance(chat_obj.chat, dict) else {}
                        cur_history = cur_chat.get("history") or {}
                        if not isinstance(cur_history, dict):
                            cur_history = {}
                        cur_history["currentId"] = message_id
                        # Don't pull message bodies; the source of truth is
                        # the chat_message table and `_hydrate_chat_messages`
                        # rebuilds the dict on read.
                        cur_history.pop("messages", None)
                        cur_chat["history"] = cur_history
                        chat_obj.chat = cur_chat
                        chat_obj.updated_at = int(time.time())
                except Exception:
                    # As a final fallback, just bump updated_at via UPDATE.
                    try:
                        db.execute(
                            text("UPDATE chat SET updated_at = :ts WHERE id = :id"),
                            {"ts": int(time.time()), "id": id},
                        )
                    except Exception:
                        pass

                try:
                    db.commit()
                except Exception:
                    db.rollback()
                    return None

                refreshed = db.get(Chat, id)
                _hydrate_chat_messages(db, refreshed)
                try:
                    return ChatModel.model_validate(refreshed)
                except Exception:
                    return None

            # Legacy path: unmigrated chat. Do the old read-modify-write.
            # Deep-copy before mutating so SQLAlchemy detects the JSON column
            # change in the downstream update_chat_by_id call. (Mutating the
            # ORM-attached dict in place leaves the new and old values equal
            # by reference, so the dirty-check skips the flush.)
            chat_dict = (
                copy.deepcopy(chat_obj.chat) if isinstance(chat_obj.chat, dict) else {}
            )
            history = chat_dict.get("history", {})
            if not isinstance(history, dict):
                history = {}
            if "messages" not in history or not isinstance(history["messages"], dict):
                history["messages"] = {}

            if message_id in history["messages"]:
                history["messages"][message_id] = {
                    **history["messages"][message_id],
                    **message,
                }
            else:
                history["messages"][message_id] = message

            history["currentId"] = message_id
            chat_dict["history"] = history

        # Outside the with-block: update_chat_by_id opens its own session.
        return self.update_chat_by_id(id, chat_dict)

    def add_message_status_to_chat_by_id_and_message_id(
        self, id: str, message_id: str, status: dict
    ) -> Optional[ChatModel]:
        with get_db() as db:
            chat_obj = db.get(Chat, id)
            if chat_obj is None:
                return None

            migrated = bool(
                _chat_message_table_supported(db)
                and getattr(chat_obj, "messages_migrated", 0)
            )

            if migrated:
                # Update only the status_history column on the chat_message row.
                row = db.execute(
                    text(
                        "SELECT status_history FROM chat_message "
                        "WHERE chat_id = :cid AND message_id = :mid"
                    ),
                    {"cid": id, "mid": message_id},
                ).fetchone()
                if row is None:
                    # Message doesn't exist; nothing to update.
                    return ChatModel.model_validate(chat_obj)
                cur_sh: list = []
                if row[0]:
                    try:
                        parsed = json.loads(row[0])
                        if isinstance(parsed, list):
                            cur_sh = parsed
                    except Exception:
                        cur_sh = []
                cur_sh.append(status)
                db.execute(
                    text(
                        "UPDATE chat_message SET status_history = :sh "
                        "WHERE chat_id = :cid AND message_id = :mid"
                    ),
                    {"sh": json.dumps(cur_sh), "cid": id, "mid": message_id},
                )
                try:
                    db.commit()
                except Exception:
                    db.rollback()
                    return None
                refreshed = db.get(Chat, id)
                _hydrate_chat_messages(db, refreshed)
                try:
                    return ChatModel.model_validate(refreshed)
                except Exception:
                    return None

            # Legacy path — deep-copy to defeat the JSON-column dirty-check
            # short-circuit (see notes in upsert_message_to_chat_by_id_and_message_id).
            chat_dict = (
                copy.deepcopy(chat_obj.chat) if isinstance(chat_obj.chat, dict) else {}
            )
            history = chat_dict.get("history", {})
            if not isinstance(history, dict):
                history = {}

            if isinstance(history.get("messages"), dict) and message_id in history["messages"]:
                status_history = history["messages"][message_id].get("statusHistory", [])
                status_history.append(status)
                history["messages"][message_id]["statusHistory"] = status_history

            chat_dict["history"] = history

        return self.update_chat_by_id(id, chat_dict)

    def insert_shared_chat_by_chat_id(self, chat_id: str) -> Optional[ChatModel]:
        with get_db() as db:
            # Get the existing chat to share
            chat = db.get(Chat, chat_id)
            # Hydrate before reading chat.chat so the shared clone gets the
            # real messages (otherwise migrated chats would share an empty
            # history because the on-disk JSON has no messages dict).
            _hydrate_chat_messages(db, chat)
            # Check if the chat is already shared
            if chat.share_id:
                return self.get_chat_by_id_and_user_id(chat.share_id, "shared")
            # Create a new chat with the same data, but with a new ID
            shared_chat = ChatModel(
                **{
                    "id": str(uuid.uuid4()),
                    "user_id": f"shared-{chat_id}",
                    "title": chat.title,
                    "chat": chat.chat,
                    "meta": chat.meta,
                    "pinned": chat.pinned,
                    "folder_id": chat.folder_id,
                    "created_at": chat.created_at,
                    "updated_at": int(time.time()),
                }
            )
            shared_result = Chat(**shared_chat.model_dump())
            db.add(shared_result)
            db.commit()
            db.refresh(shared_result)

            # Update the original chat with the share_id
            result = (
                db.query(Chat)
                .filter_by(id=chat_id)
                .update({"share_id": shared_chat.id})
            )
            db.commit()
            return shared_chat if (shared_result and result) else None

    def update_shared_chat_by_chat_id(self, chat_id: str) -> Optional[ChatModel]:
        try:
            with get_db() as db:
                chat = db.get(Chat, chat_id)
                _hydrate_chat_messages(db, chat)
                shared_chat = (
                    db.query(Chat).filter_by(user_id=f"shared-{chat_id}").first()
                )

                if shared_chat is None:
                    return self.insert_shared_chat_by_chat_id(chat_id)

                shared_chat.title = chat.title
                shared_chat.chat = chat.chat
                shared_chat.meta = chat.meta
                shared_chat.pinned = chat.pinned
                shared_chat.folder_id = chat.folder_id
                shared_chat.updated_at = int(time.time())
                db.commit()
                db.refresh(shared_chat)

                return ChatModel.model_validate(shared_chat)
        except Exception:
            return None

    def delete_shared_chat_by_chat_id(self, chat_id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Chat).filter_by(user_id=f"shared-{chat_id}").delete()
                db.commit()

                return True
        except Exception:
            return False

    def unarchive_all_chats_by_user_id(self, user_id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Chat).filter_by(user_id=user_id).update({"archived": False})
                db.commit()
                return True
        except Exception:
            return False

    def update_chat_share_id_by_id(
        self, id: str, share_id: Optional[str]
    ) -> Optional[ChatModel]:
        try:
            with get_db() as db:
                chat = db.get(Chat, id)
                chat.share_id = share_id
                db.commit()
                db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    def toggle_chat_pinned_by_id(self, id: str) -> Optional[ChatModel]:
        try:
            with get_db() as db:
                chat = db.get(Chat, id)
                chat.pinned = not chat.pinned
                chat.updated_at = int(time.time())
                db.commit()
                db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    def toggle_chat_archive_by_id(self, id: str) -> Optional[ChatModel]:
        try:
            with get_db() as db:
                chat = db.get(Chat, id)
                chat.archived = not chat.archived
                chat.updated_at = int(time.time())
                db.commit()
                db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    def archive_all_chats_by_user_id(self, user_id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Chat).filter_by(user_id=user_id).update({"archived": True})
                db.commit()
                return True
        except Exception:
            return False

    def get_archived_chat_list_by_user_id(
        self,
        user_id: str,
        filter: Optional[dict] = None,
        skip: int = 0,
        limit: int = 50,
        include_subagents: bool = False,
    ) -> list[ChatModel]:

        with get_db() as db:
            query = db.query(Chat).filter_by(user_id=user_id, archived=True)
            query = _apply_subagent_filter(query, db, include_subagents)

            if filter:
                query_key = filter.get("query")
                if query_key:
                    query = query.filter(Chat.title.ilike(f"%{query_key}%"))

                order_by = filter.get("order_by")
                direction = filter.get("direction")

                if order_by and direction and getattr(Chat, order_by):
                    if direction.lower() == "asc":
                        query = query.order_by(getattr(Chat, order_by).asc())
                    elif direction.lower() == "desc":
                        query = query.order_by(getattr(Chat, order_by).desc())
                    else:
                        raise ValueError("Invalid direction for ordering")
            else:
                query = query.order_by(Chat.updated_at.desc())

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            all_chats = query.all()
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_chat_list_by_user_id(
        self,
        user_id: str,
        include_archived: bool = False,
        filter: Optional[dict] = None,
        skip: int = 0,
        limit: int = 50,
        include_subagents: bool = False,
    ) -> list[ChatModel]:
        with get_db() as db:
            query = db.query(Chat).filter_by(user_id=user_id)
            if not include_archived:
                query = query.filter_by(archived=False)
            query = _apply_subagent_filter(query, db, include_subagents)

            if filter:
                query_key = filter.get("query")
                if query_key:
                    query = query.filter(Chat.title.ilike(f"%{query_key}%"))

                order_by = filter.get("order_by")
                direction = filter.get("direction")

                if order_by and direction and getattr(Chat, order_by):
                    if direction.lower() == "asc":
                        query = query.order_by(getattr(Chat, order_by).asc())
                    elif direction.lower() == "desc":
                        query = query.order_by(getattr(Chat, order_by).desc())
                    else:
                        raise ValueError("Invalid direction for ordering")
            else:
                query = query.order_by(Chat.updated_at.desc())

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            all_chats = query.all()
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_chat_title_id_list_by_user_id(
        self,
        user_id: str,
        include_archived: bool = False,
        include_folders: bool = False,
        include_pinned: bool = False,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
        include_subagents: bool = False,
    ) -> list[ChatTitleIdResponse]:
        with get_db() as db:
            query = db.query(Chat).filter_by(user_id=user_id)

            if not include_folders:
                query = query.filter_by(folder_id=None)

            if not include_pinned:
                query = query.filter(or_(Chat.pinned == False, Chat.pinned == None))

            if not include_archived:
                query = query.filter_by(archived=False)

            query = _apply_subagent_filter(query, db, include_subagents)

            query = query.order_by(Chat.updated_at.desc()).with_entities(
                Chat.id, Chat.title, Chat.updated_at, Chat.created_at
            )

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            all_chats = query.all()

            # result has to be destructured from sqlalchemy `row` and mapped to a dict since the `ChatModel`is not the returned dataclass.
            return [
                ChatTitleIdResponse.model_validate(
                    {
                        "id": chat[0],
                        "title": chat[1],
                        "updated_at": chat[2],
                        "created_at": chat[3],
                    }
                )
                for chat in all_chats
            ]

    def get_chat_list_by_chat_ids(
        self, chat_ids: list[str], skip: int = 0, limit: int = 50
    ) -> list[ChatModel]:
        with get_db() as db:
            all_chats = (
                db.query(Chat)
                .filter(Chat.id.in_(chat_ids))
                .filter_by(archived=False)
                .order_by(Chat.updated_at.desc())
                .all()
            )
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_chat_by_id(self, id: str) -> Optional[ChatModel]:
        try:
            with get_db() as db:
                chat = db.get(Chat, id)
                if chat is None:
                    return None
                _hydrate_chat_messages(db, chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    def get_chat_by_share_id(self, id: str) -> Optional[ChatModel]:
        try:
            with get_db() as db:
                # it is possible that the shared link was deleted. hence,
                # we check if the chat is still shared by checking if a chat with the share_id exists
                chat = db.query(Chat).filter_by(share_id=id).first()

                if chat:
                    return self.get_chat_by_id(chat.id)
                else:
                    return None
        except Exception:
            return None

    def get_chat_by_id_and_user_id(self, id: str, user_id: str) -> Optional[ChatModel]:
        try:
            with get_db() as db:
                chat = db.query(Chat).filter_by(id=id, user_id=user_id).first()
                if chat is None:
                    return None
                _hydrate_chat_messages(db, chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    def get_chat_messages_paginated(
        self, chat_id: str, skip: int = 0, limit: int = 100
    ) -> list[dict]:
        """Return a slice of messages for a chat, ordered by ``sequence``.

        Migrated chats: direct LIMIT/OFFSET on chat_message.
        Unmigrated chats: read the JSON blob and slice the dict's ordered
        values, so the API shape is identical regardless of storage path.
        """
        with get_db() as db:
            if _is_chat_migrated(db, chat_id):
                try:
                    rows = db.execute(
                        text(
                            f"SELECT {_CHAT_MESSAGE_SELECT_COLS} "
                            "FROM chat_message WHERE chat_id = :cid "
                            "ORDER BY sequence LIMIT :lim OFFSET :sk"
                        ),
                        {"cid": chat_id, "lim": int(limit), "sk": int(skip)},
                    ).fetchall()
                except Exception:
                    rows = []
                return [_row_to_message_dict(r) for r in rows]

            # Fallback: not migrated, or table missing. Slice the JSON blob.
            chat_obj = db.get(Chat, chat_id)
            if chat_obj is None:
                return []
            chat_dict = chat_obj.chat if isinstance(chat_obj.chat, dict) else {}
            history = chat_dict.get("history") if isinstance(chat_dict, dict) else None
            msgs = history.get("messages") if isinstance(history, dict) else None
            if isinstance(msgs, dict):
                items = list(msgs.values())
                return items[skip : skip + limit]
            if isinstance(chat_dict.get("messages"), list):
                return chat_dict["messages"][skip : skip + limit]
            return []

    def get_chats(self, skip: int = 0, limit: int = 50) -> list[ChatModel]:
        with get_db() as db:
            all_chats = (
                db.query(Chat)
                # .limit(limit).offset(skip)
                .order_by(Chat.updated_at.desc())
            )
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_chats_by_user_id(
        self, user_id: str, include_subagents: bool = False
    ) -> list[ChatModel]:
        with get_db() as db:
            query = db.query(Chat).filter_by(user_id=user_id)
            query = _apply_subagent_filter(query, db, include_subagents)
            all_chats = query.order_by(Chat.updated_at.desc())
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_pinned_chats_by_user_id(
        self, user_id: str, include_subagents: bool = False
    ) -> list[ChatModel]:
        with get_db() as db:
            query = db.query(Chat).filter_by(
                user_id=user_id, pinned=True, archived=False
            )
            query = _apply_subagent_filter(query, db, include_subagents)
            all_chats = query.order_by(Chat.updated_at.desc())
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_archived_chats_by_user_id(
        self, user_id: str, include_subagents: bool = False
    ) -> list[ChatModel]:
        with get_db() as db:
            query = db.query(Chat).filter_by(user_id=user_id, archived=True)
            query = _apply_subagent_filter(query, db, include_subagents)
            all_chats = query.order_by(Chat.updated_at.desc())
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def search_chats(
        self,
        user_id: str,
        search_text: str,
        *,
        folder_ids: Optional[list[str]] = None,
        tag_ids: Optional[list[str]] = None,
        pinned: Optional[bool] = None,
        archived: Optional[bool] = None,
        shared: Optional[bool] = None,
        updated_after: Optional[int] = None,
        updated_before: Optional[int] = None,
        sort: str = "relevance",
        skip: int = 0,
        limit: int = 30,
        include_subagents: bool = False,
    ) -> "ChatSearchResponse":
        """GOATED chat search.

        Three-tier FTS (primary AND-ish, prefix-expansion, trigram fuzzy) with
        dual-path ranking (chat_fts + message_fts), title-quality penalty, and
        recency decay. Returns ChatSearchResponse with snippets, match counts,
        and facet aggregates. Falls back to LIKE on non-SQLite dialects.
        """
        # Lowercase the entire query: FTS5's unicode61 tokenizer folds case at
        # index time anyway, and this lets the hidden `tag:` / `folder:` /
        # `pinned:` / `archived:` / `shared:` prefix detection work case-blind.
        raw_text = (search_text or "").replace("\u0000", "").strip().lower()

        # Hidden power-user prefix syntax
        extra_tags, extra_folders, p_pin, p_arc, p_shr, raw_text = _strip_prefix_syntax(
            raw_text, user_id
        )
        tag_ids = list(tag_ids or []) + extra_tags
        folder_ids = list(folder_ids or []) + extra_folders
        if pinned is None:
            pinned = p_pin
        if archived is None:
            archived = p_arc
        if shared is None:
            shared = p_shr

        with get_db() as db:
            if db.bind.dialect.name == "sqlite" and _fts_supported(db):
                return self._search_chats_sqlite_fts(
                    db,
                    user_id=user_id,
                    raw_text=raw_text,
                    folder_ids=folder_ids,
                    tag_ids=tag_ids,
                    pinned=pinned,
                    archived=archived,
                    shared=shared,
                    updated_after=updated_after,
                    updated_before=updated_before,
                    sort=sort,
                    skip=skip,
                    limit=limit,
                    include_subagents=include_subagents,
                )
            return self._search_chats_like_fallback(
                db,
                user_id=user_id,
                raw_text=raw_text,
                folder_ids=folder_ids,
                tag_ids=tag_ids,
                pinned=pinned,
                archived=archived,
                shared=shared,
                updated_after=updated_after,
                updated_before=updated_before,
                sort=sort,
                skip=skip,
                limit=limit,
                include_subagents=include_subagents,
            )

    def get_chats_by_user_id_and_search_text(
        self,
        user_id: str,
        search_text: str,
        include_archived: bool = False,
        skip: int = 0,
        limit: int = 60,
        include_subagents: bool = False,
    ) -> list[ChatModel]:
        """Legacy shim: adapt ``search_chats`` results to the older list shape
        that a few internal call sites still rely on."""
        archived_filter: Optional[bool] = None if include_archived else False
        resp = self.search_chats(
            user_id,
            search_text,
            archived=archived_filter,
            skip=skip,
            limit=limit,
            include_subagents=include_subagents,
        )
        if not resp.hits:
            return []
        with get_db() as db:
            ids = [h.id for h in resp.hits]
            order = {cid: i for i, cid in enumerate(ids)}
            rows = db.query(Chat).filter(Chat.id.in_(ids)).all()
            rows.sort(key=lambda r: order.get(r.id, 0))
            return [ChatModel.model_validate(r) for r in rows]

    def _build_chat_filter_sql(
        self,
        *,
        user_id: str,
        folder_ids: Optional[list[str]],
        tag_ids: Optional[list[str]],
        pinned: Optional[bool],
        archived: Optional[bool],
        shared: Optional[bool],
        updated_after: Optional[int],
        updated_before: Optional[int],
        include_subagents: bool,
        dialect: str,
    ) -> tuple[str, dict]:
        clauses = ["c.user_id = :user_id"]
        params: dict = {"user_id": user_id}

        if not include_subagents:
            if dialect == "sqlite":
                clauses.append("(json_extract(c.meta, '$.subagent_of') IS NULL)")
            elif dialect == "postgresql":
                clauses.append("(c.meta->>'subagent_of' IS NULL)")

        if archived is True:
            clauses.append("c.archived = 1")
        elif archived is False:
            clauses.append("c.archived = 0")

        if pinned is True:
            clauses.append("c.pinned = 1")
        elif pinned is False:
            clauses.append("(c.pinned = 0 OR c.pinned IS NULL)")

        if shared is True:
            clauses.append("c.share_id IS NOT NULL")
        elif shared is False:
            clauses.append("c.share_id IS NULL")

        if folder_ids:
            phs = ",".join(f":fid_{i}" for i in range(len(folder_ids)))
            clauses.append(f"c.folder_id IN ({phs})")
            for i, fid in enumerate(folder_ids):
                params[f"fid_{i}"] = fid

        if tag_ids:
            for i, tid in enumerate(tag_ids):
                if dialect == "sqlite":
                    clauses.append(
                        f"EXISTS (SELECT 1 FROM json_each(c.meta, '$.tags') WHERE value = :tid_{i})"
                    )
                elif dialect == "postgresql":
                    clauses.append(
                        f"EXISTS (SELECT 1 FROM json_array_elements_text(c.meta->'tags') AS t WHERE t = :tid_{i})"
                    )
                params[f"tid_{i}"] = tid

        if updated_after:
            clauses.append("c.updated_at >= :updated_after")
            params["updated_after"] = updated_after
        if updated_before:
            clauses.append("c.updated_at <= :updated_before")
            params["updated_before"] = updated_before

        return (" AND ".join(clauses), params)

    def _search_chats_sqlite_fts(
        self,
        db,
        *,
        user_id: str,
        raw_text: str,
        folder_ids: Optional[list[str]],
        tag_ids: Optional[list[str]],
        pinned: Optional[bool],
        archived: Optional[bool],
        shared: Optional[bool],
        updated_after: Optional[int],
        updated_before: Optional[int],
        sort: str,
        skip: int,
        limit: int,
        include_subagents: bool,
    ) -> "ChatSearchResponse":
        filter_sql, filter_params = self._build_chat_filter_sql(
            user_id=user_id,
            folder_ids=folder_ids,
            tag_ids=tag_ids,
            pinned=pinned,
            archived=archived,
            shared=shared,
            updated_after=updated_after,
            updated_before=updated_before,
            include_subagents=include_subagents,
            dialect="sqlite",
        )

        if not raw_text:
            return self._sqlite_filtered_list(db, filter_sql, filter_params, skip, limit)

        primary_q, prefix_q, fuzzy_q = _build_fts_queries(raw_text)
        if not primary_q:
            return self._sqlite_filtered_list(db, filter_sql, filter_params, skip, limit)

        now = int(time.time())
        used_fuzzy = False

        # Tier 1
        hits = self._sqlite_run_tier(
            db, fts_q=primary_q, filter_sql=filter_sql,
            filter_params=filter_params, now=now, msg_boost=1.2,
        )

        # Tier 2 (gated)
        if len(hits) < 5 and prefix_q and prefix_q != primary_q:
            t2 = self._sqlite_run_tier(
                db, fts_q=prefix_q, filter_sql=filter_sql,
                filter_params=filter_params, now=now, msg_boost=1.2,
                global_scale=0.7,
            )
            seen = {h["id"] for h in hits}
            hits.extend(h for h in t2 if h["id"] not in seen)

        # Tier 3 (gated)
        if len(hits) < 5 and fuzzy_q:
            t3 = self._sqlite_run_fuzzy(
                db, fuzzy_q=fuzzy_q, filter_sql=filter_sql,
                filter_params=filter_params, now=now,
            )
            seen = {h["id"] for h in hits}
            new_hits = [h for h in t3 if h["id"] not in seen]
            if new_hits and not hits:
                used_fuzzy = True
            hits.extend(new_hits)

        if sort == "recent":
            hits.sort(key=lambda h: h["updated_at"], reverse=True)
        else:
            hits.sort(key=lambda h: (h["final_score"], h["updated_at"]), reverse=True)
        total = len(hits)
        page = hits[skip : skip + limit]

        enrichment = self._sqlite_enrich_snippets(db, [h["id"] for h in page], primary_q)
        facets = self._sqlite_facets(db, [h["id"] for h in hits])

        out_hits: list[ChatSearchHit] = []
        for h in page:
            enrich = enrichment.get(h["id"], {})
            out_hits.append(
                ChatSearchHit(
                    id=h["id"],
                    title=h["title"] or "",
                    updated_at=h["updated_at"],
                    created_at=h["created_at"],
                    archived=bool(h["archived"]),
                    pinned=bool(h["pinned"]),
                    folder_id=h["folder_id"],
                    snippet=enrich.get("snippet"),
                    match_count=enrich.get("match_count", 0),
                    matched_message_id=enrich.get("matched_message_id"),
                    matched_role=enrich.get("matched_role"),
                    score=h["final_score"],
                )
            )

        return ChatSearchResponse(
            total=total, hits=out_hits, facets=facets,
            used_fuzzy=used_fuzzy,
            did_you_mean=raw_text if used_fuzzy else None,
        )

    def _sqlite_filtered_list(
        self, db, filter_sql: str, filter_params: dict, skip: int, limit: int
    ) -> "ChatSearchResponse":
        total = db.execute(
            text(f"SELECT COUNT(*) FROM chat c WHERE {filter_sql}"),
            filter_params,
        ).scalar() or 0
        rows = db.execute(
            text(
                f"SELECT c.id, c.title, c.updated_at, c.created_at, c.archived, c.pinned, c.folder_id "
                f"FROM chat c WHERE {filter_sql} "
                f"ORDER BY c.updated_at DESC LIMIT :limit OFFSET :skip"
            ),
            {**filter_params, "limit": limit, "skip": skip},
        ).fetchall()
        hits = [
            ChatSearchHit(
                id=r[0], title=r[1] or "", updated_at=r[2] or 0, created_at=r[3] or 0,
                archived=bool(r[4]), pinned=bool(r[5]), folder_id=r[6],
            )
            for r in rows
        ]
        facets = self._sqlite_facets(db, [h.id for h in hits])
        return ChatSearchResponse(total=int(total), hits=hits, facets=facets)

    def _sqlite_run_tier(
        self,
        db,
        *,
        fts_q: str,
        filter_sql: str,
        filter_params: dict,
        now: int,
        msg_boost: float,
        global_scale: float = 1.0,
    ) -> list[dict]:
        # SQLite FTS5 quirk: bm25() is an auxiliary function that can only be
        # used in a SELECT that directly evaluates `... MATCH ...`. Aggregating
        # bm25 output inside a CTE (`MAX(-bm25(...))`) or chaining CTEs that
        # consume bm25 results breaks the planner's "FTS context" tracking and
        # raises "unable to use function bm25 in the requested context". So we
        # emit raw per-message rows in SQL and aggregate per-chat in Python.
        params = {**filter_params, "q": fts_q}
        sql = f"""
            WITH chat_scored AS (
                SELECT chat_fts.id AS id,
                       -bm25(chat_fts, 3.0, 1.0) AS s
                FROM chat_fts WHERE chat_fts MATCH :q
            ),
            msg_rows AS (
                SELECT message_fts.chat_id AS id,
                       message_fts.message_id AS mid,
                       -bm25(message_fts) AS s
                FROM message_fts WHERE message_fts MATCH :q
            )
            SELECT c.id, c.title, c.updated_at, c.created_at,
                   c.archived, c.pinned, c.folder_id,
                   COALESCE(cs.s, 0.0) AS chat_s,
                   msg_rows.s AS msg_s
            FROM chat c
            LEFT JOIN chat_scored cs ON cs.id = c.id
            LEFT JOIN msg_rows ON msg_rows.id = c.id
            WHERE {filter_sql}
              AND (cs.s IS NOT NULL OR msg_rows.s IS NOT NULL)
            LIMIT 1500
        """
        rows = db.execute(text(sql), params).fetchall()

        # Aggregate per chat: take chat-level score as-is, take max msg score,
        # and count distinct messages that matched.
        agg: dict[str, dict] = {}
        for r in rows:
            cid = r[0]
            slot = agg.get(cid)
            if slot is None:
                title = (r[1] or "").strip()
                title_l = title.lower()
                if title_l in _GENERIC_TITLES:
                    title_penalty = 1.5
                elif len(title) <= 3:
                    title_penalty = 1.3
                else:
                    title_penalty = 1.0
                slot = {
                    "id": cid,
                    "title": title,
                    "updated_at": r[2] or 0,
                    "created_at": r[3] or 0,
                    "archived": r[4],
                    "pinned": r[5],
                    "folder_id": r[6],
                    "chat_score": float(r[7] or 0.0),
                    "msg_score": 0.0,
                    "match_count": 0,
                    "title_penalty": title_penalty,
                }
                agg[cid] = slot
            if r[8] is not None:
                msg_s = float(r[8])
                if msg_s > slot["msg_score"]:
                    slot["msg_score"] = msg_s
                slot["match_count"] += 1

        out: list[dict] = []
        for slot in agg.values():
            raw = max(slot["chat_score"], slot["msg_score"] * msg_boost)
            age_days = max(0, (now - (slot["updated_at"] or now)) / 86400.0)
            decay = 2.71828 ** (-age_days / 90.0)
            final = (raw / slot["title_penalty"]) * decay * global_scale
            out.append({
                "id": slot["id"],
                "title": slot["title"],
                "updated_at": slot["updated_at"],
                "created_at": slot["created_at"],
                "archived": slot["archived"],
                "pinned": slot["pinned"],
                "folder_id": slot["folder_id"],
                "raw_score": raw,
                "final_score": final,
                "match_count": slot["match_count"],
            })
        return out

    def _sqlite_run_fuzzy(
        self, db, *, fuzzy_q: str, filter_sql: str, filter_params: dict, now: int,
    ) -> list[dict]:
        params = {**filter_params, "q": fuzzy_q}
        sql = f"""
            SELECT c.id, c.title, c.updated_at, c.created_at,
                   c.archived, c.pinned, c.folder_id,
                   -bm25(chat_fts_tri) AS s
            FROM chat_fts_tri JOIN chat c ON c.id = chat_fts_tri.id
            WHERE chat_fts_tri MATCH :q AND {filter_sql}
            LIMIT 100
        """
        rows = db.execute(text(sql), params).fetchall()
        out: list[dict] = []
        for r in rows:
            raw = float(r[7] or 0.0)
            age_days = max(0, (now - (r[2] or now)) / 86400.0)
            decay = 2.71828 ** (-age_days / 90.0)
            final = raw * decay * 0.4
            out.append({
                "id": r[0], "title": r[1] or "",
                "updated_at": r[2] or 0, "created_at": r[3] or 0,
                "archived": r[4], "pinned": r[5], "folder_id": r[6],
                "raw_score": raw, "final_score": final, "match_count": 0,
            })
        return out

    def _sqlite_enrich_snippets(
        self, db, chat_ids: list[str], fts_q: str
    ) -> dict[str, dict]:
        if not chat_ids or not fts_q:
            return {}
        placeholders = ",".join(f":cid_{i}" for i in range(len(chat_ids)))
        params: dict = {"q": fts_q}
        for i, cid in enumerate(chat_ids):
            params[f"cid_{i}"] = cid

        sql = f"""
            WITH ranked AS (
                SELECT message_fts.chat_id AS chat_id,
                       message_fts.message_id AS message_id,
                       message_fts.role AS role,
                       snippet(message_fts, 3, '<mark>', '</mark>', '…', 14) AS snip,
                       -bm25(message_fts) AS s
                FROM message_fts
                WHERE message_fts MATCH :q
                  AND message_fts.chat_id IN ({placeholders})
            ),
            counts AS (
                SELECT chat_id, COUNT(*) AS cnt FROM ranked GROUP BY chat_id
            ),
            tops AS (
                SELECT chat_id, message_id, role, snip, s,
                       ROW_NUMBER() OVER (PARTITION BY chat_id ORDER BY s DESC) AS rn
                FROM ranked
            )
            SELECT t.chat_id, t.message_id, t.role, t.snip, COALESCE(c.cnt, 0)
            FROM tops t
            LEFT JOIN counts c ON c.chat_id = t.chat_id
            WHERE t.rn = 1
        """
        rows = db.execute(text(sql), params).fetchall()
        out: dict[str, dict] = {}
        for r in rows:
            out[r[0]] = {
                "matched_message_id": r[1],
                "matched_role": r[2],
                "snippet": _sanitize_snippet(r[3]),
                "match_count": int(r[4] or 0),
            }

        missing = [cid for cid in chat_ids if cid not in out]
        if missing:
            placeholders2 = ",".join(f":cid_{i}" for i in range(len(missing)))
            params2: dict = {"q": fts_q}
            for i, cid in enumerate(missing):
                params2[f"cid_{i}"] = cid
            sql2 = f"""
                SELECT id, snippet(chat_fts, 1, '<mark>', '</mark>', '…', 16) AS snip
                FROM chat_fts
                WHERE chat_fts MATCH :q AND id IN ({placeholders2})
            """
            try:
                rows2 = db.execute(text(sql2), params2).fetchall()
                for r in rows2:
                    out[r[0]] = {
                        "matched_message_id": None,
                        "matched_role": None,
                        "snippet": _sanitize_snippet(r[1]),
                        "match_count": 0,
                    }
            except Exception:
                pass
        return out

    def _sqlite_facets(self, db, chat_ids: list[str]) -> "ChatSearchFacets":
        if not chat_ids:
            return ChatSearchFacets()
        placeholders = ",".join(f":cid_{i}" for i in range(len(chat_ids)))
        params: dict = {}
        for i, cid in enumerate(chat_ids):
            params[f"cid_{i}"] = cid

        try:
            folder_rows = db.execute(
                text(
                    f"SELECT c.folder_id, f.name, COUNT(*) "
                    f"FROM chat c LEFT JOIN folder f ON f.id = c.folder_id "
                    f"WHERE c.id IN ({placeholders}) AND c.folder_id IS NOT NULL "
                    f"GROUP BY c.folder_id, f.name "
                    f"ORDER BY COUNT(*) DESC LIMIT 20"
                ),
                params,
            ).fetchall()
            folders = [
                FacetBucket(id=r[0], name=(r[1] or r[0]), count=int(r[2]))
                for r in folder_rows
            ]
        except Exception:
            folders = []

        try:
            tag_rows = db.execute(
                text(
                    f"SELECT tag.value, COUNT(*) "
                    f"FROM chat c, json_each(c.meta, '$.tags') AS tag "
                    f"WHERE c.id IN ({placeholders}) "
                    f"GROUP BY tag.value "
                    f"ORDER BY COUNT(*) DESC LIMIT 20"
                ),
                params,
            ).fetchall()
            tags = [
                FacetBucket(id=str(r[0]), name=str(r[0]), count=int(r[1]))
                for r in tag_rows if r[0]
            ]
        except Exception:
            tags = []

        try:
            model_rows = db.execute(
                text(
                    f"SELECT json_extract(c.chat, '$.models[0]') AS m, COUNT(*) "
                    f"FROM chat c WHERE c.id IN ({placeholders}) AND m IS NOT NULL "
                    f"GROUP BY m ORDER BY COUNT(*) DESC LIMIT 20"
                ),
                params,
            ).fetchall()
            models = [
                FacetBucket(id=str(r[0]), name=str(r[0]), count=int(r[1]))
                for r in model_rows if r[0]
            ]
        except Exception:
            models = []

        return ChatSearchFacets(folders=folders, tags=tags, models=models)

    def _search_chats_like_fallback(
        self,
        db,
        *,
        user_id: str,
        raw_text: str,
        folder_ids: Optional[list[str]],
        tag_ids: Optional[list[str]],
        pinned: Optional[bool],
        archived: Optional[bool],
        shared: Optional[bool],
        updated_after: Optional[int],
        updated_before: Optional[int],
        sort: str,
        skip: int,
        limit: int,
        include_subagents: bool,
    ) -> "ChatSearchResponse":
        """Postgres/MySQL fallback: previous LIKE-based behavior. No snippets,
        no facets, no fuzzy. Will be replaced in a follow-up migration."""
        query = db.query(Chat).filter(Chat.user_id == user_id)
        query = _apply_subagent_filter(query, db, include_subagents)

        if archived is True:
            query = query.filter(Chat.archived == True)
        elif archived is False:
            query = query.filter(Chat.archived == False)
        if pinned is True:
            query = query.filter(Chat.pinned == True)
        elif pinned is False:
            query = query.filter(or_(Chat.pinned == False, Chat.pinned == None))
        if shared is True:
            query = query.filter(Chat.share_id.isnot(None))
        elif shared is False:
            query = query.filter(Chat.share_id.is_(None))
        if folder_ids:
            query = query.filter(Chat.folder_id.in_(folder_ids))
        if updated_after:
            query = query.filter(Chat.updated_at >= updated_after)
        if updated_before:
            query = query.filter(Chat.updated_at <= updated_before)

        words = [w for w in raw_text.lower().split(" ") if w]
        _has_search_col = _search_text_column_exists(db)
        for word in words:
            if _has_search_col:
                query = query.filter(
                    or_(
                        text("chat.search_text LIKE :w").params(w=f"%{word}%"),
                        and_(
                            text("chat.search_text IS NULL"),
                            Chat.title.ilike(f"%{word}%"),
                        ),
                    )
                )
            else:
                query = query.filter(Chat.title.ilike(f"%{word}%"))

        if db.bind.dialect.name == "postgresql" and tag_ids:
            for i, tag_id in enumerate(tag_ids):
                query = query.filter(
                    text(
                        f"EXISTS (SELECT 1 FROM json_array_elements_text(chat.meta->'tags') AS t WHERE t = :tagp_{i})"
                    ).params(**{f"tagp_{i}": tag_id})
                )

        query = query.order_by(Chat.updated_at.desc())
        total = query.count()
        rows = query.offset(skip).limit(limit).all()
        hits = [
            ChatSearchHit(
                id=r.id, title=r.title or "",
                updated_at=r.updated_at or 0, created_at=r.created_at or 0,
                archived=bool(r.archived), pinned=bool(r.pinned),
                folder_id=r.folder_id,
            )
            for r in rows
        ]
        return ChatSearchResponse(total=int(total), hits=hits)

    def get_chats_by_folder_id_and_user_id(
        self, folder_id: str, user_id: str, skip: int = 0, limit: int = 60
    ) -> list[ChatModel]:
        with get_db() as db:
            query = db.query(Chat).filter_by(folder_id=folder_id, user_id=user_id)
            query = query.filter(or_(Chat.pinned == False, Chat.pinned == None))
            query = query.filter_by(archived=False)

            query = query.order_by(Chat.updated_at.desc())

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            all_chats = query.all()
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def get_chats_by_folder_ids_and_user_id(
        self, folder_ids: list[str], user_id: str
    ) -> list[ChatModel]:
        with get_db() as db:
            query = db.query(Chat).filter(
                Chat.folder_id.in_(folder_ids), Chat.user_id == user_id
            )
            query = query.filter(or_(Chat.pinned == False, Chat.pinned == None))
            query = query.filter_by(archived=False)

            query = query.order_by(Chat.updated_at.desc())

            all_chats = query.all()
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def update_chat_folder_id_by_id_and_user_id(
        self, id: str, user_id: str, folder_id: str
    ) -> Optional[ChatModel]:
        try:
            with get_db() as db:
                chat = db.get(Chat, id)
                chat.folder_id = folder_id
                chat.updated_at = int(time.time())
                chat.pinned = False
                db.commit()
                db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    def get_chat_tags_by_id_and_user_id(self, id: str, user_id: str) -> list[TagModel]:
        with get_db() as db:
            chat = db.get(Chat, id)
            tags = chat.meta.get("tags", [])
            return [Tags.get_tag_by_name_and_user_id(tag, user_id) for tag in tags]

    def get_chat_list_by_user_id_and_tag_name(
        self, user_id: str, tag_name: str, skip: int = 0, limit: int = 50
    ) -> list[ChatModel]:
        with get_db() as db:
            query = db.query(Chat).filter_by(user_id=user_id)
            tag_id = tag_name.replace(" ", "_").lower()

            log.info(f"DB dialect name: {db.bind.dialect.name}")
            if db.bind.dialect.name == "sqlite":
                # SQLite JSON1 querying for tags within the meta JSON field
                query = query.filter(
                    text(
                        f"EXISTS (SELECT 1 FROM json_each(Chat.meta, '$.tags') WHERE json_each.value = :tag_id)"
                    )
                ).params(tag_id=tag_id)
            elif db.bind.dialect.name == "postgresql":
                # PostgreSQL JSON query for tags within the meta JSON field (for `json` type)
                query = query.filter(
                    text(
                        "EXISTS (SELECT 1 FROM json_array_elements_text(Chat.meta->'tags') elem WHERE elem = :tag_id)"
                    )
                ).params(tag_id=tag_id)
            else:
                raise NotImplementedError(
                    f"Unsupported dialect: {db.bind.dialect.name}"
                )

            all_chats = query.all()
            log.debug(f"all_chats: {all_chats}")
            return [ChatModel.model_validate(chat) for chat in all_chats]

    def add_chat_tag_by_id_and_user_id_and_tag_name(
        self, id: str, user_id: str, tag_name: str
    ) -> Optional[ChatModel]:
        tag = Tags.get_tag_by_name_and_user_id(tag_name, user_id)
        if tag is None:
            tag = Tags.insert_new_tag(tag_name, user_id)
        try:
            with get_db() as db:
                chat = db.get(Chat, id)

                tag_id = tag.id
                if tag_id not in chat.meta.get("tags", []):
                    chat.meta = {
                        **chat.meta,
                        "tags": list(set(chat.meta.get("tags", []) + [tag_id])),
                    }

                db.commit()
                db.refresh(chat)
                return ChatModel.model_validate(chat)
        except Exception:
            return None

    def count_chats_by_tag_name_and_user_id(self, tag_name: str, user_id: str) -> int:
        with get_db() as db:  # Assuming `get_db()` returns a session object
            query = db.query(Chat).filter_by(user_id=user_id, archived=False)

            # Normalize the tag_name for consistency
            tag_id = tag_name.replace(" ", "_").lower()

            if db.bind.dialect.name == "sqlite":
                # SQLite JSON1 support for querying the tags inside the `meta` JSON field
                query = query.filter(
                    text(
                        f"EXISTS (SELECT 1 FROM json_each(Chat.meta, '$.tags') WHERE json_each.value = :tag_id)"
                    )
                ).params(tag_id=tag_id)

            elif db.bind.dialect.name == "postgresql":
                # PostgreSQL JSONB support for querying the tags inside the `meta` JSON field
                query = query.filter(
                    text(
                        "EXISTS (SELECT 1 FROM json_array_elements_text(Chat.meta->'tags') elem WHERE elem = :tag_id)"
                    )
                ).params(tag_id=tag_id)

            else:
                raise NotImplementedError(
                    f"Unsupported dialect: {db.bind.dialect.name}"
                )

            # Get the count of matching records
            count = query.count()

            # Debugging output for inspection
            log.info(f"Count of chats for tag '{tag_name}': {count}")

            return count

    def count_chats_by_folder_id_and_user_id(self, folder_id: str, user_id: str) -> int:
        with get_db() as db:
            query = db.query(Chat).filter_by(user_id=user_id)

            query = query.filter_by(folder_id=folder_id)
            count = query.count()

            log.info(f"Count of chats for folder '{folder_id}': {count}")
            return count

    def count_chats_by_user_id(self, user_id: str) -> int:
        with get_db() as db:
            count = db.query(Chat).filter_by(user_id=user_id, archived=False).count()
            return count

    def delete_tag_by_id_and_user_id_and_tag_name(
        self, id: str, user_id: str, tag_name: str
    ) -> bool:
        try:
            with get_db() as db:
                chat = db.get(Chat, id)
                tags = chat.meta.get("tags", [])
                tag_id = tag_name.replace(" ", "_").lower()

                tags = [tag for tag in tags if tag != tag_id]
                chat.meta = {
                    **chat.meta,
                    "tags": list(set(tags)),
                }
                db.commit()
                return True
        except Exception:
            return False

    def delete_all_tags_by_id_and_user_id(self, id: str, user_id: str) -> bool:
        try:
            with get_db() as db:
                chat = db.get(Chat, id)
                chat.meta = {
                    **chat.meta,
                    "tags": [],
                }
                db.commit()

                return True
        except Exception:
            return False

    def delete_chat_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Chat).filter_by(id=id).delete()
                db.commit()

                return True and self.delete_shared_chat_by_chat_id(id)
        except Exception:
            return False

    def delete_chat_by_id_and_user_id(self, id: str, user_id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Chat).filter_by(id=id, user_id=user_id).delete()
                db.commit()

                return True and self.delete_shared_chat_by_chat_id(id)
        except Exception:
            return False

    def delete_chats_by_user_id(self, user_id: str) -> bool:
        try:
            with get_db() as db:
                self.delete_shared_chats_by_user_id(user_id)

                db.query(Chat).filter_by(user_id=user_id).delete()
                db.commit()

                return True
        except Exception:
            return False

    def delete_chats_by_user_id_and_folder_id(
        self, user_id: str, folder_id: str
    ) -> bool:
        try:
            with get_db() as db:
                db.query(Chat).filter_by(user_id=user_id, folder_id=folder_id).delete()
                db.commit()

                return True
        except Exception:
            return False

    def delete_shared_chats_by_user_id(self, user_id: str) -> bool:
        try:
            with get_db() as db:
                chats_by_user = db.query(Chat).filter_by(user_id=user_id).all()
                shared_chat_ids = [f"shared-{chat.id}" for chat in chats_by_user]

                db.query(Chat).filter(Chat.user_id.in_(shared_chat_ids)).delete()
                db.commit()

                return True
        except Exception:
            return False


Chats = ChatTable()
