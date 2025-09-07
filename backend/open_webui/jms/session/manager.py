from typing import Dict


class SessionManager:
    def __init__(self):
        self.store: Dict[str, dict] = {}

    def register_jms_session(self, jms_session, chat: dict):
        key = str(jms_session.session.id)
        self.store[key] = {"jms_session": jms_session, "chat": chat}

    def unregister_jms_session(self, jms_session):
        key = str(jms_session.session.id)
        self.store.pop(key, None)

    def get_store(self):
        return self.store

    def get_jms_session(self, s_id: str):
        return self.store.get(str(s_id), {}).get("jms_session")

    def get_chat(self, s_id: str) -> dict:
        return self.store.get(str(s_id), {}).get("chat", {})




session_manager = SessionManager()