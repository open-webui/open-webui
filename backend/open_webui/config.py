import copy
import json
import logging
import os
import shutil
import base64

from datetime import datetime
from pathlib import Path
from typing import Generic, Optional, TypeVar
from urllib.parse import urlparse

import requests
from pydantic import BaseModel
from sqlalchemy import JSON, Column, DateTime, Integer, func, Any, String
from sqlalchemy.orm.attributes import flag_modified
from open_webui.models.groups import (
    Groups)
from open_webui.models.users import (
    Users)
import inspect

from open_webui.env import (
    DATA_DIR,
    DATABASE_URL,
    ENV,
    FRONTEND_BUILD_DIR,
    OFFLINE_MODE,
    OPEN_WEBUI_DIR,
    WEBUI_AUTH,
    WEBUI_FAVICON_URL,
    WEBUI_NAME,
    log,
)
from open_webui.internal.db import Base, get_db

# Local logger for config persistence events
logger = logging.getLogger(__name__)

class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("/health") == -1


# Filter out /endpoint
logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

####################################
# Config helpers
####################################


# Function to run the alembic migrations
def run_migrations():
    log.info("Running migrations")
    try:
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config(OPEN_WEBUI_DIR / "alembic.ini")

        # Set the script location dynamically
        migrations_path = OPEN_WEBUI_DIR / "migrations"
        alembic_cfg.set_main_option("script_location", str(migrations_path))

        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        log.exception(f"Error running migrations: {e}")


run_migrations()


class Config(Base):
    __tablename__ = "config"

    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False, index=True, default="system@default")
    data = Column(JSON, nullable=False)
    version = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())


def load_json_config():
    with open(f"{DATA_DIR}/config.json", "r") as file:
        return json.load(file)


# Global config row identifier. Only this row is updated by save_to_db(CONFIG_DATA).
# User-scoped config is stored in rows with email=user@example.com and must never be overwritten.
GLOBAL_CONFIG_EMAIL = "system@default"


def save_to_db(data):
    """
    Persist global config (CONFIG_DATA) to the database.
    Only updates the global config row (email=GLOBAL_CONFIG_EMAIL). Never overwrites
    user-scoped config rows (per-email), which are updated via UserScopedConfig.set().
    """
    with get_db() as db:
        # Get full call stack for debugging
        call_stack = []
        try:
            stack = inspect.stack()
            for i in range(1, min(6, len(stack))):
                frame = stack[i]
                call_stack.append(f"{os.path.basename(frame.filename)}:{frame.function}:{frame.lineno}")
        except Exception:
            call_stack = ["unknown"]
        caller = " <- ".join(call_stack)

        existing_config = db.query(Config).filter(
            Config.email == GLOBAL_CONFIG_EMAIL
        ).first()
        if not existing_config:
            # Legacy DB may have global config in a row with NULL email
            existing_config = (
                db.query(Config).filter(Config.email.is_(None)).order_by(Config.id.asc()).first()
            )
        if not existing_config:
            new_config = Config(email=GLOBAL_CONFIG_EMAIL, data=data, version=0)
            db.add(new_config)
            logger.info(
                "===== GLOBAL CONFIG: Creating NEW config in database ===== "
                "Keys being saved: %s. Called from: %s. Full data: %s",
                list(data.keys()) if isinstance(data, dict) else "unknown",
                caller,
                data,
            )
        else:
            logger.info(
                "===== GLOBAL CONFIG: Updating EXISTING config in database ===== "
                "Config ID: %s. Old keys: %s. New keys: %s. Called from: %s. New data: %s",
                existing_config.id if hasattr(existing_config, "id") else "n/a",
                list(existing_config.data.keys()) if isinstance(existing_config.data, dict) else "unknown",
                list(data.keys()) if isinstance(data, dict) else "unknown",
                caller,
                data,
            )
            existing_config.data = data
            existing_config.updated_at = datetime.now()
            if existing_config.email is None:
                existing_config.email = GLOBAL_CONFIG_EMAIL
            db.add(existing_config)
        db.commit()
        logger.info("===== GLOBAL CONFIG: Database commit complete ===== Called from: %s", caller)


def reset_config():
    with get_db() as db:
        db.query(Config).delete()
        db.commit()


# When initializing, check if config.json exists and migrate it to the database
if os.path.exists(f"{DATA_DIR}/config.json"):
    data = load_json_config()
    save_to_db(data)
    os.rename(f"{DATA_DIR}/config.json", f"{DATA_DIR}/old_config.json")

DEFAULT_CONFIG = {
    "version": 0,
    "ui": {
        "default_locale": "",
        "prompt_suggestions": [
            {
                "title": [
                    "Help me study",
                    "vocabulary for a college entrance exam",
                ],
                "content": "Help me study vocabulary: write a sentence for me to fill in the blank, and I'll try to pick the correct option.",
            },
            {
                "title": [
                    "Give me ideas",
                    "for what to do with my kids' art",
                ],
                "content": "What are 5 creative things I could do with my kids' art? I don't want to throw them away, but it's also so much clutter.",
            },
            {
                "title": ["Tell me a fun fact", "about the Roman Empire"],
                "content": "Tell me a random fun fact about the Roman Empire",
            },
            {
                "title": [
                    "Show me a code snippet",
                    "of a website's sticky header",
                ],
                "content": "Show me a code snippet of a website's sticky header in CSS and JavaScript.",
            },
            {
                "title": [
                    "Explain options trading",
                    "if I'm familiar with buying and selling stocks",
                ],
                "content": "Explain options trading in simple terms if I'm familiar with buying and selling stocks.",
            },
            {
                "title": ["Overcome procrastination", "give me tips"],
                "content": "Could you start by asking me about instances when I procrastinate the most and then give me some suggestions to overcome it?",
            },
            {
                "title": [
                    "Grammar check",
                    "rewrite it for better readability ",
                ],
                "content": 'Check the following sentence for grammar and clarity: "[sentence]". Rewrite it for better readability while maintaining its original meaning.',
            },
        ],
    },
}


def get_config():
    """Load global config for CONFIG_DATA. Prefers the global row (system@default)."""
    with get_db() as db:
        config_entry = db.query(Config).filter(
            Config.email == GLOBAL_CONFIG_EMAIL
        ).first()
        if not config_entry:
            config_entry = (
                db.query(Config).filter(Config.email.is_(None)).order_by(Config.id.asc()).first()
                or db.query(Config).order_by(Config.id.desc()).first()
            )
        return config_entry.data if config_entry else DEFAULT_CONFIG

from sqlalchemy import create_engine, inspect, text

def ensure_config_email_column():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        inspector = inspect(conn)
        columns = [col["name"] for col in inspector.get_columns("config")]
        if "email" not in columns:
            print("🔧 Adding missing column: config.email")
            conn.execute(text('ALTER TABLE "config" ADD COLUMN email TEXT DEFAULT \'system@default\';'))
            print(" Column 'email' added successfully")
        else:
            print("Column 'email' already exists")

ensure_config_email_column()

CONFIG_DATA = get_config()


def get_config_value(config_path: str):
    path_parts = config_path.split(".")
    cur_config = CONFIG_DATA
    for key in path_parts:
        if key in cur_config:
            cur_config = cur_config[key]
        else:
            return None
    return cur_config


PERSISTENT_CONFIG_REGISTRY = []


def save_config(config):
    global CONFIG_DATA
    global PERSISTENT_CONFIG_REGISTRY
    try:
        save_to_db(config)
        CONFIG_DATA = config

        # Trigger updates on all registered PersistentConfig entries
        for config_item in PERSISTENT_CONFIG_REGISTRY:
            config_item.update()
    except Exception as e:
        log.exception(e)
        return False
    return True


T = TypeVar("T")


class PersistentConfig(Generic[T]):
    def __init__(self, env_name: str, config_path: str, env_value: T):
        self.env_name = env_name
        self.config_path = config_path
        self.env_value = env_value
        self.config_value = get_config_value(config_path)
        if self.config_value is not None:
            log.info(f"'{env_name}' loaded from the latest database entry")
            self.value = self.config_value
        else:
            self.value = env_value

        PERSISTENT_CONFIG_REGISTRY.append(self)

    def __str__(self):
        return str(self.value)

    @property
    def __dict__(self):
        raise TypeError(
            "PersistentConfig object cannot be converted to dict, use config_get or .value instead."
        )

    def __getattribute__(self, item):
        if item == "__dict__":
            raise TypeError(
                "PersistentConfig object cannot be converted to dict, use config_get or .value instead."
            )
        return super().__getattribute__(item)

    def update(self):
        new_value = get_config_value(self.config_path)
        if new_value is not None:
            self.value = new_value
            log.info(f"Updated {self.env_name} to new value {self.value}")

    def save(self):
        log.info(f"Saving '{self.env_name}' to the database")
        path_parts = self.config_path.split(".")
        sub_config = CONFIG_DATA
        for key in path_parts[:-1]:
            if key not in sub_config:
                sub_config[key] = {}
            sub_config = sub_config[key]
        sub_config[path_parts[-1]] = self.value
        save_to_db(CONFIG_DATA)
        self.config_value = self.value

class UserScopedConfig:
    def __init__(self, config_path: str, default: Any):
        self.config_path = config_path
        self.default = default

    # def get(self, email: str) -> Any:
    #     with get_db() as db:
    #         entry = db.query(Config).filter_by(email=email).first()
    #         if entry and isinstance(entry.data, dict):
    #             data = entry.data
    #             for part in self.config_path.split("."):
    #                 if isinstance(data, dict) and part in data:
    #                     data = data[part]
    #                 else:
    #                     return self.default
    #             return data
        
    # # Step 2: If not found, try group creator lookup
    #         user_id = Users.get_user_by_email(email)
    #         user_groups = []
    #         user_groups = Groups.get_groups_by_member_id(user_id)
    #         for group in user_groups:
    #             group_creator_email = group.created_by  
    #             if group_creator_email:
    #                 creator_entry = db.query(Config).filter_by(email=group_creator_email).first()
    #                 if creator_entry and isinstance(creator_entry.data, dict):
    #                     data = creator_entry.data
    #                     for part in self.config_path.split("."):
    #                         if isinstance(data, dict) and part in data:
    #                             data = data[part]
    #                         else:
    #                             return self.default
    #                     return data

    #         # Step 3: If still nothing, return default
    #     return self.default
        
    def _get_for_user_direct(self, email: str, user) -> Any:
        """
        Get config for non-admin users by querying PostgreSQL directly.
        Bypasses cache entirely to avoid cache hit/miss consistency issues
        when users inherit API keys and settings from group admins.
        """
        logging.debug(
            f"[RBAC_CONFIG_GET] _get_for_user_direct() entered: email={email}, "
            f"user_id={user.id}, config_path={self.config_path}"
        )
        with get_db() as db:
            # Check group creator's config
            user_groups = Groups.get_groups_by_member_id(user.id)
            logging.debug(
                f"[RBAC_CONFIG_GET] _get_for_user_direct() group admin: "
                f"user {email} in {len(user_groups)} group(s): "
                f"{[(g.id, g.created_by) for g in user_groups]}"
            )
            for group in user_groups:
                group_creator_email = group.created_by
                if not group_creator_email:
                    continue
                creator_entry = db.query(Config).filter_by(email=group_creator_email).first()
                if creator_entry and isinstance(creator_entry.data, dict):
                    data = creator_entry.data
                    final_value = self.default
                    for part in self.config_path.split("."):
                        if isinstance(data, dict) and part in data:
                            data = data[part]
                            final_value = data
                        else:
                            final_value = self.default
                            break
                    if final_value != self.default:
                        is_api_key = "api_key" in self.config_path or "openai_api_key" in self.config_path
                        if is_api_key:
                            logging.debug(
                                f"[RBAC_CONFIG_GET] User {email} inheriting API key from group admin "
                                f"{group_creator_email} (group {group.id}) via PostgreSQL direct"
                            )
                        return final_value

        logging.debug(
            f"[RBAC_CONFIG_GET] _get_for_user_direct() returning default for email={email}, "
            f"config_path={self.config_path}"
        )
        return self.default

    def get(self, email: str) -> Any:
        logging.debug(f"[RBAC_CONFIG_GET] get() called: config_path={self.config_path}, email={email}")

        user = Users.get_user_by_email(email)
        if not user:
            logging.debug(f"[RBAC_CONFIG_GET] User {email} not found, returning default for {self.config_path}")
            return self.default

        # Avoids cache hit/miss consistency issues for users inheriting from group admins
        if user.role != "admin":
            logging.debug(f"[RBAC_CONFIG_GET] User {email} (ID: {user.id}) is non-admin - using PostgreSQL direct")
            return self._get_for_user_direct(email, user)

        logging.debug(
            f"[RBAC_CONFIG_GET] Admin path: checking cache for admin {email} "
            f"(ID: {user.id}), config_path={self.config_path}"
        )
        from open_webui.utils.cache import get_cache_manager
        cache = get_cache_manager()

        cached_value = cache.get_user_settings(user.id, self.config_path)
        if cached_value is not None:
            logging.debug(f"[RBAC_CONFIG_GET] Cache hit for admin {email} config {self.config_path}")
            return cached_value

        with get_db() as db:
            entry = db.query(Config).filter_by(email=email).first()
            if entry and isinstance(entry.data, dict):
                data = entry.data
                final_value = self.default
                for part in self.config_path.split("."):
                    if isinstance(data, dict) and part in data:
                        data = data[part]
                        final_value = data
                    else:
                        final_value = self.default
                        break
                if final_value != self.default:
                    logging.debug(
                        f"[RBAC_CONFIG_GET] Admin {email}: found config in DB, "
                        f"config_path={self.config_path}, caching and returning"
                    )
                    cache.set_user_settings(user.id, self.config_path, final_value)
                    return final_value

        logging.debug(
            f"[RBAC_CONFIG_GET] Admin {email}: no config in DB, "
            f"returning default for config_path={self.config_path}"
        )
        cache.set_user_settings(user.id, self.config_path, self.default)
        return self.default

    def set(self, email: str, value: Any):
        """
        Set a user-scoped configuration value.
        
        RBAC Note: For API keys (rag.openai_api_key), this stores the key under the admin's email.
        The key will be accessible to:
        1. The admin themselves (when they use their own email to lookup)
        2. Users in groups created by this admin (via group inheritance)
        3. NOT accessible to other admins or users in other admins' groups
        
        This ensures proper RBAC isolation between different admins and their groups.
        """
        from open_webui.utils.cache import get_cache_manager
        
        cache = get_cache_manager()
        
        # Get caller information for debugging
        caller = "unknown"
        call_stack = []
        try:
            stack = inspect.stack()
            # Get the immediate caller (index 1) and a few more levels for context
            for i in range(1, min(5, len(stack))):
                frame = stack[i]
                call_stack.append(f"{os.path.basename(frame.filename)}:{frame.function}:{frame.lineno}")
            caller = " <- ".join(call_stack)
        except Exception:
            pass
        
        # RBAC: Log API key configuration for audit
        is_api_key = "api_key" in self.config_path or "openai_api_key" in self.config_path
        logging.debug(
            f"[RBAC_CONFIG_SET] set() called: config_path={self.config_path}, email={email}, "
            f"caller={caller}"
        )
        if is_api_key:
            logging.debug(
                f"[RBAC_CONFIG_SET] API key being changed for admin '{email}', "
                f"config_path={self.config_path}, caller={caller}"
            )
        
        with get_db() as db:
            entry = db.query(Config).filter_by(email=email).first()
            if not entry:
                entry = Config(email=email, data={})
                db.add(entry)

            # CRITICAL FIX: Create a deep copy of the data dict to ensure SQLAlchemy
            # detects the change. In-place modification of JSON columns may not be
            # tracked properly even with flag_modified in some SQLAlchemy/PostgreSQL cases.
            old_data = entry.data
            data = copy.deepcopy(entry.data) if entry.data else {}
            
            logging.debug(
                f"[RBAC_CONFIG_SET] Current DB value for '{email}' before change: {old_data}"
            )
            
            current = data
            parts = self.config_path.split(".")
            for part in parts[:-1]:
                if part not in current or not isinstance(current[part], dict):
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value

            logging.debug(
                f"[RBAC_CONFIG_SET] New value being saved for '{email}': "
                f"config_path={self.config_path}, caller={caller}"
            )

            # Assign the new dict object (not the same reference)
            entry.data = data
            entry.updated_at = datetime.now()
            flag_modified(entry, "data")
            db.commit()
            
            logging.debug(
                f"[RBAC_CONFIG_SET] Config saved to DB for '{email}': "
                f"config_path={self.config_path}, caller={caller}"
            )
        
        # CRITICAL RBAC: Update cache with new value (write-through caching)
        # This ensures subsequent GET requests get the new value from cache
        user = Users.get_user_by_email(email)
        if user:
            # Step 1: Invalidate old cache entries first (for this user and inherited groups)
            logging.debug(
                f"[RBAC_CONFIG_SET] Invalidating cache for admin {email} (ID: {user.id}), "
                f"config_path={self.config_path}"
            )
            cache.invalidate_user_settings(user.id, self.config_path)
            
            # Step 2: Set the new value in cache (write-through)
            cache.set_user_settings(user.id, self.config_path, value)
            logging.debug(
                f"[RBAC_CONFIG_SET] Cache updated for user '{email}' (ID: {user.id}), "
                f"config_path={self.config_path}"
            )
            
            # Step 3: Invalidate cache for all users who inherit from this admin (group members)
            # They need to re-fetch to get the new inherited value
            groups = Groups.get_groups(email)
            if is_api_key:
                logging.debug(
                    f"[RBAC_CONFIG_SET] Invalidating inherited cache for admin {email}'s "
                    f"{len(groups)} group(s) to propagate new API key"
                )
            for group in groups:
                # Invalidate group admin config cache
                cache.invalidate_group_admin_config(group.id, self.config_path)
                # Invalidate cache for all members of this group (they inherit from admin)
                member_count = cache.invalidate_group_member_users(group.id)
                logging.debug(
                    f"[RBAC_CONFIG_SET] Invalidated cache for {member_count} member(s) "
                    f"of group {group.id} created by {email}"
                )



