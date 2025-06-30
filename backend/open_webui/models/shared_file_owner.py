import logging

from sqlalchemy import exists

from open_webui.env import SRC_LOG_LEVELS
from open_webui.internal.db import get_db
from open_webui.models.users import shared_file_owner

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

class SharedFileOwner:

    @staticmethod
    def has_access(access_type: str, file_id: str, user_id: str) -> bool:
        """Checks if a user-file link exists in the database."""
        if access_type != "read":
            return False

        with get_db() as db:
            try:
                stmt = exists().where(
                    shared_file_owner.c.user_id == user_id,
                    shared_file_owner.c.file_id == file_id
                ).select()

                result = db.execute(stmt).scalar()
                return result
            except Exception as e:
                log.error(f"An error occurred: {e}")
                return False

    @staticmethod
    def add_shared_file_owner(user_id: str, chat: dict) -> None:
        file_ids = []
        for file in chat.get("files", []):
            file_id = file.get("id")
            if not file_id:
                continue
            file_ids.append(file_id)

        if not file_ids:
            return

        with get_db() as db:
            from sqlalchemy import text
            files_to_add = db.execute(text("SELECT id FROM file WHERE id IN :file_ids"), {"file_ids": tuple(file_ids)}).fetchall()
            existing_file_ids = db.execute(text("SELECT file_id FROM shared_file_owner WHERE user_id = :user_id"), {"user_id": user_id}).fetchall()
            existing_file_ids = {f[0] for f in existing_file_ids}
            for file_id in files_to_add:
                file_id = file_id[0]
                if file_id not in existing_file_ids:
                    db.execute(shared_file_owner.insert().values(user_id=user_id, file_id=file_id))
            db.commit()