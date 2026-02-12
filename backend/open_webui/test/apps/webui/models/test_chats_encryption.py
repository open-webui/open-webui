import copy
import importlib
from contextlib import contextmanager

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _reload_modules(monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("WEBUI_CHAT_ENCRYPTION_KEY", key)

    import open_webui.env as env
    importlib.reload(env)

    import open_webui.utils.db.chat_encryption as chat_encryption
    importlib.reload(chat_encryption)

    if chat_encryption.WEBUI_CHAT_ENCRYPTION_CIPHER is None:
        chat_encryption.WEBUI_CHAT_ENCRYPTION_KEY = key
        chat_encryption.WEBUI_CHAT_ENCRYPTION_CIPHER = Fernet(key.encode("ascii"))

    def _encrypt_content_guard(chat_data: dict) -> dict:
        assert chat_encryption.WEBUI_CHAT_ENCRYPTION_CIPHER is not None
        return chat_encryption.encrypt_content(chat_data)

    def _decrypt_content_guard(chat_data: dict) -> dict:
        assert chat_encryption.WEBUI_CHAT_ENCRYPTION_CIPHER is not None
        return chat_encryption.decrypt_content(chat_data)

    import open_webui.models.chats as chats_model
    chats_model.encrypt_content = _encrypt_content_guard
    chats_model.decrypt_content = _decrypt_content_guard

    return chats_model, chat_encryption


@contextmanager
def _db_context(session):
    yield session


def _setup_db():
    from open_webui.internal.db import Base
    from open_webui.models.files import File

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal, SessionLocal()


@pytest.mark.filterwarnings(
    r"ignore:The ``declarative_base\(\)`` function is now available as sqlalchemy\.orm\.declarative_base\(\)\.:sqlalchemy.exc.MovedIn20Warning"
)
def test_chat_model_encrypt_decrypt_flow(monkeypatch):
    chats_model, chat_encryption = _reload_modules(monkeypatch)
    SessionLocal, session = _setup_db()

    monkeypatch.setattr(
        chats_model, "get_db_context", lambda db=None: _db_context(session)
    )

    Chats = chats_model.ChatTable()

    chat_body = {
        "title": "Test",
        "history": {"messages": {"m1": {"content": "hello"}}, "currentId": "m1"},
        "messages": [{"content": "world"}],
    }

    encrypted_preview = chats_model.encrypt_content(copy.deepcopy(chat_body))
    preview_value = encrypted_preview["history"]["messages"]["m1"]["content"]
    assert preview_value.startswith("gAAAAAB"), f"preview not encrypted: {preview_value}"

    created = Chats.insert_new_chat(
        "u1", chats_model.ChatForm(chat=chat_body, folder_id=None)
    )
    assert created.chat["history"]["messages"]["m1"]["content"] == "hello"

    fresh_session = SessionLocal()
    stored = fresh_session.query(chats_model.Chat).filter_by(id=created.id).first()
    stored_value = stored.chat["history"]["messages"]["m1"]["content"]
    assert stored_value.startswith("gAAAAAB"), f"stored not encrypted: {stored_value}"

    updated = Chats.update_chat_by_id(
        created.id, {**created.chat, "title": "Updated"}, db=session
    )
    assert updated.chat["title"] == "Updated"

    upserted = Chats.upsert_message_to_chat_by_id_and_message_id(
        created.id, "m2", {"content": "new message"}
    )
    assert upserted.chat["history"]["messages"]["m2"]["content"] == "new message"

    fresh_session = SessionLocal()
    stored = fresh_session.query(chats_model.Chat).filter_by(id=created.id).first()
    stored_value = stored.chat["history"]["messages"]["m2"]["content"]
    assert stored_value.startswith("gAAAAAB"), f"stored m2 not encrypted: {stored_value}"