class AppConfig:
    _state: dict[str, PersistentConfig | UserScopedConfig ]

    def __init__(self):
        super().__setattr__("_state", {})

    def __setattr__(self, key, value):
        # Support PersistentConfig and UserScopedConfig both
        if isinstance(value, (PersistentConfig, UserScopedConfig)):
            self._state[key] = value
        else:
            # Update the config's internal value and persist it
            if isinstance(self._state[key], PersistentConfig):
                self._state[key].value = value
                self._state[key].save()
            elif isinstance(self._state[key], UserScopedConfig):
                raise TypeError("Use .set(email, value) to update UserScopedConfig.")
            
    def __getattr__(self, key):
        config_obj = self._state[key]
        if isinstance(config_obj, PersistentConfig):
            return config_obj.value
        return config_obj

    # def __getattr__(self, key):
    #     return self._state[key]  # return the whole config object (not just .value)





# class AppConfig:
#     _state: dict[str, PersistentConfig]

#     def __init__(self):
#         super().__setattr__("_state", {})

#     def __setattr__(self, key, value):
#         if isinstance(value, PersistentConfig):
#             self._state[key] = value
#         else:
#             self._state[key].value = value
#             self._state[key].save()

#     def __getattr__(self, key):
#         return self._state[key]


####################################
# WEBUI_AUTH (Required for security)
####################################

ENABLE_API_KEY = PersistentConfig(
    "ENABLE_API_KEY",
    "auth.api_key.enable",
    os.environ.get("ENABLE_API_KEY", "True").lower() == "true",
)

ENABLE_API_KEY_ENDPOINT_RESTRICTIONS = PersistentConfig(
    "ENABLE_API_KEY_ENDPOINT_RESTRICTIONS",
    "auth.api_key.endpoint_restrictions",
    os.environ.get("ENABLE_API_KEY_ENDPOINT_RESTRICTIONS", "False").lower() == "true",
)

API_KEY_ALLOWED_ENDPOINTS = PersistentConfig(
    "API_KEY_ALLOWED_ENDPOINTS",
    "auth.api_key.allowed_endpoints",
    os.environ.get("API_KEY_ALLOWED_ENDPOINTS", ""),
)


JWT_EXPIRES_IN = PersistentConfig(
    "JWT_EXPIRES_IN", "auth.jwt_expiry", os.environ.get("JWT_EXPIRES_IN", "-1")
)

####################################
# Pilot GenAI Terms & Conditions
####################################

PILOT_GENAI_TERMS_VERSION = PersistentConfig(
    "PILOT_GENAI_TERMS_VERSION",
    "pilot_genai.terms.version",
    int(os.environ.get("PILOT_GENAI_TERMS_VERSION", "1")),
)

####################################
# OAuth config
####################################

ENABLE_OAUTH_SIGNUP = PersistentConfig(
    "ENABLE_OAUTH_SIGNUP",
    "oauth.enable_signup",
    os.environ.get("ENABLE_OAUTH_SIGNUP", "False").lower() == "true",
)

OAUTH_MERGE_ACCOUNTS_BY_EMAIL = PersistentConfig(
    "OAUTH_MERGE_ACCOUNTS_BY_EMAIL",
    "oauth.merge_accounts_by_email",
    os.environ.get("OAUTH_MERGE_ACCOUNTS_BY_EMAIL", "False").lower() == "true",
)

OAUTH_PROVIDERS = {}

GOOGLE_CLIENT_ID = PersistentConfig(
    "GOOGLE_CLIENT_ID",
    "oauth.google.client_id",
    os.environ.get("GOOGLE_CLIENT_ID", ""),
)

GOOGLE_CLIENT_SECRET = PersistentConfig(
    "GOOGLE_CLIENT_SECRET",
    "oauth.google.client_secret",
    os.environ.get("GOOGLE_CLIENT_SECRET", ""),
)


GOOGLE_OAUTH_SCOPE = PersistentConfig(
    "GOOGLE_OAUTH_SCOPE",
    "oauth.google.scope",
    os.environ.get("GOOGLE_OAUTH_SCOPE", "openid email profile"),
)

GOOGLE_REDIRECT_URI = PersistentConfig(
    "GOOGLE_REDIRECT_URI",
    "oauth.google.redirect_uri",
    os.environ.get("GOOGLE_REDIRECT_URI", ""),
)

MICROSOFT_CLIENT_ID = PersistentConfig(
    "MICROSOFT_CLIENT_ID",
    "oauth.microsoft.client_id",
    os.environ.get("MICROSOFT_CLIENT_ID", ""),
)

MICROSOFT_CLIENT_SECRET = PersistentConfig(
    "MICROSOFT_CLIENT_SECRET",
    "oauth.microsoft.client_secret",
    os.environ.get("MICROSOFT_CLIENT_SECRET", ""),
)

MICROSOFT_CLIENT_TENANT_ID = PersistentConfig(
    "MICROSOFT_CLIENT_TENANT_ID",
    "oauth.microsoft.tenant_id",
    os.environ.get("MICROSOFT_CLIENT_TENANT_ID", ""),
)

MICROSOFT_OAUTH_SCOPE = PersistentConfig(
    "MICROSOFT_OAUTH_SCOPE",
    "oauth.microsoft.scope",
    os.environ.get("MICROSOFT_OAUTH_SCOPE", "openid email profile"),
)

MICROSOFT_REDIRECT_URI = PersistentConfig(
    "MICROSOFT_REDIRECT_URI",
    "oauth.microsoft.redirect_uri",
    os.environ.get("MICROSOFT_REDIRECT_URI", ""),
)

GITHUB_CLIENT_ID = PersistentConfig(
    "GITHUB_CLIENT_ID",
    "oauth.github.client_id",
    os.environ.get("GITHUB_CLIENT_ID", ""),
)

GITHUB_CLIENT_SECRET = PersistentConfig(
    "GITHUB_CLIENT_SECRET",
    "oauth.github.client_secret",
    os.environ.get("GITHUB_CLIENT_SECRET", ""),
)

GITHUB_CLIENT_SCOPE = PersistentConfig(
    "GITHUB_CLIENT_SCOPE",
    "oauth.github.scope",
    os.environ.get("GITHUB_CLIENT_SCOPE", "user:email"),
)

GITHUB_CLIENT_REDIRECT_URI = PersistentConfig(
    "GITHUB_CLIENT_REDIRECT_URI",
    "oauth.github.redirect_uri",
    os.environ.get("GITHUB_CLIENT_REDIRECT_URI", ""),
)

OAUTH_CLIENT_ID = PersistentConfig(
    "OAUTH_CLIENT_ID",
    "oauth.oidc.client_id",
    os.environ.get("OAUTH_CLIENT_ID", ""),
)

OAUTH_CLIENT_SECRET = PersistentConfig(
    "OAUTH_CLIENT_SECRET",
    "oauth.oidc.client_secret",
    os.environ.get("OAUTH_CLIENT_SECRET", ""),
)

OPENID_PROVIDER_URL = PersistentConfig(
    "OPENID_PROVIDER_URL",
    "oauth.oidc.provider_url",
    os.environ.get("OPENID_PROVIDER_URL", ""),
)

OPENID_REDIRECT_URI = PersistentConfig(
    "OPENID_REDIRECT_URI",
    "oauth.oidc.redirect_uri",
    os.environ.get("OPENID_REDIRECT_URI", ""),
)

OAUTH_SCOPES = PersistentConfig(
    "OAUTH_SCOPES",
    "oauth.oidc.scopes",
    os.environ.get("OAUTH_SCOPES", "openid email profile"),
)

OAUTH_PROVIDER_NAME = PersistentConfig(
    "OAUTH_PROVIDER_NAME",
    "oauth.oidc.provider_name",
    os.environ.get("OAUTH_PROVIDER_NAME", "SSO"),
)

OAUTH_USERNAME_CLAIM = PersistentConfig(
    "OAUTH_USERNAME_CLAIM",
    "oauth.oidc.username_claim",
    os.environ.get("OAUTH_USERNAME_CLAIM", "name"),
)

OAUTH_PICTURE_CLAIM = PersistentConfig(
    "OAUTH_PICTURE_CLAIM",
    "oauth.oidc.avatar_claim",
    os.environ.get("OAUTH_PICTURE_CLAIM", "picture"),
)

OAUTH_EMAIL_CLAIM = PersistentConfig(
    "OAUTH_EMAIL_CLAIM",
    "oauth.oidc.email_claim",
    os.environ.get("OAUTH_EMAIL_CLAIM", "email"),
)

OAUTH_GROUPS_CLAIM = PersistentConfig(
    "OAUTH_GROUPS_CLAIM",
    "oauth.oidc.group_claim",
    os.environ.get("OAUTH_GROUP_CLAIM", "groups"),
)

ENABLE_OAUTH_ROLE_MANAGEMENT = PersistentConfig(
    "ENABLE_OAUTH_ROLE_MANAGEMENT",
    "oauth.enable_role_mapping",
    os.environ.get("ENABLE_OAUTH_ROLE_MANAGEMENT", "False").lower() == "true",
)

ENABLE_OAUTH_GROUP_MANAGEMENT = PersistentConfig(
    "ENABLE_OAUTH_GROUP_MANAGEMENT",
    "oauth.enable_group_mapping",
    os.environ.get("ENABLE_OAUTH_GROUP_MANAGEMENT", "False").lower() == "true",
)

OAUTH_ROLES_CLAIM = PersistentConfig(
    "OAUTH_ROLES_CLAIM",
    "oauth.roles_claim",
    os.environ.get("OAUTH_ROLES_CLAIM", "roles"),
)

OAUTH_ALLOWED_ROLES = PersistentConfig(
    "OAUTH_ALLOWED_ROLES",
    "oauth.allowed_roles",
    [
        role.strip()
        for role in os.environ.get("OAUTH_ALLOWED_ROLES", "user,admin").split(",")
    ],
)

