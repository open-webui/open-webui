import importlib
from contextlib import contextmanager

from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _reload_encryption_modules(monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("WEBUI_CHAT_ENCRYPTION_KEY", key)

    import open_webui.env as env
    importlib.reload(env)

    import open_webui.utils.db.chat_encryption as chat_encryption
    importlib.reload(chat_encryption)

    import open_webui.utils.db.encrypt_old_chats as encrypt_old_chats
    importlib.reload(encrypt_old_chats)

    return chat_encryption, encrypt_old_chats


@contextmanager
def _db_context(session):
    yield session


def test_encrypt_old_chats_for_user(monkeypatch):
    _, encrypt_old_chats = _reload_encryption_modules(monkeypatch)

    from open_webui.internal.db import Base
    from open_webui.models.chats import Chat
    from open_webui.models.files import File

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    chat_json = {
        "title": "Plain",
        "history": {"messages": {"m1": {"content": "hello"}}},
        "messages": [{"content": "world"}],
    }

    session.add(
        Chat(
            id="c1",
            user_id="u1",
            title="Plain",
            chat=chat_json,
            created_at=0,
            updated_at=0,
        )
    )
    session.commit()

    monkeypatch.setattr(
        encrypt_old_chats, "get_db_context", lambda db=None: _db_context(session)
    )

    count = encrypt_old_chats.encrypt_old_chats_for_user("u1")
    assert count == 1

    stored = session.query(Chat).filter_by(id="c1").first()
    assert stored.chat["history"]["messages"]["m1"]["content"].startswith("gAAAAAB")
    assert stored.chat["messages"][0]["content"].startswith("gAAAAAB")
