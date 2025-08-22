import logging
import time
import uuid
from typing import Optional

from open_webui.internal.db import get_db
from open_webui.models.chats import Chat, ChatForm, ChatImportForm, ChatModel, ChatTable
from open_webui.utils.user_encryption import (
    EncryptionError,
    UserEncryptionConfig,
    decrypt_chat_data,
    decrypt_title_data,
    encrypt_chat_data,
    encrypt_title_data,
)

log = logging.getLogger(__name__)


class ChatTableEncryptionProxy(ChatTable):
    """
    Encryption proxy for ChatTable that transparently encrypts/decrypts chat data.

    This proxy wraps the existing ChatTable class without modifying it,
    providing automatic encryption/decryption of chat.chat field.
    """

    def __init__(self):
        super().__init__()
        self._encryption_enabled = UserEncryptionConfig.is_encryption_enabled()

        # Log configuration status
        UserEncryptionConfig.log_config_status()

        log_level = "ENABLED" if self._encryption_enabled else "DISABLED"
        env_hint = (
            ""
            if self._encryption_enabled
            else " (set ENABLE_CHAT_ENCRYPTION=true to enable)"
        )
        log.info(
            f"ChatTableEncryptionProxy initialized with per-user encryption {log_level}{env_hint}"
        )

    def _create_chat_model_from_db_record(self, db_record) -> ChatModel:
        """Create ChatModel from database record, handling encrypted data."""
        chat_data = db_record.chat
        title_data = db_record.title

        # Handle encrypted chat data
        if isinstance(chat_data, str):
            try:
                chat_data = decrypt_chat_data(chat_data, db_record.user_id)
            except Exception as e:
                log.error(f"Failed to decrypt chat data for {db_record.id}: {e}")
                # Return None to indicate failure - let caller handle it
                return None

        # Handle encrypted title data (with fallback)
        if isinstance(title_data, str):
            try:
                title_data = decrypt_title_data(title_data, db_record.user_id)
            except Exception as e:
                log.error(f"Failed to decrypt title data for {db_record.id}: {e}")
                # Fallback to original title if decryption fails
                title_data = db_record.title

        return ChatModel(
            id=db_record.id,
            user_id=db_record.user_id,
            title=title_data,
            chat=chat_data,
            created_at=db_record.created_at,
            updated_at=db_record.updated_at,
            share_id=db_record.share_id,
            archived=db_record.archived or False,
            pinned=db_record.pinned or False,
            meta=db_record.meta or {},
            folder_id=db_record.folder_id,
        )

    def _store_encrypted_chat(self, chat_record, chat_data: dict, user_id: str) -> None:
        """Store chat data in database record, encrypting if enabled."""
        if self._encryption_enabled:
            try:
                chat_record.chat = encrypt_chat_data(chat_data, user_id)
            except EncryptionError as e:
                log.error(
                    f"Encryption failed, falling back to unencrypted storage: {e}"
                )
                chat_record.chat = chat_data
        else:
            chat_record.chat = chat_data

    def _store_encrypted_title(self, chat_record, title: str, user_id: str) -> None:
        """Store title data in database record, encrypting if enabled."""
        if self._encryption_enabled:
            try:
                chat_record.title = encrypt_title_data(title, user_id)
            except EncryptionError as e:
                log.error(
                    f"Title encryption failed, falling back to unencrypted storage: {e}"
                )
                chat_record.title = title
        else:
            chat_record.title = title

    # Override INSERT/UPDATE methods

    def insert_new_chat(self, user_id: str, form_data: ChatForm) -> Optional[ChatModel]:
        """Override to encrypt chat data before inserting."""
        if not self._encryption_enabled:
            return super().insert_new_chat(user_id, form_data)

        try:
            with get_db() as db:
                id = str(uuid.uuid4())
                title = form_data.chat.get("title", "New Chat")

                # Create database record
                chat_record = Chat(
                    id=id,
                    user_id=user_id,
                    folder_id=form_data.folder_id,
                    created_at=int(time.time()),
                    updated_at=int(time.time()),
                )

                # Store encrypted chat and title data
                self._store_encrypted_chat(chat_record, form_data.chat, user_id)
                self._store_encrypted_title(chat_record, title, user_id)

                db.add(chat_record)
                db.commit()
                db.refresh(chat_record)

                # Return ChatModel with decrypted data
                return ChatModel(
                    id=chat_record.id,
                    user_id=chat_record.user_id,
                    title=title,  # Return original title (not encrypted)
                    chat=form_data.chat,
                    created_at=chat_record.created_at,
                    updated_at=chat_record.updated_at,
                    share_id=chat_record.share_id,
                    archived=chat_record.archived or False,
                    pinned=chat_record.pinned or False,
                    meta=chat_record.meta or {},
                    folder_id=chat_record.folder_id,
                )

        except Exception as e:
            log.error(f"Error in encrypted insert_new_chat: {e}")
            # Fallback to parent method
            return super().insert_new_chat(user_id, form_data)

    def import_chat(
        self, user_id: str, form_data: ChatImportForm
    ) -> Optional[ChatModel]:
        """Override to encrypt chat data before importing."""
        if not self._encryption_enabled:
            return super().import_chat(user_id, form_data)

        raise NotImplementedError("Importing chats is not supported")

    def update_chat_by_id(self, id: str, chat: dict) -> Optional[ChatModel]:
        """Override to encrypt chat data before updating."""
        if not self._encryption_enabled:
            return super().update_chat_by_id(id, chat)

        try:
            with get_db() as db:
                chat_item = db.get(Chat, id)
                if not chat_item:
                    return None

                title = chat.get("title", "New Chat")

                # Store encrypted chat and title data
                self._store_encrypted_chat(chat_item, chat, chat_item.user_id)
                self._store_encrypted_title(chat_item, title, chat_item.user_id)

                chat_item.updated_at = int(time.time())
                db.commit()
                db.refresh(chat_item)

                # Return ChatModel with decrypted data
                return ChatModel(
                    id=chat_item.id,
                    user_id=chat_item.user_id,
                    title=title,  # Return original title (not encrypted)
                    chat=chat,
                    created_at=chat_item.created_at,
                    updated_at=chat_item.updated_at,
                    share_id=chat_item.share_id,
                    archived=chat_item.archived or False,
                    pinned=chat_item.pinned or False,
                    meta=chat_item.meta or {},
                    folder_id=chat_item.folder_id,
                )

        except Exception as e:
            log.error(f"Error in encrypted update_chat_by_id: {e}")
            return super().update_chat_by_id(id, chat)

    def upsert_message_to_chat_by_id_and_message_id(
        self, id: str, message_id: str, message: dict
    ) -> Optional[ChatModel]:
        """Override to handle encryption during message upsert."""
        if not self._encryption_enabled:
            return super().upsert_message_to_chat_by_id_and_message_id(
                id, message_id, message
            )

        try:
            # Get current chat and decrypt it first
            current_chat = self.get_chat_by_id(id)
            if not current_chat:
                return None

            # Perform the message upsert on decrypted data
            chat_data = current_chat.chat
            history = chat_data.get("history", {})

            # Sanitize message content for null characters
            if isinstance(message.get("content"), str):
                message["content"] = message["content"].replace("\x00", "")

            if message_id in history.get("messages", {}):
                history["messages"][message_id] = {
                    **history["messages"][message_id],
                    **message,
                }
            else:
                history["messages"][message_id] = message

            history["currentId"] = message_id
            chat_data["history"] = history

            # Update with encrypted data
            return self.update_chat_by_id(id, chat_data)

        except Exception as e:
            log.error(f"Error in encrypted upsert_message: {e}")
            return super().upsert_message_to_chat_by_id_and_message_id(
                id, message_id, message
            )

    # Override RETRIEVAL methods

    def get_chat_by_id(self, id: str) -> Optional[ChatModel]:
        """Override to decrypt chat data after retrieving."""
        try:
            with get_db() as db:
                chat_item = db.get(Chat, id)
                if not chat_item:
                    return None

                return self._create_chat_model_from_db_record(chat_item)

        except Exception as e:
            log.error(f"Error in get_chat_by_id: {e}")
            return super().get_chat_by_id(id)

    def get_chat_by_id_and_user_id(self, id: str, user_id: str) -> Optional[ChatModel]:
        """Override to decrypt chat data after retrieving."""
        try:
            with get_db() as db:
                chat_item = db.query(Chat).filter_by(id=id, user_id=user_id).first()
                if not chat_item:
                    return None

                return self._create_chat_model_from_db_record(chat_item)

        except Exception as e:
            log.error(f"Error in get_chat_by_id_and_user_id: {e}")
            return super().get_chat_by_id_and_user_id(id, user_id)

    def get_chat_by_share_id(self, id: str) -> Optional[ChatModel]:
        """Override to decrypt chat data after retrieving."""
        if not self._encryption_enabled:
            return super().get_chat_by_share_id(id)

        # Use parent method and decrypt result
        result = super().get_chat_by_share_id(id)
        if result and isinstance(result.chat, str):
            try:
                result.chat = decrypt_chat_data(result.chat, result.user_id)
            except Exception as e:
                log.error(f"Failed to decrypt shared chat {id}: {e}")
                return None
        return result

    # For list methods, use parent methods and handle individual decryption
    def _decrypt_chat_models_list(
        self, chat_models: list[ChatModel]
    ) -> list[ChatModel]:
        """Decrypt a list of chat models."""
        decrypted_models = []
        for model in chat_models:
            # Decrypt chat data if needed
            if isinstance(model.chat, str):
                try:
                    model.chat = decrypt_chat_data(model.chat, model.user_id)
                except Exception as e:
                    log.error(f"Failed to decrypt chat {model.id}: {e}")
                    # Skip corrupted chats instead of crashing
                    continue

            # Decrypt title data if needed
            if isinstance(model.title, str):
                try:
                    model.title = decrypt_title_data(model.title, model.user_id)
                except Exception as e:
                    log.error(f"Failed to decrypt title for {model.id}: {e}")
                    # Keep original title if decryption fails
                    pass

            decrypted_models.append(model)
        return decrypted_models

    def get_chat_list_by_user_id(
        self,
        user_id: str,
        include_archived: bool = False,
        filter: Optional[dict] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[ChatModel]:
        """Override to decrypt chat data after retrieving."""
        results = super().get_chat_list_by_user_id(
            user_id, include_archived, filter, skip, limit
        )
        return (
            self._decrypt_chat_models_list(results)
            if self._encryption_enabled
            else results
        )

    def get_archived_chat_list_by_user_id(
        self,
        user_id: str,
        filter: Optional[dict] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[ChatModel]:
        """Override to decrypt chat data after retrieving."""
        results = super().get_archived_chat_list_by_user_id(
            user_id, filter, skip, limit
        )
        return (
            self._decrypt_chat_models_list(results)
            if self._encryption_enabled
            else results
        )

    def get_chats(self, skip: int = 0, limit: int = 50) -> list[ChatModel]:
        """Override to decrypt chat data after retrieving."""
        results = super().get_chats(skip, limit)
        return (
            self._decrypt_chat_models_list(results)
            if self._encryption_enabled
            else results
        )

    def get_chats_by_user_id(self, user_id: str) -> list[ChatModel]:
        """Override to decrypt chat data after retrieving."""
        if not self._encryption_enabled:
            return super().get_chats_by_user_id(user_id)

        try:
            with get_db() as db:
                all_chats = (
                    db.query(Chat)
                    .filter_by(user_id=user_id)
                    .order_by(Chat.updated_at.desc())
                )

                chat_models = []
                for chat_record in all_chats:
                    chat_model = self._create_chat_model_from_db_record(chat_record)
                    if chat_model is not None:  # Skip corrupted/undecryptable chats
                        chat_models.append(chat_model)

                return chat_models

        except Exception as e:
            log.error(f"Error in get_chats_by_user_id: {e}")
            # Fallback: try parent method but handle potential validation errors
            try:
                results = super().get_chats_by_user_id(user_id)
                return self._decrypt_chat_models_list(results)
            except Exception as fallback_error:
                log.error(f"Fallback also failed: {fallback_error}")
                return []

    def get_pinned_chats_by_user_id(self, user_id: str) -> list[ChatModel]:
        """Override to decrypt chat data after retrieving."""
        if not self._encryption_enabled:
            return super().get_pinned_chats_by_user_id(user_id)

        try:
            with get_db() as db:
                all_chats = (
                    db.query(Chat)
                    .filter_by(user_id=user_id, pinned=True, archived=False)
                    .order_by(Chat.updated_at.desc())
                )

                chat_models = []
                for chat_record in all_chats:
                    chat_model = self._create_chat_model_from_db_record(chat_record)
                    if chat_model is not None:  # Skip corrupted/undecryptable chats
                        chat_models.append(chat_model)

                return chat_models

        except Exception as e:
            log.error(f"Error in get_pinned_chats_by_user_id: {e}")
            # Fallback: try parent method but handle potential validation errors
            try:
                results = super().get_pinned_chats_by_user_id(user_id)
                return self._decrypt_chat_models_list(results)
            except Exception as fallback_error:
                log.error(f"Fallback also failed: {fallback_error}")
                return []

    def get_archived_chats_by_user_id(self, user_id: str) -> list[ChatModel]:
        """Override to decrypt chat data after retrieving."""
        if not self._encryption_enabled:
            return super().get_archived_chats_by_user_id(user_id)

        try:
            with get_db() as db:
                all_chats = (
                    db.query(Chat)
                    .filter_by(user_id=user_id, archived=True)
                    .order_by(Chat.updated_at.desc())
                )

                chat_models = []
                for chat_record in all_chats:
                    chat_model = self._create_chat_model_from_db_record(chat_record)
                    if chat_model is not None:  # Skip corrupted/undecryptable chats
                        chat_models.append(chat_model)

                return chat_models

        except Exception as e:
            log.error(f"Error in get_archived_chats_by_user_id: {e}")
            # Fallback: try parent method but handle potential validation errors
            try:
                results = super().get_archived_chats_by_user_id(user_id)
                return self._decrypt_chat_models_list(results)
            except Exception as fallback_error:
                log.error(f"Fallback also failed: {fallback_error}")
                return []

    def get_chats_by_user_id_and_search_text(
        self,
        user_id: str,
        search_text: str,
        include_archived: bool = False,
        skip: int = 0,
        limit: int = 60,
    ) -> list[ChatModel]:
        if not self._encryption_enabled:
            return super().get_chats_by_user_id_and_search_text(
                user_id, search_text, include_archived, skip, limit
            )

        raise NotImplementedError("Searching chats is not supported")

    def get_chats_by_folder_id_and_user_id(
        self, folder_id: str, user_id: str
    ) -> list[ChatModel]:
        """Override to decrypt chat data after retrieving."""
        results = super().get_chats_by_folder_id_and_user_id(folder_id, user_id)
        return (
            self._decrypt_chat_models_list(results)
            if self._encryption_enabled
            else results
        )

    def get_chats_by_folder_ids_and_user_id(
        self, folder_ids: list[str], user_id: str
    ) -> list[ChatModel]:
        """Override to decrypt chat data after retrieving."""
        results = super().get_chats_by_folder_ids_and_user_id(folder_ids, user_id)
        return (
            self._decrypt_chat_models_list(results)
            if self._encryption_enabled
            else results
        )

    def get_chat_list_by_chat_ids(
        self, chat_ids: list[str], skip: int = 0, limit: int = 50
    ) -> list[ChatModel]:
        """Override to decrypt chat data after retrieving."""
        results = super().get_chat_list_by_chat_ids(chat_ids, skip, limit)
        return (
            self._decrypt_chat_models_list(results)
            if self._encryption_enabled
            else results
        )

    def get_chat_list_by_user_id_and_tag_name(
        self, user_id: str, tag_name: str, skip: int = 0, limit: int = 50
    ) -> list[ChatModel]:
        """Override to decrypt chat data after retrieving."""
        results = super().get_chat_list_by_user_id_and_tag_name(
            user_id, tag_name, skip, limit
        )
        return (
            self._decrypt_chat_models_list(results)
            if self._encryption_enabled
            else results
        )

    def get_chat_title_id_list_by_user_id(
        self,
        user_id: str,
        include_archived: bool = False,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
    ):
        """Override to decrypt titles in the title/id list."""
        results = super().get_chat_title_id_list_by_user_id(
            user_id, include_archived, skip, limit
        )

        if not self._encryption_enabled:
            return results

        # Decrypt titles in the response
        for item in results:
            if isinstance(item.title, str):
                try:
                    item.title = decrypt_title_data(item.title, user_id)
                except Exception as e:
                    log.error(f"Failed to decrypt title for chat {item.id}: {e}")
                    # Keep original title if decryption fails
                    pass

        return results

    # Helper methods for message extraction
    def get_messages_by_chat_id(self, id: str) -> Optional[dict]:
        """Override to decrypt before extracting messages."""
        chat = self.get_chat_by_id(id)
        if chat is None:
            return None
        return chat.chat.get("history", {}).get("messages", {}) or {}

    def get_message_by_id_and_message_id(
        self, id: str, message_id: str
    ) -> Optional[dict]:
        """Override to decrypt before extracting message."""
        chat = self.get_chat_by_id(id)
        if chat is None:
            return None
        return chat.chat.get("history", {}).get("messages", {}).get(message_id, {})

    # Shared chat methods - delegate to parent with decryption
    def insert_shared_chat_by_chat_id(self, chat_id: str) -> Optional[ChatModel]:
        """Override to handle shared chat encryption."""
        if not self._encryption_enabled:
            return super().insert_shared_chat_by_chat_id(chat_id)

        raise NotImplementedError("Inserting shared chats is not supported")

    def update_shared_chat_by_chat_id(self, chat_id: str) -> Optional[ChatModel]:
        """Override to handle shared chat encryption."""
        if not self._encryption_enabled:
            return super().update_shared_chat_by_chat_id(chat_id)

        raise NotImplementedError("Updating shared chats is not supported")