OAUTH_ADMIN_ROLES = PersistentConfig(
    "OAUTH_ADMIN_ROLES",
    "oauth.admin_roles",
    [role.strip() for role in os.environ.get("OAUTH_ADMIN_ROLES", "admin").split(",")],
)

OAUTH_ALLOWED_DOMAINS = PersistentConfig(
    "OAUTH_ALLOWED_DOMAINS",
    "oauth.allowed_domains",
    [
        domain.strip()
        for domain in os.environ.get("OAUTH_ALLOWED_DOMAINS", "*").split(",")
    ],
)


def load_oauth_providers():
    OAUTH_PROVIDERS.clear()
    if GOOGLE_CLIENT_ID.value and GOOGLE_CLIENT_SECRET.value:

        def google_oauth_register(client):
            client.register(
                name="google",
                client_id=GOOGLE_CLIENT_ID.value,
                client_secret=GOOGLE_CLIENT_SECRET.value,
                server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
                client_kwargs={"scope": GOOGLE_OAUTH_SCOPE.value},
                redirect_uri=GOOGLE_REDIRECT_URI.value,
            )

        OAUTH_PROVIDERS["google"] = {
            "redirect_uri": GOOGLE_REDIRECT_URI.value,
            "register": google_oauth_register,
        }

    if (
        MICROSOFT_CLIENT_ID.value
        and MICROSOFT_CLIENT_SECRET.value
        and MICROSOFT_CLIENT_TENANT_ID.value
    ):

        def microsoft_oauth_register(client):
            client.register(
                name="microsoft",
                client_id=MICROSOFT_CLIENT_ID.value,
                client_secret=MICROSOFT_CLIENT_SECRET.value,
                server_metadata_url=f"https://login.microsoftonline.com/{MICROSOFT_CLIENT_TENANT_ID.value}/v2.0/.well-known/openid-configuration",
                client_kwargs={
                    "scope": MICROSOFT_OAUTH_SCOPE.value,
                },
                redirect_uri=MICROSOFT_REDIRECT_URI.value,
            )

        OAUTH_PROVIDERS["microsoft"] = {
            "redirect_uri": MICROSOFT_REDIRECT_URI.value,
            "picture_url": "https://graph.microsoft.com/v1.0/me/photo/$value",
            "register": microsoft_oauth_register,
        }

    if GITHUB_CLIENT_ID.value and GITHUB_CLIENT_SECRET.value:

        def github_oauth_register(client):
            client.register(
                name="github",
                client_id=GITHUB_CLIENT_ID.value,
                client_secret=GITHUB_CLIENT_SECRET.value,
                access_token_url="https://github.com/login/oauth/access_token",
                authorize_url="https://github.com/login/oauth/authorize",
                api_base_url="https://api.github.com",
                userinfo_endpoint="https://api.github.com/user",
                client_kwargs={"scope": GITHUB_CLIENT_SCOPE.value},
                redirect_uri=GITHUB_CLIENT_REDIRECT_URI.value,
            )

        OAUTH_PROVIDERS["github"] = {
            "redirect_uri": GITHUB_CLIENT_REDIRECT_URI.value,
            "register": github_oauth_register,
            "sub_claim": "id",
        }

    if (
        OAUTH_CLIENT_ID.value
        and OAUTH_CLIENT_SECRET.value
        and OPENID_PROVIDER_URL.value
    ):

        def oidc_oauth_register(client):
            client.register(
                name="oidc",
                client_id=OAUTH_CLIENT_ID.value,
                client_secret=OAUTH_CLIENT_SECRET.value,
                server_metadata_url=OPENID_PROVIDER_URL.value,
                client_kwargs={
                    "scope": OAUTH_SCOPES.value,
                },
                redirect_uri=OPENID_REDIRECT_URI.value,
            )

        OAUTH_PROVIDERS["oidc"] = {
            "name": OAUTH_PROVIDER_NAME.value,
            "redirect_uri": OPENID_REDIRECT_URI.value,
            "register": oidc_oauth_register,
        }


load_oauth_providers()

####################################
# Static DIR
####################################

STATIC_DIR = Path(os.getenv("STATIC_DIR", OPEN_WEBUI_DIR / "static")).resolve()

frontend_favicon = FRONTEND_BUILD_DIR / "static" / "favicon.png"

if frontend_favicon.exists():
    try:
        shutil.copyfile(frontend_favicon, STATIC_DIR / "favicon.png")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

frontend_splash = FRONTEND_BUILD_DIR / "static" / "splash.png"

if frontend_splash.exists():
    try:
        shutil.copyfile(frontend_splash, STATIC_DIR / "splash.png")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

frontend_loader = FRONTEND_BUILD_DIR / "static" / "loader.js"

if frontend_loader.exists():
    try:
        shutil.copyfile(frontend_loader, STATIC_DIR / "loader.js")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

frontend_favicon_violet = FRONTEND_BUILD_DIR / "static" / "favicon-violet.png"

if frontend_favicon_violet.exists():
    try:
        shutil.copyfile(frontend_favicon_violet, STATIC_DIR / "favicon-violet.png")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

frontend_favicon_white = FRONTEND_BUILD_DIR / "static" / "favicon-white.png"

if frontend_favicon_white.exists():
    try:
        shutil.copyfile(frontend_favicon_white, STATIC_DIR / "favicon-white.png")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

user_temp = FRONTEND_BUILD_DIR / "static" / "user_temp.png"

if user_temp.exists():
    try:
        shutil.copyfile(user_temp, STATIC_DIR / "user_temp.png")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

frontend_flower_violet = FRONTEND_BUILD_DIR / "static" / "flower-violet.png"

if frontend_flower_violet.exists():
    try:
        shutil.copyfile(frontend_flower_violet, STATIC_DIR / "flower-violet.png")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

frontend_flower_white = FRONTEND_BUILD_DIR / "static" / "flower-white.png"

if frontend_flower_white.exists():
    try:
        shutil.copyfile(frontend_flower_white, STATIC_DIR / "flower-white.png")
    except Exception as e:
        logging.error(f"An error occurred: {e}")


####################################
# CUSTOM_NAME (Legacy)
####################################

CUSTOM_NAME = os.environ.get("CUSTOM_NAME", "")

if CUSTOM_NAME:
    try:
        r = requests.get(f"https://api.openwebui.com/api/v1/custom/{CUSTOM_NAME}")
        data = r.json()
        if r.ok:
            if "logo" in data:
                WEBUI_FAVICON_URL = url = (
                    f"https://api.openwebui.com{data['logo']}"
                    if data["logo"][0] == "/"
                    else data["logo"]
                )

                r = requests.get(url, stream=True)
                if r.status_code == 200:
                    with open(f"{STATIC_DIR}/favicon.png", "wb") as f:
                        r.raw.decode_content = True
                        shutil.copyfileobj(r.raw, f)

            if "splash" in data:
                url = (
                    f"https://api.openwebui.com{data['splash']}"
                    if data["splash"][0] == "/"
                    else data["splash"]
                )

                r = requests.get(url, stream=True)
                if r.status_code == 200:
                    with open(f"{STATIC_DIR}/splash.png", "wb") as f:
                        r.raw.decode_content = True
                        shutil.copyfileobj(r.raw, f)

            WEBUI_NAME = data["name"]
    except Exception as e:
        log.exception(e)
        pass


####################################
# LICENSE_KEY
####################################

LICENSE_KEY = PersistentConfig(
    "LICENSE_KEY",
    "license.key",
    os.environ.get("LICENSE_KEY", ""),
)

####################################
# STORAGE PROVIDER
####################################

STORAGE_PROVIDER = os.environ.get("STORAGE_PROVIDER", "local")  # defaults to local, s3

S3_ACCESS_KEY_ID = os.environ.get("S3_ACCESS_KEY_ID", None)
S3_SECRET_ACCESS_KEY = os.environ.get("S3_SECRET_ACCESS_KEY", None)
S3_REGION_NAME = os.environ.get("S3_REGION_NAME", None)
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", None)
S3_KEY_PREFIX = os.environ.get("S3_KEY_PREFIX", None)
S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL", None)
S3_USE_ACCELERATE_ENDPOINT = (
    os.environ.get("S3_USE_ACCELERATE_ENDPOINT", "False").lower() == "true"
)
S3_ADDRESSING_STYLE = os.environ.get("S3_ADDRESSING_STYLE", None)

GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", None)
GOOGLE_APPLICATION_CREDENTIALS_JSON = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS_JSON", None
)

AZURE_STORAGE_ENDPOINT = os.environ.get("AZURE_STORAGE_ENDPOINT", None)
AZURE_STORAGE_CONTAINER_NAME = os.environ.get("AZURE_STORAGE_CONTAINER_NAME", None)
AZURE_STORAGE_KEY = os.environ.get("AZURE_STORAGE_KEY", None)

####################################
# File Upload DIR
####################################

UPLOAD_DIR = f"{DATA_DIR}/uploads"
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


####################################
# Cache DIR
####################################

CACHE_DIR = f"{DATA_DIR}/cache"
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)


####################################
# DIRECT CONNECTIONS
####################################

ENABLE_DIRECT_CONNECTIONS = PersistentConfig(
    "ENABLE_DIRECT_CONNECTIONS",
    "direct.enable",
    os.environ.get("ENABLE_DIRECT_CONNECTIONS", "True").lower() == "true",
)

####################################
# OLLAMA_BASE_URL
####################################

ENABLE_OLLAMA_API = PersistentConfig(
    "ENABLE_OLLAMA_API",
    "ollama.enable",
    os.environ.get("ENABLE_OLLAMA_API", "True").lower() == "true",
)

OLLAMA_API_BASE_URL = os.environ.get(
    "OLLAMA_API_BASE_URL", "http://localhost:11434/api"
)

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "")
if OLLAMA_BASE_URL:
    # Remove trailing slash
    OLLAMA_BASE_URL = (
        OLLAMA_BASE_URL[:-1] if OLLAMA_BASE_URL.endswith("/") else OLLAMA_BASE_URL
    )


K8S_FLAG = os.environ.get("K8S_FLAG", "")
USE_OLLAMA_DOCKER = os.environ.get("USE_OLLAMA_DOCKER", "false")

if OLLAMA_BASE_URL == "" and OLLAMA_API_BASE_URL != "":
    OLLAMA_BASE_URL = (
        OLLAMA_API_BASE_URL[:-4]
        if OLLAMA_API_BASE_URL.endswith("/api")
        else OLLAMA_API_BASE_URL
    )

if ENV == "prod":
    if OLLAMA_BASE_URL == "/ollama" and not K8S_FLAG:
        if USE_OLLAMA_DOCKER.lower() == "true":
            # if you use all-in-one docker container (Open WebUI + Ollama)
            # with the docker build arg USE_OLLAMA=true (--build-arg="USE_OLLAMA=true") this only works with http://localhost:11434
            OLLAMA_BASE_URL = "http://localhost:11434"
        else:
            OLLAMA_BASE_URL = "http://host.docker.internal:11434"
    elif K8S_FLAG:
        OLLAMA_BASE_URL = "http://ollama-service.open-webui.svc.cluster.local:11434"


OLLAMA_BASE_URLS = os.environ.get("OLLAMA_BASE_URLS", "")
OLLAMA_BASE_URLS = OLLAMA_BASE_URLS if OLLAMA_BASE_URLS != "" else OLLAMA_BASE_URL

OLLAMA_BASE_URLS = [url.strip() for url in OLLAMA_BASE_URLS.split(";")]
OLLAMA_BASE_URLS = PersistentConfig(
    "OLLAMA_BASE_URLS", "ollama.base_urls", OLLAMA_BASE_URLS
)

OLLAMA_API_CONFIGS = PersistentConfig(
    "OLLAMA_API_CONFIGS",
    "ollama.api_configs",
    {},
)

####################################
# OPENAI_API
####################################


ENABLE_OPENAI_API = PersistentConfig(
    "ENABLE_OPENAI_API",
    "openai.enable",
    os.environ.get("ENABLE_OPENAI_API", "True").lower() == "true",
)


OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_API_BASE_URL = os.environ.get("OPENAI_API_BASE_URL", "")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_API_BASE_URL = os.environ.get("GEMINI_API_BASE_URL", "")


if OPENAI_API_BASE_URL == "":
    OPENAI_API_BASE_URL = "https://api.openai.com/v1"

OPENAI_API_KEYS = os.environ.get("OPENAI_API_KEYS", "")
OPENAI_API_KEYS = OPENAI_API_KEYS if OPENAI_API_KEYS != "" else OPENAI_API_KEY

OPENAI_API_KEYS = [url.strip() for url in OPENAI_API_KEYS.split(";")]
OPENAI_API_KEYS = PersistentConfig(
    "OPENAI_API_KEYS", "openai.api_keys", OPENAI_API_KEYS
)

OPENAI_API_BASE_URLS = os.environ.get("OPENAI_API_BASE_URLS", "")
OPENAI_API_BASE_URLS = (
    OPENAI_API_BASE_URLS if OPENAI_API_BASE_URLS != "" else OPENAI_API_BASE_URL
)

OPENAI_API_BASE_URLS = [
    url.strip() if url != "" else "https://api.openai.com/v1"
    for url in OPENAI_API_BASE_URLS.split(";")
]
OPENAI_API_BASE_URLS = PersistentConfig(
    "OPENAI_API_BASE_URLS", "openai.api_base_urls", OPENAI_API_BASE_URLS
)

OPENAI_API_CONFIGS = PersistentConfig(
    "OPENAI_API_CONFIGS",
    "openai.api_configs",
    {},
)

# Get the actual OpenAI API key based on the base URL
OPENAI_API_KEY = ""
try:
    OPENAI_API_KEY = OPENAI_API_KEYS.value[
        OPENAI_API_BASE_URLS.value.index("https://api.openai.com/v1")
    ]
except Exception:
    pass
OPENAI_API_BASE_URL = "https://api.openai.com/v1"

####################################
# WEBUI
####################################


