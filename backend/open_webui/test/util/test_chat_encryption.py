import copy
import importlib

from cryptography.fernet import Fernet


def _reload_chat_encryption(monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("WEBUI_CHAT_ENCRYPTION_KEY", key)

    import open_webui.env as env
    importlib.reload(env)

    import open_webui.utils.db.chat_encryption as chat_encryption
    importlib.reload(chat_encryption)

    return chat_encryption


def test_encrypt_decrypt_roundtrip(monkeypatch):
    chat_encryption = _reload_chat_encryption(monkeypatch)

    data = {"foo": "bar", "num": 1}
    encrypted = chat_encryption.encrypt(data)

    assert isinstance(encrypted, str)
    assert encrypted.startswith("gAAAAAB")

    decrypted = chat_encryption.decrypt(encrypted, encrypted)
    assert decrypted == data


def test_encrypt_decrypt_content(monkeypatch):
    chat_encryption = _reload_chat_encryption(monkeypatch)

    chat_data = {
        "title": "Test",
        "history": {
            "messages": {
                "m1": {"content": "hello", "role": "user"},
                "m2": {"content": "world", "role": "assistant"},
            },
            "currentId": "m2",
        },
        "messages": [{"content": "list message"}],
    }

    encrypted = chat_encryption.encrypt_content(copy.deepcopy(chat_data))

    assert encrypted["history"]["messages"]["m1"]["content"].startswith("gAAAAAB")
    assert encrypted["history"]["messages"]["m2"]["content"].startswith("gAAAAAB")
    assert encrypted["messages"][0]["content"].startswith("gAAAAAB")

    decrypted = chat_encryption.decrypt_content(copy.deepcopy(encrypted))

    assert decrypted["history"]["messages"]["m1"]["content"] == "hello"
    assert decrypted["history"]["messages"]["m2"]["content"] == "world"
    assert decrypted["messages"][0]["content"] == "list message"