WEBUI_URL = PersistentConfig(
    "WEBUI_URL", "webui.url", os.environ.get("WEBUI_URL", "http://localhost:3000")
)


ENABLE_SIGNUP = PersistentConfig(
    "ENABLE_SIGNUP",
    "ui.enable_signup",
    (
        False
        if not WEBUI_AUTH
        else os.environ.get("ENABLE_SIGNUP", "True").lower() == "true"
    ),
)

ENABLE_LOGIN_FORM = PersistentConfig(
    "ENABLE_LOGIN_FORM",
    "ui.ENABLE_LOGIN_FORM",
    os.environ.get("ENABLE_LOGIN_FORM", "True").lower() == "true",
)


DEFAULT_LOCALE = PersistentConfig(
    "DEFAULT_LOCALE",
    "ui.default_locale",
    os.environ.get("DEFAULT_LOCALE", ""),
)

DEFAULT_MODELS = PersistentConfig(
    "DEFAULT_MODELS", "ui.default_models", os.environ.get("DEFAULT_MODELS", None)
)

DEFAULT_PROMPT_SUGGESTIONS = PersistentConfig(
    "DEFAULT_PROMPT_SUGGESTIONS",
    "ui.prompt_suggestions",
    [
        {
            "title": ["Help me study", "vocabulary for a college entrance exam"],
            "content": "Help me study vocabulary: write a sentence for me to fill in the blank, and I'll try to pick the correct option.",
        },
        {
            "title": ["Give me ideas", "for what to do with my kids' art"],
            "content": "What are 5 creative things I could do with my kids' art? I don't want to throw them away, but it's also so much clutter.",
        },
        {
            "title": ["Tell me a fun fact", "about the Roman Empire"],
            "content": "Tell me a random fun fact about the Roman Empire",
        },
        {
            "title": ["Show me a code snippet", "of a website's sticky header"],
            "content": "Show me a code snippet of a website's sticky header in CSS and JavaScript.",
        },
        {
            "title": [
                "Explain options trading",
                "if I'm familiar with buying and selling stocks",
            ],
            "content": "Explain options trading in simple terms if I'm familiar with buying and selling stocks.",
        },
        {
            "title": ["Overcome procrastination", "give me tips"],
            "content": "Could you start by asking me about instances when I procrastinate the most and then give me some suggestions to overcome it?",
        },
    ],
)

MODEL_ORDER_LIST = PersistentConfig(
    "MODEL_ORDER_LIST",
    "ui.model_order_list",
    [],
)

DEFAULT_USER_ROLE = PersistentConfig(
    "DEFAULT_USER_ROLE",
    "ui.default_user_role",
    os.getenv("DEFAULT_USER_ROLE", "pending"),
)

USER_PERMISSIONS_WORKSPACE_MODELS_ACCESS = (
    os.environ.get("USER_PERMISSIONS_WORKSPACE_MODELS_ACCESS", "False").lower()
    == "true"
)

USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ACCESS = (
    os.environ.get("USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ACCESS", "False").lower()
    == "true"
)

USER_PERMISSIONS_WORKSPACE_PROMPTS_ACCESS = (
    os.environ.get("USER_PERMISSIONS_WORKSPACE_PROMPTS_ACCESS", "False").lower()
    == "true"
)

USER_PERMISSIONS_WORKSPACE_TOOLS_ACCESS = (
    os.environ.get("USER_PERMISSIONS_WORKSPACE_TOOLS_ACCESS", "False").lower() == "true"
)

USER_PERMISSIONS_CHAT_CONTROLS = (
    os.environ.get("USER_PERMISSIONS_CHAT_CONTROLS", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_FILE_UPLOAD = (
    os.environ.get("USER_PERMISSIONS_CHAT_FILE_UPLOAD", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_DELETE = (
    os.environ.get("USER_PERMISSIONS_CHAT_DELETE", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_EDIT = (
    os.environ.get("USER_PERMISSIONS_CHAT_EDIT", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_TEMPORARY = (
    os.environ.get("USER_PERMISSIONS_CHAT_TEMPORARY", "True").lower() == "true"
)

USER_PERMISSIONS_FEATURES_WEB_SEARCH = (
    os.environ.get("USER_PERMISSIONS_FEATURES_WEB_SEARCH", "True").lower() == "true"
)

USER_PERMISSIONS_FEATURES_IMAGE_GENERATION = (
    os.environ.get("USER_PERMISSIONS_FEATURES_IMAGE_GENERATION", "True").lower()
    == "true"
)

USER_PERMISSIONS_FEATURES_CODE_INTERPRETER = (
    os.environ.get("USER_PERMISSIONS_FEATURES_CODE_INTERPRETER", "True").lower()
    == "true"
)


DEFAULT_USER_PERMISSIONS = {
    "workspace": {
        "models": USER_PERMISSIONS_WORKSPACE_MODELS_ACCESS,
        "knowledge": USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ACCESS,
        "prompts": USER_PERMISSIONS_WORKSPACE_PROMPTS_ACCESS,
        "tools": USER_PERMISSIONS_WORKSPACE_TOOLS_ACCESS,
    },
    "chat": {
        "controls": USER_PERMISSIONS_CHAT_CONTROLS,
        "file_upload": USER_PERMISSIONS_CHAT_FILE_UPLOAD,
        "delete": USER_PERMISSIONS_CHAT_DELETE,
        "edit": USER_PERMISSIONS_CHAT_EDIT,
        "temporary": USER_PERMISSIONS_CHAT_TEMPORARY,
    },
    "features": {
        "web_search": USER_PERMISSIONS_FEATURES_WEB_SEARCH,
        "image_generation": USER_PERMISSIONS_FEATURES_IMAGE_GENERATION,
        "code_interpreter": USER_PERMISSIONS_FEATURES_CODE_INTERPRETER,
    },
}

USER_PERMISSIONS = PersistentConfig(
    "USER_PERMISSIONS",
    "user.permissions",
    DEFAULT_USER_PERMISSIONS,
)

ENABLE_CHANNELS = PersistentConfig(
    "ENABLE_CHANNELS",
    "channels.enable",
    os.environ.get("ENABLE_CHANNELS", "False").lower() == "true",
)


ENABLE_EVALUATION_ARENA_MODELS = PersistentConfig(
    "ENABLE_EVALUATION_ARENA_MODELS",
    "evaluation.arena.enable",
    os.environ.get("ENABLE_EVALUATION_ARENA_MODELS", "True").lower() == "true",
)
EVALUATION_ARENA_MODELS = PersistentConfig(
    "EVALUATION_ARENA_MODELS",
    "evaluation.arena.models",
    [],
)

DEFAULT_ARENA_MODEL = {
    "id": "arena-model",
    "name": "Arena Model",
    "meta": {
        "profile_image_url": "/favicon.png",
        "description": "Submit your questions to anonymous AI chatbots and vote on the best response.",
        "model_ids": None,
    },
}

WEBHOOK_URL = PersistentConfig(
    "WEBHOOK_URL", "webhook_url", os.environ.get("WEBHOOK_URL", "")
)

ENABLE_ADMIN_EXPORT = os.environ.get("ENABLE_ADMIN_EXPORT", "True").lower() == "true"

ENABLE_ADMIN_CHAT_ACCESS = (
    os.environ.get("ENABLE_ADMIN_CHAT_ACCESS", "True").lower() == "true"
)

ENABLE_COMMUNITY_SHARING = PersistentConfig(
    "ENABLE_COMMUNITY_SHARING",
    "ui.enable_community_sharing",
    os.environ.get("ENABLE_COMMUNITY_SHARING", "True").lower() == "true",
)

ENABLE_MESSAGE_RATING = PersistentConfig(
    "ENABLE_MESSAGE_RATING",
    "ui.enable_message_rating",
    os.environ.get("ENABLE_MESSAGE_RATING", "True").lower() == "true",
)


def validate_cors_origins(origins):
    for origin in origins:
        if origin != "*":
            validate_cors_origin(origin)


def validate_cors_origin(origin):
    parsed_url = urlparse(origin)

    # Check if the scheme is either http or https
    if parsed_url.scheme not in ["http", "https"]:
        raise ValueError(
            f"Invalid scheme in CORS_ALLOW_ORIGIN: '{origin}'. Only 'http' and 'https' are allowed."
        )

    # Ensure that the netloc (domain + port) is present, indicating it's a valid URL
    if not parsed_url.netloc:
        raise ValueError(f"Invalid URL structure in CORS_ALLOW_ORIGIN: '{origin}'.")


# For production, you should only need one host as
# fastapi serves the svelte-kit built frontend and backend from the same host and port.
# To test CORS_ALLOW_ORIGIN locally, you can set something like
CORS_ALLOW_ORIGIN = "http://localhost:5173;http://localhost:8080"
# in your .env file depending on your frontend port, 5173 in this case.
CORS_ALLOW_ORIGIN = os.environ.get("CORS_ALLOW_ORIGIN", "*").split(";")

if "*" in CORS_ALLOW_ORIGIN:
    log.warning(
        "\n\nWARNING: CORS_ALLOW_ORIGIN IS SET TO '*' - NOT RECOMMENDED FOR PRODUCTION DEPLOYMENTS.\n"
    )

validate_cors_origins(CORS_ALLOW_ORIGIN)


class BannerModel(BaseModel):
    id: str
    type: str
    title: Optional[str] = None
    content: str
    dismissible: bool
    timestamp: int


try:
    banners = json.loads(os.environ.get("WEBUI_BANNERS", "[]"))
    banners = [BannerModel(**banner) for banner in banners]
except Exception as e:
    log.exception(f"Error loading WEBUI_BANNERS: {e}")
    banners = []

WEBUI_BANNERS = PersistentConfig("WEBUI_BANNERS", "ui.banners", banners)


SHOW_ADMIN_DETAILS = PersistentConfig(
    "SHOW_ADMIN_DETAILS",
    "auth.admin.show",
    os.environ.get("SHOW_ADMIN_DETAILS", "true").lower() == "true",
)

ADMIN_EMAIL = PersistentConfig(
    "ADMIN_EMAIL",
    "auth.admin.email",
    os.environ.get("ADMIN_EMAIL", None),
)


####################################
# TASKS
####################################


TASK_MODEL = PersistentConfig(
    "TASK_MODEL",
    "task.model.default",
    os.environ.get("TASK_MODEL", ""),
)

# TASK_MODEL_EXTERNAL is now per-admin - auto-set to Gemini 2.5 Flash Lite if user has access
TASK_MODEL_EXTERNAL = UserScopedConfig(
    "task.model.external",
    os.environ.get("TASK_MODEL_EXTERNAL", ""),
)

TITLE_GENERATION_PROMPT_TEMPLATE = PersistentConfig(
    "TITLE_GENERATION_PROMPT_TEMPLATE",
    "task.title.prompt_template",
    os.environ.get("TITLE_GENERATION_PROMPT_TEMPLATE", ""),
)

DEFAULT_TITLE_GENERATION_PROMPT_TEMPLATE = """### Task:
Generate a concise, 3-5 word title with an emoji summarizing the chat history.
### Guidelines:
- The title should clearly represent the main theme or subject of the conversation.
- Use emojis that enhance understanding of the topic, but avoid quotation marks or special formatting.
- Write the title in the chat's primary language; default to English if multilingual.
- Prioritize accuracy over excessive creativity; keep it clear and simple.
### Output:
JSON format: { "title": "your concise title here" }
### Examples:
- { "title": "📉 Stock Market Trends" },
- { "title": "🍪 Perfect Chocolate Chip Recipe" },
- { "title": "Evolution of Music Streaming" },
- { "title": "Remote Work Productivity Tips" },
- { "title": "Artificial Intelligence in Healthcare" },
- { "title": "🎮 Video Game Development Insights" }
### Chat History:
<chat_history>
{{MESSAGES:END:2}}
</chat_history>"""

TAGS_GENERATION_PROMPT_TEMPLATE = PersistentConfig(
    "TAGS_GENERATION_PROMPT_TEMPLATE",
    "task.tags.prompt_template",
    os.environ.get("TAGS_GENERATION_PROMPT_TEMPLATE", ""),
)

DEFAULT_TAGS_GENERATION_PROMPT_TEMPLATE = """### Task:
Generate 1-3 broad tags categorizing the main themes of the chat history, along with 1-3 more specific subtopic tags.

### Guidelines:
- Start with high-level domains (e.g. Science, Technology, Philosophy, Arts, Politics, Business, Health, Sports, Entertainment, Education)
- Consider including relevant subfields/subdomains if they are strongly represented throughout the conversation
- If content is too short (less than 3 messages) or too diverse, use only ["General"]
- Use the chat's primary language; default to English if multilingual
- Prioritize accuracy over specificity

### Output:
JSON format: { "tags": ["tag1", "tag2", "tag3"] }

### Chat History:
<chat_history>
{{MESSAGES:END:6}}
</chat_history>"""

IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE = PersistentConfig(
    "IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE",
    "task.image.prompt_template",
    os.environ.get("IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE", ""),
)

DEFAULT_IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE = """### Task:
Generate a detailed prompt for am image generation task based on the given language and context. Describe the image as if you were explaining it to someone who cannot see it. Include relevant details, colors, shapes, and any other important elements.

### Guidelines:
- Be descriptive and detailed, focusing on the most important aspects of the image.
- Avoid making assumptions or adding information not present in the image.
- Use the chat's primary language; default to English if multilingual.
- If the image is too complex, focus on the most prominent elements.

### Output:
Strictly return in JSON format:
{
    "prompt": "Your detailed description here."
}

### Chat History:
<chat_history>
{{MESSAGES:END:6}}
</chat_history>"""

# Task feature flags are now per-admin, default to False (disabled)
ENABLE_TAGS_GENERATION = UserScopedConfig(
    "task.tags.enable",
    os.environ.get("ENABLE_TAGS_GENERATION", "False").lower() == "true",
)

ENABLE_TITLE_GENERATION = UserScopedConfig(
    "task.title.enable",
    os.environ.get("ENABLE_TITLE_GENERATION", "False").lower() == "true",
)

ENABLE_SEARCH_QUERY_GENERATION = UserScopedConfig(
    "task.query.search.enable",
    os.environ.get("ENABLE_SEARCH_QUERY_GENERATION", "False").lower() == "true",
)

ENABLE_RETRIEVAL_QUERY_GENERATION = UserScopedConfig(
    "task.query.retrieval.enable",
    os.environ.get("ENABLE_RETRIEVAL_QUERY_GENERATION", "False").lower() == "true",
)


QUERY_GENERATION_PROMPT_TEMPLATE = PersistentConfig(
    "QUERY_GENERATION_PROMPT_TEMPLATE",
    "task.query.prompt_template",
    os.environ.get("QUERY_GENERATION_PROMPT_TEMPLATE", ""),
)

DEFAULT_QUERY_GENERATION_PROMPT_TEMPLATE = """### Task:
Analyze the chat history to determine the necessity of generating search queries, in the given language. By default, **prioritize generating 1-3 broad and relevant search queries** unless it is absolutely certain that no additional information is required. The aim is to retrieve comprehensive, updated, and valuable information even with minimal uncertainty. If no search is unequivocally needed, return an empty list.

### Guidelines:
- Respond **EXCLUSIVELY** with a JSON object. Any form of extra commentary, explanation, or additional text is strictly prohibited.
- When generating search queries, respond in the format: { "queries": ["query1", "query2"] }, ensuring each query is distinct, concise, and relevant to the topic.
- If and only if it is entirely certain that no useful results can be retrieved by a search, return: { "queries": [] }.
- Err on the side of suggesting search queries if there is **any chance** they might provide useful or updated information.
- Be concise and focused on composing high-quality search queries, avoiding unnecessary elaboration, commentary, or assumptions.
- Today's date is: {{CURRENT_DATE}}.
- Always prioritize providing actionable and broad queries that maximize informational coverage.

### Output:
Strictly return in JSON format: 
{
  "queries": ["query1", "query2"]
}

### Chat History:
<chat_history>
{{MESSAGES:END:6}}
</chat_history>
"""

# Autocomplete generation is now per-admin, default to False (disabled)
ENABLE_AUTOCOMPLETE_GENERATION = UserScopedConfig(
    "task.autocomplete.enable",
    os.environ.get("ENABLE_AUTOCOMPLETE_GENERATION", "False").lower() == "true",
)

AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH = PersistentConfig(
    "AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH",
    "task.autocomplete.input_max_length",
    int(os.environ.get("AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH", "-1")),
)

AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE = PersistentConfig(
    "AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE",
    "task.autocomplete.prompt_template",
    os.environ.get("AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE", ""),
)


DEFAULT_AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE = """### Task:
You are an autocompletion system. Continue the text in `<text>` based on the **completion type** in `<type>` and the given language.  

### **Instructions**:
1. Analyze `<text>` for context and meaning.  
2. Use `<type>` to guide your output:  
   - **General**: Provide a natural, concise continuation.  
   - **Search Query**: Complete as if generating a realistic search query.  
3. Start as if you are directly continuing `<text>`. Do **not** repeat, paraphrase, or respond as a model. Simply complete the text.  
4. Ensure the continuation:
   - Flows naturally from `<text>`.  
   - Avoids repetition, overexplaining, or unrelated ideas.  
5. If unsure, return: `{ "text": "" }`.  

### **Output Rules**:
- Respond only in JSON format: `{ "text": "<your_completion>" }`.

### **Examples**:
#### Example 1:  
Input:  
<type>General</type>  
<text>The sun was setting over the horizon, painting the sky</text>  
Output:  
{ "text": "with vibrant shades of orange and pink." }

#### Example 2:  
Input:  
<type>Search Query</type>  
<text>Top-rated restaurants in</text>  
Output:  
{ "text": "New York City for Italian cuisine." }  

---
### Context:
<chat_history>
{{MESSAGES:END:6}}
</chat_history>
<type>{{TYPE}}</type>  
<text>{{PROMPT}}</text>  
#### Output:
"""

TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE = PersistentConfig(
    "TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE",
    "task.tools.prompt_template",
    os.environ.get("TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE", ""),
)


DEFAULT_TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE = """Available Tools: {{TOOLS}}

Your task is to choose and return the correct tool(s) from the list of available tools based on the query. Follow these guidelines:

- Return only the JSON object, without any additional text or explanation.

- If no tools match the query, return an empty array: 
   {
     "tool_calls": []
   }

- If one or more tools match the query, construct a JSON response containing a "tool_calls" array with objects that include:
   - "name": The tool's name.
   - "parameters": A dictionary of required parameters and their corresponding values.

The format for the JSON response is strictly:
{
  "tool_calls": [
    {"name": "toolName1", "parameters": {"key1": "value1"}},
    {"name": "toolName2", "parameters": {"key2": "value2"}}
  ]
}"""


DEFAULT_EMOJI_GENERATION_PROMPT_TEMPLATE = """Your task is to reflect the speaker's likely facial expression through a fitting emoji. Interpret emotions from the message and reflect their facial expression using fitting, diverse emojis (e.g., 😊, 😢, 😡, 😱).

Message: ```{{prompt}}```"""

DEFAULT_MOA_GENERATION_PROMPT_TEMPLATE = """You have been provided with a set of responses from various models to the latest user query: "{{prompt}}"

Your task is to synthesize these responses into a single, high-quality response. It is crucial to critically evaluate the information provided in these responses, recognizing that some of it may be biased or incorrect. Your response should not simply replicate the given answers but should offer a refined, accurate, and comprehensive reply to the instruction. Ensure your response is well-structured, coherent, and adheres to the highest standards of accuracy and reliability.

Responses from models: {{responses}}"""


####################################
# Code Interpreter
####################################


CODE_EXECUTION_ENGINE = PersistentConfig(
    "CODE_EXECUTION_ENGINE",
    "code_execution.engine",
    os.environ.get("CODE_EXECUTION_ENGINE", "pyodide"),
)

CODE_EXECUTION_JUPYTER_URL = PersistentConfig(
    "CODE_EXECUTION_JUPYTER_URL",
    "code_execution.jupyter.url",
    os.environ.get("CODE_EXECUTION_JUPYTER_URL", ""),
)

CODE_EXECUTION_JUPYTER_AUTH = PersistentConfig(
    "CODE_EXECUTION_JUPYTER_AUTH",
    "code_execution.jupyter.auth",
    os.environ.get("CODE_EXECUTION_JUPYTER_AUTH", ""),
)

CODE_EXECUTION_JUPYTER_AUTH_TOKEN = PersistentConfig(
    "CODE_EXECUTION_JUPYTER_AUTH_TOKEN",
    "code_execution.jupyter.auth_token",
    os.environ.get("CODE_EXECUTION_JUPYTER_AUTH_TOKEN", ""),
)


CODE_EXECUTION_JUPYTER_AUTH_PASSWORD = PersistentConfig(
    "CODE_EXECUTION_JUPYTER_AUTH_PASSWORD",
    "code_execution.jupyter.auth_password",
    os.environ.get("CODE_EXECUTION_JUPYTER_AUTH_PASSWORD", ""),
)

CODE_EXECUTION_JUPYTER_TIMEOUT = PersistentConfig(
    "CODE_EXECUTION_JUPYTER_TIMEOUT",
    "code_execution.jupyter.timeout",
    int(os.environ.get("CODE_EXECUTION_JUPYTER_TIMEOUT", "60")),
)

ENABLE_CODE_INTERPRETER = PersistentConfig(
    "ENABLE_CODE_INTERPRETER",
    "code_interpreter.enable",
    os.environ.get("ENABLE_CODE_INTERPRETER", "True").lower() == "true",
)

CODE_INTERPRETER_ENGINE = PersistentConfig(
    "CODE_INTERPRETER_ENGINE",
    "code_interpreter.engine",
    os.environ.get("CODE_INTERPRETER_ENGINE", "pyodide"),
)

CODE_INTERPRETER_PROMPT_TEMPLATE = PersistentConfig(
    "CODE_INTERPRETER_PROMPT_TEMPLATE",
    "code_interpreter.prompt_template",
    os.environ.get("CODE_INTERPRETER_PROMPT_TEMPLATE", ""),
)

CODE_INTERPRETER_JUPYTER_URL = PersistentConfig(
    "CODE_INTERPRETER_JUPYTER_URL",
    "code_interpreter.jupyter.url",
    os.environ.get(
        "CODE_INTERPRETER_JUPYTER_URL", os.environ.get("CODE_EXECUTION_JUPYTER_URL", "")
    ),
)

CODE_INTERPRETER_JUPYTER_AUTH = PersistentConfig(
    "CODE_INTERPRETER_JUPYTER_AUTH",
    "code_interpreter.jupyter.auth",
    os.environ.get(
        "CODE_INTERPRETER_JUPYTER_AUTH",
        os.environ.get("CODE_EXECUTION_JUPYTER_AUTH", ""),
    ),
)

CODE_INTERPRETER_JUPYTER_AUTH_TOKEN = PersistentConfig(
    "CODE_INTERPRETER_JUPYTER_AUTH_TOKEN",
    "code_interpreter.jupyter.auth_token",
    os.environ.get(
        "CODE_INTERPRETER_JUPYTER_AUTH_TOKEN",
        os.environ.get("CODE_EXECUTION_JUPYTER_AUTH_TOKEN", ""),
    ),
)


CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD = PersistentConfig(
    "CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD",
    "code_interpreter.jupyter.auth_password",
    os.environ.get(
        "CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD",
        os.environ.get("CODE_EXECUTION_JUPYTER_AUTH_PASSWORD", ""),
    ),
)

CODE_INTERPRETER_JUPYTER_TIMEOUT = PersistentConfig(
    "CODE_INTERPRETER_JUPYTER_TIMEOUT",
    "code_interpreter.jupyter.timeout",
    int(
        os.environ.get(
            "CODE_INTERPRETER_JUPYTER_TIMEOUT",
            os.environ.get("CODE_EXECUTION_JUPYTER_TIMEOUT", "60"),
        )
    ),
)


DEFAULT_CODE_INTERPRETER_PROMPT = """
#### Tools Available

1. **Code Interpreter**: `<code_interpreter type="code" lang="python"></code_interpreter>`
   - You have access to a Python shell that runs directly in the user's browser, enabling fast execution of code for analysis, calculations, or problem-solving.  Use it in this response.
   - The Python code you write can incorporate a wide array of libraries, handle data manipulation or visualization, perform API calls for web-related tasks, or tackle virtually any computational challenge. Use this flexibility to **think outside the box, craft elegant solutions, and harness Python's full potential**.
   - To use it, **you must enclose your code within `<code_interpreter type="code" lang="python">` XML tags** and stop right away. If you don't, the code won't execute. Do NOT use triple backticks.
   - When coding, **always aim to print meaningful outputs** (e.g., results, tables, summaries, or visuals) to better interpret and verify the findings. Avoid relying on implicit outputs; prioritize explicit and clear print statements so the results are effectively communicated to the user.  
   - After obtaining the printed output, **always provide a concise analysis, interpretation, or next steps to help the user understand the findings or refine the outcome further.**  
   - If the results are unclear, unexpected, or require validation, refine the code and execute it again as needed. Always aim to deliver meaningful insights from the results, iterating if necessary.  
   - **If a link to an image, audio, or any file is provided in markdown format in the output, ALWAYS regurgitate word for word, explicitly display it as part of the response to ensure the user can access it easily, do NOT change the link.**
   - All responses should be communicated in the chat's primary language, ensuring seamless understanding. If the chat is multilingual, default to English for clarity.

Ensure that the tools are effectively utilized to achieve the highest-quality analysis for the user."""


####################################
# Vector Database
####################################

VECTOR_DB = os.environ.get("VECTOR_DB", "chroma")

# Chroma
CHROMA_DATA_PATH = f"{DATA_DIR}/vector_db"

if VECTOR_DB == "chroma":
    import chromadb
    
    CHROMA_TENANT = os.environ.get("CHROMA_TENANT", chromadb.DEFAULT_TENANT)
    CHROMA_DATABASE = os.environ.get("CHROMA_DATABASE", chromadb.DEFAULT_DATABASE)
    CHROMA_HTTP_HOST = os.environ.get("CHROMA_HTTP_HOST", "")
    CHROMA_HTTP_PORT = int(os.environ.get("CHROMA_HTTP_PORT", "8000"))
    CHROMA_CLIENT_AUTH_PROVIDER = os.environ.get("CHROMA_CLIENT_AUTH_PROVIDER", "")
    CHROMA_CLIENT_AUTH_CREDENTIALS = os.environ.get(
        "CHROMA_CLIENT_AUTH_CREDENTIALS", ""
    )
    # Comma-separated list of header=value pairs
    CHROMA_HTTP_HEADERS = os.environ.get("CHROMA_HTTP_HEADERS", "")
    if CHROMA_HTTP_HEADERS:
        CHROMA_HTTP_HEADERS = dict(
            [pair.split("=") for pair in CHROMA_HTTP_HEADERS.split(",")]
        )
    else:
        CHROMA_HTTP_HEADERS = None
    CHROMA_HTTP_SSL = os.environ.get("CHROMA_HTTP_SSL", "false").lower() == "true"
# this uses the model defined in the Dockerfile ENV variable. If you dont use docker or docker based deployments such as k8s, the default embedding model will be used (sentence-transformers/all-MiniLM-L6-v2)

# Milvus

MILVUS_URI = os.environ.get("MILVUS_URI", f"{DATA_DIR}/vector_db/milvus.db")
MILVUS_DB = os.environ.get("MILVUS_DB", "default")
MILVUS_TOKEN = os.environ.get("MILVUS_TOKEN", None)

# Qdrant
QDRANT_URI = os.environ.get("QDRANT_URI", None)
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", None)

# OpenSearch
OPENSEARCH_URI = os.environ.get("OPENSEARCH_URI", "https://localhost:9200")
OPENSEARCH_SSL = os.environ.get("OPENSEARCH_SSL", True)
OPENSEARCH_CERT_VERIFY = os.environ.get("OPENSEARCH_CERT_VERIFY", False)
OPENSEARCH_USERNAME = os.environ.get("OPENSEARCH_USERNAME", None)
OPENSEARCH_PASSWORD = os.environ.get("OPENSEARCH_PASSWORD", None)

# Pgvector
PGVECTOR_DB_URL = os.environ.get("PGVECTOR_DB_URL", DATABASE_URL)
if VECTOR_DB == "pgvector" and not PGVECTOR_DB_URL.startswith("postgres"):
    raise ValueError(
        "Pgvector requires setting PGVECTOR_DB_URL or using Postgres with vector extension as the primary database."
    )
PGVECTOR_INITIALIZE_MAX_VECTOR_LENGTH = int(
    os.environ.get("PGVECTOR_INITIALIZE_MAX_VECTOR_LENGTH", "1536")
)

####################################
# Information Retrieval (RAG)
####################################


# If configured, Google Drive will be available as an upload option.
ENABLE_GOOGLE_DRIVE_INTEGRATION = PersistentConfig(
    "ENABLE_GOOGLE_DRIVE_INTEGRATION",
    "google_drive.enable",
    os.getenv("ENABLE_GOOGLE_DRIVE_INTEGRATION", "False").lower() == "true",
)

GOOGLE_DRIVE_CLIENT_ID = PersistentConfig(
    "GOOGLE_DRIVE_CLIENT_ID",
    "google_drive.client_id",
    os.environ.get("GOOGLE_DRIVE_CLIENT_ID", ""),
)

GOOGLE_DRIVE_API_KEY = PersistentConfig(
    "GOOGLE_DRIVE_API_KEY",
    "google_drive.api_key",
    os.environ.get("GOOGLE_DRIVE_API_KEY", ""),
)

ENABLE_ONEDRIVE_INTEGRATION = PersistentConfig(
    "ENABLE_ONEDRIVE_INTEGRATION",
    "onedrive.enable",
    os.getenv("ENABLE_ONEDRIVE_INTEGRATION", "False").lower() == "true",
)

ONEDRIVE_CLIENT_ID = PersistentConfig(
    "ONEDRIVE_CLIENT_ID",
    "onedrive.client_id",
    os.environ.get("ONEDRIVE_CLIENT_ID", ""),
)

# RAG Content Extraction
CONTENT_EXTRACTION_ENGINE = PersistentConfig(
    "CONTENT_EXTRACTION_ENGINE",
    "rag.CONTENT_EXTRACTION_ENGINE",
    os.environ.get("CONTENT_EXTRACTION_ENGINE", "").lower(),
)

TIKA_SERVER_URL = PersistentConfig(
    "TIKA_SERVER_URL",
    "rag.tika_server_url",
    os.getenv("TIKA_SERVER_URL", "http://tika:9998"),  # Default for sidecar deployment
)

DOCUMENT_INTELLIGENCE_ENDPOINT = PersistentConfig(
    "DOCUMENT_INTELLIGENCE_ENDPOINT",
    "rag.document_intelligence_endpoint",
    os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT", ""),
)

DOCUMENT_INTELLIGENCE_KEY = PersistentConfig(
    "DOCUMENT_INTELLIGENCE_KEY",
    "rag.document_intelligence_key",
    os.getenv("DOCUMENT_INTELLIGENCE_KEY", ""),
)


BYPASS_EMBEDDING_AND_RETRIEVAL = PersistentConfig(
    "BYPASS_EMBEDDING_AND_RETRIEVAL",
    "rag.bypass_embedding_and_retrieval",
    os.environ.get("BYPASS_EMBEDDING_AND_RETRIEVAL", "False").lower() == "true",
)
RAG_TOP_K = UserScopedConfig( "rag.top_k", int(os.environ.get("RAG_TOP_K", "10")))

# RAG_TOP_K = PersistentConfig(
#     "RAG_TOP_K", "rag.top_k", int(os.environ.get("RAG_TOP_K", "3"))
#)
RAG_RELEVANCE_THRESHOLD = PersistentConfig(
    "RAG_RELEVANCE_THRESHOLD",
    "rag.relevance_threshold",
    float(os.environ.get("RAG_RELEVANCE_THRESHOLD", "1")),
)

ENABLE_RAG_HYBRID_SEARCH = UserScopedConfig("rag.enable_hybrid_search",os.environ.get("ENABLE_RAG_HYBRID_SEARCH", "").lower() == "true" )
#     "ENABLE_RAG_HYBRID_SEARCH",
#     "rag.enable_hybrid_search",
#     os.environ.get("ENABLE_RAG_HYBRID_SEARCH", "").lower() == "true",
# )

# RAG_FULL_CONTEXT = PersistentConfig(
#     "RAG_FULL_CONTEXT",
#     "rag.full_context",
#     os.getenv("RAG_FULL_CONTEXT", "False").lower() == "true",
# )

RAG_FULL_CONTEXT = UserScopedConfig(
    "rag.full_context",
    os.getenv("RAG_FULL_CONTEXT", "False").lower() == "true")

RAG_FILE_MAX_COUNT = PersistentConfig(
    "RAG_FILE_MAX_COUNT",
    "rag.file.max_count",
    (
        int(os.environ.get("RAG_FILE_MAX_COUNT"))
        if os.environ.get("RAG_FILE_MAX_COUNT")
        else None
    ),
)

RAG_FILE_MAX_SIZE = PersistentConfig(
    "RAG_FILE_MAX_SIZE",
    "rag.file.max_size",
    (
        int(os.environ.get("RAG_FILE_MAX_SIZE"))
        if os.environ.get("RAG_FILE_MAX_SIZE")
        else None
    ),
)

ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION = PersistentConfig(
    "ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION",
    "rag.enable_web_loader_ssl_verification",
    os.environ.get("ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION", "True").lower() == "true",
)

RAG_EMBEDDING_ENGINE = PersistentConfig(
    "RAG_EMBEDDING_ENGINE",
    "rag.embedding_engine",
    os.environ.get("RAG_EMBEDDING_ENGINE", "portkey"),
)

# PDF_EXTRACT_IMAGES: Extract images from PDFs during processing
# WARNING: Setting this to True can cause significant slowdowns (2+ minutes) or hangs
# on PDFs with many images. PyPDFLoader's image extraction is CPU-intensive and can deadlock.
# Default: False (disabled) - only extract text content
PDF_EXTRACT_IMAGES = PersistentConfig(
    "PDF_EXTRACT_IMAGES",
    "rag.pdf_extract_images",
    os.environ.get("PDF_EXTRACT_IMAGES", "False").lower() == "true",
)

# DEPRECATED: Legacy global embedding model - NOT USED for RAG operations
# We only use Portkey for embeddings, and each admin has their own model name (see RAG_EMBEDDING_MODEL_USER below)
RAG_EMBEDDING_MODEL = PersistentConfig(
    "RAG_EMBEDDING_MODEL",
    "rag.embedding_model",
    # No hardcoded default model; must be configured explicitly by an admin.
    os.environ.get("RAG_EMBEDDING_MODEL", ""),
)
log.info(f"Embedding model set: {RAG_EMBEDDING_MODEL.value!r}")

# Per-admin embedding model name (RBAC-scoped)
# Each admin sets their own model name that applies to them and their user group
# No hardcoded default - admins must configure their own model name
# This is used for all RAG operations (file embeddings, query embeddings)
RAG_EMBEDDING_MODEL_USER = UserScopedConfig(
    "rag.embedding_model_user",
    os.getenv("RAG_EMBEDDING_MODEL_USER", ""),  # Empty default - must be configured by admin
)

RAG_EMBEDDING_MODEL_AUTO_UPDATE = (
    not OFFLINE_MODE
    and os.environ.get("RAG_EMBEDDING_MODEL_AUTO_UPDATE", "True").lower() == "true"
)

RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE = (
    os.environ.get("RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE", "True").lower() == "true"
)

RAG_EMBEDDING_BATCH_SIZE = PersistentConfig(
    "RAG_EMBEDDING_BATCH_SIZE",
    "rag.embedding_batch_size",
    int(
        os.environ.get("RAG_EMBEDDING_BATCH_SIZE")
        or os.environ.get("RAG_EMBEDDING_OPENAI_BATCH_SIZE", "1")
    ),
)

# Portkey virtual key - user-specific, inherits from group admin if user is member
# For admins: uses their own virtual key from config
# For group members: inherits virtual key from their group's admin
# Default: from RAG_EMBEDDING_MODEL if it's a virtual key (doesn't start with "@")
# NOTE: RAG_EMBEDDING_PORTKEY_VIRTUAL_KEY has been removed (deprecated)
# Portkey no longer uses virtual_key - only api_key is needed

RAG_RERANKING_MODEL = PersistentConfig(
    "RAG_RERANKING_MODEL",
    "rag.reranking_model",
    os.environ.get("RAG_RERANKING_MODEL", ""),
)

if RAG_RERANKING_MODEL.value != "":
    log.info(f"Reranking model set: {RAG_RERANKING_MODEL.value}")

RAG_RERANKING_MODEL_AUTO_UPDATE = (
    not OFFLINE_MODE
    and os.environ.get("RAG_RERANKING_MODEL_AUTO_UPDATE", "True").lower() == "true"
)

RAG_RERANKING_MODEL_TRUST_REMOTE_CODE = (
    os.environ.get("RAG_RERANKING_MODEL_TRUST_REMOTE_CODE", "True").lower() == "true"
)


RAG_TEXT_SPLITTER = PersistentConfig(
    "RAG_TEXT_SPLITTER",
    "rag.text_splitter",
    os.environ.get("RAG_TEXT_SPLITTER", ""),
)


TIKTOKEN_CACHE_DIR = os.environ.get("TIKTOKEN_CACHE_DIR", f"{CACHE_DIR}/tiktoken")
TIKTOKEN_ENCODING_NAME = PersistentConfig(
    "TIKTOKEN_ENCODING_NAME",
    "rag.tiktoken_encoding_name",
    os.environ.get("TIKTOKEN_ENCODING_NAME", "cl100k_base"),
)

CHUNK_SIZE = UserScopedConfig("rag.chunk_size", int(os.environ.get("CHUNK_SIZE", "1000")))
# CHUNK_SIZE = PersistentConfig(
#     "CHUNK_SIZE", "rag.chunk_size", int(os.environ.get("CHUNK_SIZE", "1000"))
# )

CHUNK_OVERLAP = UserScopedConfig(
    "rag.chunk_overlap",
    int(os.environ.get("CHUNK_OVERLAP", "200")),
)

# CHUNK_OVERLAP = PersistentConfig(
#     "CHUNK_OVERLAP",
#     "rag.chunk_overlap",
#     int(os.environ.get("CHUNK_OVERLAP", "100")),
# )


DEFAULT_RAG_TEMPLATE = """### Task:
Respond to the user query using the provided context, incorporating inline citations in the format [source_id] **only when the <source_id> tag is explicitly provided** in the context.

### Guidelines:
- If you don't know the answer, clearly state that.
- If uncertain, ask the user for clarification.
- Respond in the same language as the user's query.
- If the context is unreadable or of poor quality, inform the user and provide the best possible answer.
- If the answer isn't present in the context but you possess the knowledge, explain this to the user and provide the answer using your own understanding.
- **Only include inline citations using [source_id] (e.g., [1], [2]) when a `<source_id>` tag is explicitly provided in the context.**
- Do not cite if the <source_id> tag is not provided in the context.  
- Do not use XML tags in your response.
- Ensure citations are concise and directly related to the information provided.

### Example of Citation:
If the user asks about a specific topic and the information is found in "whitepaper.pdf" with a provided <source_id>, the response should include the citation like so:  
* "According to the study, the proposed method increases efficiency by 20% [whitepaper.pdf]."
If no <source_id> is present, the response should omit the citation.

### Output:
Provide a clear and direct response to the user's query, including inline citations in the format [source_id] only when the <source_id> tag is present in the context.

<context>
{{CONTEXT}}
</context>

<user_query>
{{QUERY}}
</user_query>
"""

# RAG_TEMPLATE = PersistentConfig(
#     "RAG_TEMPLATE",
#     "rag.template",
#     os.environ.get("RAG_TEMPLATE", DEFAULT_RAG_TEMPLATE),
# )

RAG_TEMPLATE = UserScopedConfig("rag.template", DEFAULT_RAG_TEMPLATE)

RAG_OPENAI_API_BASE_URL = PersistentConfig(
    "RAG_OPENAI_API_BASE_URL",
    "rag.openai_api_base_url",
    os.getenv("RAG_OPENAI_API_BASE_URL", "https://ai-gateway.apps.cloud.rt.nyu.edu/v1"),
)
# Per-admin embedding API key
# Each admin sets their own key that applies to them and their user group
# No hardcoded default - admins must configure their own key
RAG_OPENAI_API_KEY = UserScopedConfig(
    "rag.openai_api_key",
    os.getenv("RAG_OPENAI_API_KEY", ""),  # Empty default - must be configured by admin
)

RAG_OLLAMA_BASE_URL = PersistentConfig(
    "RAG_OLLAMA_BASE_URL",
    "rag.ollama.url",
    os.getenv("RAG_OLLAMA_BASE_URL", OLLAMA_BASE_URL),
)

RAG_OLLAMA_API_KEY = PersistentConfig(
    "RAG_OLLAMA_API_KEY",
    "rag.ollama.key",
    os.getenv("RAG_OLLAMA_API_KEY", ""),
)


ENABLE_RAG_LOCAL_WEB_FETCH = (
    os.getenv("ENABLE_RAG_LOCAL_WEB_FETCH", "False").lower() == "true"
)

YOUTUBE_LOADER_LANGUAGE = PersistentConfig(
    "YOUTUBE_LOADER_LANGUAGE",
    "rag.youtube_loader_language",
    os.getenv("YOUTUBE_LOADER_LANGUAGE", "en").split(","),
)

YOUTUBE_LOADER_PROXY_URL = PersistentConfig(
    "YOUTUBE_LOADER_PROXY_URL",
    "rag.youtube_loader_proxy_url",
    os.getenv("YOUTUBE_LOADER_PROXY_URL", ""),
)


# ENABLE_RAG_WEB_SEARCH = PersistentConfig(
#     "ENABLE_RAG_WEB_SEARCH",
#     "rag.web.search.enable",
#     os.getenv("ENABLE_RAG_WEB_SEARCH", "False").lower() == "true",
# )

ENABLE_RAG_WEB_SEARCH = UserScopedConfig(
    "rag.web.search.enable",
    os.getenv("ENABLE_RAG_WEB_SEARCH", "False").lower() == "true",
)

# RAG_WEB_SEARCH_ENGINE = PersistentConfig(
#     "RAG_WEB_SEARCH_ENGINE",
#     "rag.web.search.engine",
#     os.getenv("RAG_WEB_SEARCH_ENGINE", ""),
# )

RAG_WEB_SEARCH_ENGINE = UserScopedConfig(
    "rag.web.search.engine",
    os.getenv("RAG_WEB_SEARCH_ENGINE", ""),
)

# Facilities feature flag
ENABLE_FACILITIES = UserScopedConfig(
    "facilities.enable",
    os.getenv("ENABLE_FACILITIES", "True").lower() == "true",
)

# BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL = PersistentConfig(
#     "BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL",
#     "rag.web.search.bypass_embedding_and_retrieval",
#     os.getenv("BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL", "False").lower() == "true",
# )

BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL = UserScopedConfig(
    "rag.web.search.bypass_embedding_and_retrieval",
    os.getenv("BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL", "False").lower() == "true",
)

# You can provide a list of your own websites to filter after performing a web search.
# This ensures the highest level of safety and reliability of the information sources.
# Each user has their own private domain filter list.
RAG_WEB_SEARCH_DOMAIN_FILTER_LIST = UserScopedConfig(
    "rag.web.search.domain.filter_list",
    [],
)

# Website blocklist - URLs that should be blocked even if they're from allowed domains
RAG_WEB_SEARCH_WEBSITE_BLOCKLIST = UserScopedConfig(
    "rag.web.search.website.blocklist",
    [],
)

# Internal facilities specific sites for NYU HPC searches
RAG_WEB_SEARCH_INTERNAL_FACILITIES_SITES = UserScopedConfig(
    "rag.web.search.internal.facilities.sites",
    [
        "https://sites.google.com/nyu.edu/nyu-hpc/",
        "https://www.nyu.edu/life/information-technology/research-computing-services/high-performance-computing.html",
        "https://www.nyu.edu/life/information-technology/research-computing-services/high-performance-computing/high-performance-computing-nyu-it.html"
    ],
)


# SEARXNG_QUERY_URL = PersistentConfig(
#     "SEARXNG_QUERY_URL",
#     "rag.web.search.searxng_query_url",
#     os.getenv("SEARXNG_QUERY_URL", ""),
# )

SEARXNG_QUERY_URL = UserScopedConfig(
    "rag.web.search.searxng_query_url",
    os.getenv("SEARXNG_QUERY_URL", ""),
)

# GOOGLE_PSE_API_KEY = PersistentConfig(
#     "GOOGLE_PSE_API_KEY",
#     "rag.web.search.google_pse_api_key",
#     os.getenv("GOOGLE_PSE_API_KEY", ""),
# )

GOOGLE_PSE_API_KEY = UserScopedConfig(
    "rag.web.search.google_pse_api_key",
    os.getenv("GOOGLE_PSE_API_KEY", ""),
)

# GOOGLE_PSE_ENGINE_ID = PersistentConfig(
#     "GOOGLE_PSE_ENGINE_ID",
#     "rag.web.search.google_pse_engine_id",
#     os.getenv("GOOGLE_PSE_ENGINE_ID", ""),
# )

GOOGLE_PSE_ENGINE_ID = UserScopedConfig(
    "rag.web.search.google_pse_engine_id",
    os.getenv("GOOGLE_PSE_ENGINE_ID", ""),
)

# BRAVE_SEARCH_API_KEY = PersistentConfig(
#     "BRAVE_SEARCH_API_KEY",
#     "rag.web.search.brave_search_api_key",
#     os.getenv("BRAVE_SEARCH_API_KEY", ""),
# )

BRAVE_SEARCH_API_KEY = UserScopedConfig(
    "rag.web.search.brave_search_api_key",
    os.getenv("BRAVE_SEARCH_API_KEY", ""),
)

# KAGI_SEARCH_API_KEY = PersistentConfig(
#     "KAGI_SEARCH_API_KEY",
#     "rag.web.search.kagi_search_api_key",
#     os.getenv("KAGI_SEARCH_API_KEY", ""),
# )

KAGI_SEARCH_API_KEY = UserScopedConfig(
    "rag.web.search.kagi_search_api_key",
    os.getenv("KAGI_SEARCH_API_KEY", ""),
)

# MOJEEK_SEARCH_API_KEY = PersistentConfig(
#     "MOJEEK_SEARCH_API_KEY",
#     "rag.web.search.mojeek_search_api_key",
#     os.getenv("MOJEEK_SEARCH_API_KEY", ""),
# )

MOJEEK_SEARCH_API_KEY = UserScopedConfig(
    "rag.web.search.mojeek_search_api_key",
    os.getenv("MOJEEK_SEARCH_API_KEY", ""),
)

# BOCHA_SEARCH_API_KEY = PersistentConfig(
#     "BOCHA_SEARCH_API_KEY",
#     "rag.web.search.bocha_search_api_key",
#     os.getenv("BOCHA_SEARCH_API_KEY", ""),
# )

BOCHA_SEARCH_API_KEY = UserScopedConfig(
    "rag.web.search.bocha_search_api_key",
    os.getenv("BOCHA_SEARCH_API_KEY", ""),
)

# SERPSTACK_API_KEY = PersistentConfig(
#     "SERPSTACK_API_KEY",
#     "rag.web.search.serpstack_api_key",
#     os.getenv("SERPSTACK_API_KEY", ""),
# )

SERPSTACK_API_KEY = UserScopedConfig(
    "rag.web.search.serpstack_api_key",
    os.getenv("SERPSTACK_API_KEY", ""),
)


# SERPSTACK_HTTPS = PersistentConfig(
#     "SERPSTACK_HTTPS",
#     "rag.web.search.serpstack_https",
#     os.getenv("SERPSTACK_HTTPS", "True").lower() == "true",
# )

SERPSTACK_HTTPS = UserScopedConfig(
    "rag.web.search.serpstack_https",
    os.getenv("SERPSTACK_HTTPS", "True").lower() == "true",
)

# SERPER_API_KEY = PersistentConfig(
#     "SERPER_API_KEY",
#     "rag.web.search.serper_api_key",
#     os.getenv("SERPER_API_KEY", ""),
# )

SERPER_API_KEY = UserScopedConfig(
    "rag.web.search.serper_api_key",
    os.getenv("SERPER_API_KEY", ""),
)

# SERPLY_API_KEY = PersistentConfig(
#     "SERPLY_API_KEY",
#     "rag.web.search.serply_api_key",
#     os.getenv("SERPLY_API_KEY", ""),
# )

SERPLY_API_KEY = UserScopedConfig(
    "rag.web.search.serply_api_key",
    os.getenv("SERPLY_API_KEY", ""),
)

# TAVILY_API_KEY = PersistentConfig(
#     "TAVILY_API_KEY",
#     "rag.web.search.tavily_api_key",
#     os.getenv("TAVILY_API_KEY", ""),
# )

TAVILY_API_KEY = UserScopedConfig(
    "rag.web.search.tavily_api_key",
    os.getenv("TAVILY_API_KEY", ""),
)

# JINA_API_KEY = PersistentConfig(
#     "JINA_API_KEY",
#     "rag.web.search.jina_api_key",
#     os.getenv("JINA_API_KEY", ""),
# )

JINA_API_KEY = UserScopedConfig(
    "rag.web.search.jina_api_key",
    os.getenv("JINA_API_KEY", ""),
)

# SEARCHAPI_API_KEY = PersistentConfig(
#     "SEARCHAPI_API_KEY",
#     "rag.web.search.searchapi_api_key",
#     os.getenv("SEARCHAPI_API_KEY", ""),
# )

SEARCHAPI_API_KEY = UserScopedConfig(
    "rag.web.search.searchapi_api_key",
    os.getenv("SEARCHAPI_API_KEY", ""),
)

# SEARCHAPI_ENGINE = PersistentConfig(
#     "SEARCHAPI_ENGINE",
#     "rag.web.search.searchapi_engine",
#     os.getenv("SEARCHAPI_ENGINE", ""),
# )

SEARCHAPI_ENGINE = UserScopedConfig(
    "rag.web.search.searchapi_engine",
    os.getenv("SEARCHAPI_ENGINE", ""),
)

# SERPAPI_API_KEY = PersistentConfig(
#     "SERPAPI_API_KEY",
#     "rag.web.search.serpapi_api_key",
#     os.getenv("SERPAPI_API_KEY", ""),
# )

SERPAPI_API_KEY = UserScopedConfig(
    "rag.web.search.serpapi_api_key",
    os.getenv("SERPAPI_API_KEY", ""),
)

# SERPAPI_ENGINE = PersistentConfig(
#     "SERPAPI_ENGINE",
#     "rag.web.search.serpapi_engine",
#     os.getenv("SERPAPI_ENGINE", ""),
# )

SERPAPI_ENGINE = UserScopedConfig(
    "rag.web.search.serpapi_engine",
    os.getenv("SERPAPI_ENGINE", ""),
)

# BING_SEARCH_V7_ENDPOINT = PersistentConfig(
#     "BING_SEARCH_V7_ENDPOINT",
#     "rag.web.search.bing_search_v7_endpoint",
#     os.environ.get(
#         "BING_SEARCH_V7_ENDPOINT", "https://api.bing.microsoft.com/v7.0/search"
#     ),
# )

BING_SEARCH_V7_ENDPOINT = UserScopedConfig(
    "rag.web.search.bing_search_v7_endpoint",
    os.environ.get(
        "BING_SEARCH_V7_ENDPOINT", "https://api.bing.microsoft.com/v7.0/search"
    ),
)

# BING_SEARCH_V7_SUBSCRIPTION_KEY = PersistentConfig(
#     "BING_SEARCH_V7_SUBSCRIPTION_KEY",
#     "rag.web.search.bing_search_v7_subscription_key",
#     os.environ.get("BING_SEARCH_V7_SUBSCRIPTION_KEY", ""),
# )

BING_SEARCH_V7_SUBSCRIPTION_KEY = UserScopedConfig(
    "rag.web.search.bing_search_v7_subscription_key",
    os.environ.get("BING_SEARCH_V7_SUBSCRIPTION_KEY", ""),
)

# EXA_API_KEY = PersistentConfig(
#     "EXA_API_KEY",
#     "rag.web.search.exa_api_key",
#     os.getenv("EXA_API_KEY", ""),
# )

EXA_API_KEY = UserScopedConfig(
    "rag.web.search.exa_api_key",
    os.getenv("EXA_API_KEY", ""),
)

# RAG_WEB_SEARCH_RESULT_COUNT = PersistentConfig(
#     "RAG_WEB_SEARCH_RESULT_COUNT",
#     "rag.web.search.result_count",
#     int(os.getenv("RAG_WEB_SEARCH_RESULT_COUNT", "3")),
# )

RAG_WEB_SEARCH_RESULT_COUNT = UserScopedConfig(
    "rag.web.search.result_count",
    int(os.getenv("RAG_WEB_SEARCH_RESULT_COUNT", "3")),
)

# RAG_WEB_SEARCH_CONCURRENT_REQUESTS = PersistentConfig(
#     "RAG_WEB_SEARCH_CONCURRENT_REQUESTS",
#     "rag.web.search.concurrent_requests",
#     int(os.getenv("RAG_WEB_SEARCH_CONCURRENT_REQUESTS", "10")),
# )

RAG_WEB_SEARCH_CONCURRENT_REQUESTS = UserScopedConfig(
    "rag.web.search.concurrent_requests",
    int(os.getenv("RAG_WEB_SEARCH_CONCURRENT_REQUESTS", "10")),
)

RAG_WEB_LOADER_ENGINE = PersistentConfig(
    "RAG_WEB_LOADER_ENGINE",
    "rag.web.loader.engine",
    os.environ.get("RAG_WEB_LOADER_ENGINE", "safe_web"),
)


# RAG_WEB_SEARCH_TRUST_ENV = PersistentConfig(
#     "RAG_WEB_SEARCH_TRUST_ENV",
#     "rag.web.search.trust_env",
#     os.getenv("RAG_WEB_SEARCH_TRUST_ENV", "False").lower() == "true",
# )

RAG_WEB_SEARCH_TRUST_ENV = UserScopedConfig(
    "rag.web.search.trust_env",
    os.getenv("RAG_WEB_SEARCH_TRUST_ENV", "False").lower() == "true",
)

PLAYWRIGHT_WS_URI = PersistentConfig(
    "PLAYWRIGHT_WS_URI",
    "rag.web.loader.engine.playwright.ws.uri",
    os.environ.get("PLAYWRIGHT_WS_URI", None),
)

FIRECRAWL_API_KEY = PersistentConfig(
    "FIRECRAWL_API_KEY",
    "firecrawl.api_key",
    os.environ.get("FIRECRAWL_API_KEY", ""),
)

FIRECRAWL_API_BASE_URL = PersistentConfig(
    "FIRECRAWL_API_BASE_URL",
    "firecrawl.api_url",
    os.environ.get("FIRECRAWL_API_BASE_URL", "https://api.firecrawl.dev"),
)

####################################
# Images
####################################

IMAGE_GENERATION_ENGINE = PersistentConfig(
    "IMAGE_GENERATION_ENGINE",
    "image_generation.engine",
    os.getenv("IMAGE_GENERATION_ENGINE", "openai"),
)

ENABLE_IMAGE_GENERATION = PersistentConfig(
    "ENABLE_IMAGE_GENERATION",
    "image_generation.enable",
    os.environ.get("ENABLE_IMAGE_GENERATION", "").lower() == "true",
)

ENABLE_IMAGE_PROMPT_GENERATION = PersistentConfig(
    "ENABLE_IMAGE_PROMPT_GENERATION",
    "image_generation.prompt.enable",
    os.environ.get("ENABLE_IMAGE_PROMPT_GENERATION", "true").lower() == "true",
)

AUTOMATIC1111_BASE_URL = PersistentConfig(
    "AUTOMATIC1111_BASE_URL",
    "image_generation.automatic1111.base_url",
    os.getenv("AUTOMATIC1111_BASE_URL", ""),
)
AUTOMATIC1111_API_AUTH = PersistentConfig(
    "AUTOMATIC1111_API_AUTH",
    "image_generation.automatic1111.api_auth",
    os.getenv("AUTOMATIC1111_API_AUTH", ""),
)

AUTOMATIC1111_CFG_SCALE = PersistentConfig(
    "AUTOMATIC1111_CFG_SCALE",
    "image_generation.automatic1111.cfg_scale",
    (
        float(os.environ.get("AUTOMATIC1111_CFG_SCALE"))
        if os.environ.get("AUTOMATIC1111_CFG_SCALE")
        else None
    ),
)


AUTOMATIC1111_SAMPLER = PersistentConfig(
    "AUTOMATIC1111_SAMPLER",
    "image_generation.automatic1111.sampler",
    (
        os.environ.get("AUTOMATIC1111_SAMPLER")
        if os.environ.get("AUTOMATIC1111_SAMPLER")
        else None
    ),
)

AUTOMATIC1111_SCHEDULER = PersistentConfig(
    "AUTOMATIC1111_SCHEDULER",
    "image_generation.automatic1111.scheduler",
    (
        os.environ.get("AUTOMATIC1111_SCHEDULER")
        if os.environ.get("AUTOMATIC1111_SCHEDULER")
        else None
    ),
)

COMFYUI_BASE_URL = PersistentConfig(
    "COMFYUI_BASE_URL",
    "image_generation.comfyui.base_url",
    os.getenv("COMFYUI_BASE_URL", ""),
)

COMFYUI_API_KEY = PersistentConfig(
    "COMFYUI_API_KEY",
    "image_generation.comfyui.api_key",
    os.getenv("COMFYUI_API_KEY", ""),
)

COMFYUI_DEFAULT_WORKFLOW = """
{
  "3": {
    "inputs": {
      "seed": 0,
      "steps": 20,
      "cfg": 8,
      "sampler_name": "euler",
      "scheduler": "normal",
      "denoise": 1,
      "model": [
        "4",
        0
      ],
      "positive": [
        "6",
        0
      ],
      "negative": [
        "7",
        0
      ],
      "latent_image": [
        "5",
        0
      ]
    },
    "class_type": "KSampler",
    "_meta": {
      "title": "KSampler"
    }
  },
  "4": {
    "inputs": {
      "ckpt_name": "model.safetensors"
    },
    "class_type": "CheckpointLoaderSimple",
    "_meta": {
      "title": "Load Checkpoint"
    }
  },
  "5": {
    "inputs": {
      "width": 512,
      "height": 512,
      "batch_size": 1
    },
    "class_type": "EmptyLatentImage",
    "_meta": {
      "title": "Empty Latent Image"
    }
  },
  "6": {
    "inputs": {
      "text": "Prompt",
      "clip": [
        "4",
        1
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "7": {
    "inputs": {
      "text": "",
      "clip": [
        "4",
        1
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "8": {
    "inputs": {
      "samples": [
        "3",
        0
      ],
      "vae": [
        "4",
        2
      ]
    },
    "class_type": "VAEDecode",
    "_meta": {
      "title": "VAE Decode"
    }
  },
  "9": {
    "inputs": {
      "filename_prefix": "ComfyUI",
      "images": [
        "8",
        0
      ]
    },
    "class_type": "SaveImage",
    "_meta": {
      "title": "Save Image"
    }
  }
}
"""


COMFYUI_WORKFLOW = PersistentConfig(
    "COMFYUI_WORKFLOW",
    "image_generation.comfyui.workflow",
    os.getenv("COMFYUI_WORKFLOW", COMFYUI_DEFAULT_WORKFLOW),
)

COMFYUI_WORKFLOW_NODES = PersistentConfig(
    "COMFYUI_WORKFLOW",
    "image_generation.comfyui.nodes",
    [],
)

IMAGES_OPENAI_API_BASE_URL = PersistentConfig(
    "IMAGES_OPENAI_API_BASE_URL",
    "image_generation.openai.api_base_url",
    os.getenv("IMAGES_OPENAI_API_BASE_URL", OPENAI_API_BASE_URL),
)
IMAGES_OPENAI_API_KEY = PersistentConfig(
    "IMAGES_OPENAI_API_KEY",
    "image_generation.openai.api_key",
    os.getenv("IMAGES_OPENAI_API_KEY", OPENAI_API_KEY),
)

IMAGES_GEMINI_API_BASE_URL = PersistentConfig(
    "IMAGES_GEMINI_API_BASE_URL",
    "image_generation.gemini.api_base_url",
    os.getenv("IMAGES_GEMINI_API_BASE_URL", GEMINI_API_BASE_URL),
)
IMAGES_GEMINI_API_KEY = PersistentConfig(
    "IMAGES_GEMINI_API_KEY",
    "image_generation.gemini.api_key",
    os.getenv("IMAGES_GEMINI_API_KEY", GEMINI_API_KEY),
)

IMAGE_SIZE = PersistentConfig(
    "IMAGE_SIZE", "image_generation.size", os.getenv("IMAGE_SIZE", "512x512")
)

IMAGE_STEPS = PersistentConfig(
    "IMAGE_STEPS", "image_generation.steps", int(os.getenv("IMAGE_STEPS", 50))
)

IMAGE_GENERATION_MODEL = PersistentConfig(
    "IMAGE_GENERATION_MODEL",
    "image_generation.model",
    os.getenv("IMAGE_GENERATION_MODEL", ""),
)

####################################
# Audio
####################################

# Transcription
WHISPER_MODEL = UserScopedConfig(
    "audio.stt.whisper_model",
    os.getenv("WHISPER_MODEL", "base"),
)

WHISPER_MODEL_DIR = os.getenv("WHISPER_MODEL_DIR", f"{CACHE_DIR}/whisper/models")
WHISPER_MODEL_AUTO_UPDATE = (
    not OFFLINE_MODE
    and os.environ.get("WHISPER_MODEL_AUTO_UPDATE", "").lower() == "true"
)

# Add Deepgram configuration
DEEPGRAM_API_KEY = PersistentConfig(
    "DEEPGRAM_API_KEY",
    "audio.stt.deepgram.api_key",
    os.getenv("DEEPGRAM_API_KEY", ""),
)

AUDIO_STT_OPENAI_API_BASE_URL = UserScopedConfig(
    "audio.stt.openai.api_base_url",
    os.getenv("AUDIO_STT_OPENAI_API_BASE_URL", OPENAI_API_BASE_URL),
)

AUDIO_STT_OPENAI_API_KEY = UserScopedConfig(
    "audio.stt.openai.api_key",
    os.getenv("AUDIO_STT_OPENAI_API_KEY", OPENAI_API_KEY),
)

AUDIO_STT_PORTKEY_API_BASE_URL = UserScopedConfig(
    "audio.stt.portkey.api_base_url",
    os.getenv("AUDIO_STT_PORTKEY_API_BASE_URL", "https://ai-gateway.apps.cloud.rt.nyu.edu/v1"),
)

AUDIO_STT_PORTKEY_API_KEY = UserScopedConfig(
    "audio.stt.portkey.api_key",
    os.getenv("AUDIO_STT_PORTKEY_API_KEY", ""),
)

AUDIO_STT_ENGINE = UserScopedConfig(
    "audio.stt.engine",
    os.getenv("AUDIO_STT_ENGINE", ""),
)

AUDIO_STT_MODEL = UserScopedConfig(
    "audio.stt.model",
    os.getenv("AUDIO_STT_MODEL", ""),
)

AUDIO_TTS_OPENAI_API_BASE_URL = UserScopedConfig(
    "audio.tts.openai.api_base_url",
    os.getenv("AUDIO_TTS_OPENAI_API_BASE_URL", OPENAI_API_BASE_URL),
)
AUDIO_TTS_OPENAI_API_KEY = UserScopedConfig(
    "audio.tts.openai.api_key",
    os.getenv("AUDIO_TTS_OPENAI_API_KEY", OPENAI_API_KEY),
)

AUDIO_TTS_PORTKEY_API_BASE_URL = UserScopedConfig(
    "audio.tts.portkey.api_base_url",
    os.getenv("AUDIO_TTS_PORTKEY_API_BASE_URL", "https://ai-gateway.apps.cloud.rt.nyu.edu/v1"),
)

AUDIO_TTS_PORTKEY_API_KEY = UserScopedConfig(
    "audio.tts.portkey.api_key",
    os.getenv("AUDIO_TTS_PORTKEY_API_KEY", ""),
)

AUDIO_TTS_API_KEY = UserScopedConfig(
    "audio.tts.api_key",
    os.getenv("AUDIO_TTS_API_KEY", ""),
)

AUDIO_TTS_ENGINE = UserScopedConfig(
    "audio.tts.engine",
    os.getenv("AUDIO_TTS_ENGINE", ""),
)


AUDIO_TTS_MODEL = UserScopedConfig(
    "audio.tts.model",
    os.getenv("AUDIO_TTS_MODEL", "@openai-4o-mini-audio/gpt-4o-mini-audio-preview"),  # Portkey audio model
)

AUDIO_TTS_VOICE = UserScopedConfig(
    "audio.tts.voice",
    os.getenv("AUDIO_TTS_VOICE", "de-DE-KatjaNeural"),  # Default German voice with full identifier
)

AUDIO_TTS_LANGUAGE = UserScopedConfig(
    "audio.tts.language",
    os.getenv("AUDIO_TTS_LANGUAGE", "de-DE"),  # Default German (Germany)
)

AUDIO_TTS_AUDIO_VOICE = UserScopedConfig(
    "audio.tts.audio_voice",
    os.getenv("AUDIO_TTS_AUDIO_VOICE", "alloy"),  # OpenAI audio voice (alloy/echo/shimmer)
)

AUDIO_TTS_SPLIT_ON = UserScopedConfig(
    "audio.tts.split_on",
    os.getenv("AUDIO_TTS_SPLIT_ON", "punctuation"),
)

AUDIO_TTS_AZURE_SPEECH_REGION = UserScopedConfig(
    "audio.tts.azure.speech_region",
    os.getenv("AUDIO_TTS_AZURE_SPEECH_REGION", "eastus"),
)

AUDIO_TTS_AZURE_SPEECH_OUTPUT_FORMAT = UserScopedConfig(
    "audio.tts.azure.speech_output_format",
    os.getenv(
        "AUDIO_TTS_AZURE_SPEECH_OUTPUT_FORMAT", "audio-24khz-160kbitrate-mono-mp3"
    ),
)


####################################
# LDAP
####################################

ENABLE_LDAP = PersistentConfig(
    "ENABLE_LDAP",
    "ldap.enable",
    os.environ.get("ENABLE_LDAP", "false").lower() == "true",
)

LDAP_SERVER_LABEL = PersistentConfig(
    "LDAP_SERVER_LABEL",
    "ldap.server.label",
    os.environ.get("LDAP_SERVER_LABEL", "LDAP Server"),
)

LDAP_SERVER_HOST = PersistentConfig(
    "LDAP_SERVER_HOST",
    "ldap.server.host",
    os.environ.get("LDAP_SERVER_HOST", "localhost"),
)

LDAP_SERVER_PORT = PersistentConfig(
    "LDAP_SERVER_PORT",
    "ldap.server.port",
    int(os.environ.get("LDAP_SERVER_PORT", "389")),
)

LDAP_ATTRIBUTE_FOR_MAIL = PersistentConfig(
    "LDAP_ATTRIBUTE_FOR_MAIL",
    "ldap.server.attribute_for_mail",
    os.environ.get("LDAP_ATTRIBUTE_FOR_MAIL", "mail"),
)

LDAP_ATTRIBUTE_FOR_USERNAME = PersistentConfig(
    "LDAP_ATTRIBUTE_FOR_USERNAME",
    "ldap.server.attribute_for_username",
    os.environ.get("LDAP_ATTRIBUTE_FOR_USERNAME", "uid"),
)

LDAP_APP_DN = PersistentConfig(
    "LDAP_APP_DN", "ldap.server.app_dn", os.environ.get("LDAP_APP_DN", "")
)

LDAP_APP_PASSWORD = PersistentConfig(
    "LDAP_APP_PASSWORD",
    "ldap.server.app_password",
    os.environ.get("LDAP_APP_PASSWORD", ""),
)

LDAP_SEARCH_BASE = PersistentConfig(
    "LDAP_SEARCH_BASE", "ldap.server.users_dn", os.environ.get("LDAP_SEARCH_BASE", "")
)

LDAP_SEARCH_FILTERS = PersistentConfig(
    "LDAP_SEARCH_FILTER",
    "ldap.server.search_filter",
    os.environ.get("LDAP_SEARCH_FILTER", os.environ.get("LDAP_SEARCH_FILTERS", "")),
)

LDAP_USE_TLS = PersistentConfig(
    "LDAP_USE_TLS",
    "ldap.server.use_tls",
    os.environ.get("LDAP_USE_TLS", "True").lower() == "true",
)

LDAP_CA_CERT_FILE = PersistentConfig(
    "LDAP_CA_CERT_FILE",
    "ldap.server.ca_cert_file",
    os.environ.get("LDAP_CA_CERT_FILE", ""),
)

LDAP_CIPHERS = PersistentConfig(
    "LDAP_CIPHERS", "ldap.server.ciphers", os.environ.get("LDAP_CIPHERS", "ALL")
)
