import json
import logging
import os
import shutil
import base64
import redis

from datetime import datetime
from pathlib import Path
from typing import Generic, Optional, TypeVar
from urllib.parse import urlparse

import requests
from pydantic import BaseModel
from sqlalchemy import JSON, Column, DateTime, Integer, func

from open_webui.env import (
    DATA_DIR,
    DATABASE_URL,
    ENV,
    REDIS_URL,
    REDIS_SENTINEL_HOSTS,
    REDIS_SENTINEL_PORT,
    FRONTEND_BUILD_DIR,
    OFFLINE_MODE,
    OPEN_WEBUI_DIR,
    WEBUI_AUTH,
    WEBUI_FAVICON_URL,
    WEBUI_NAME,
    log,
)
from open_webui.internal.db import Base, get_db
from open_webui.utils.redis import get_redis_connection


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
    data = Column(JSON, nullable=False)
    version = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())


def load_json_config():
    with open(f"{DATA_DIR}/config.json", "r") as file:
        return json.load(file)


def save_to_db(data):
    with get_db() as db:
        existing_config = db.query(Config).first()
        if not existing_config:
            new_config = Config(data=data, version=0)
            db.add(new_config)
        else:
            existing_config.data = data
            existing_config.updated_at = datetime.now()
            db.add(existing_config)
        db.commit()


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
    "ui": {},
}


def get_config():
    with get_db() as db:
        config_entry = db.query(Config).order_by(Config.id.desc()).first()
        return config_entry.data if config_entry else DEFAULT_CONFIG


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

ENABLE_PERSISTENT_CONFIG = (
    os.environ.get("ENABLE_PERSISTENT_CONFIG", "True").lower() == "true"
)


class PersistentConfig(Generic[T]):
    def __init__(self, env_name: str, config_path: str, env_value: T):
        self.env_name = env_name
        self.config_path = config_path
        self.env_value = env_value
        self.config_value = get_config_value(config_path)
        if self.config_value is not None and ENABLE_PERSISTENT_CONFIG:
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


class AppConfig:
    _state: dict[str, PersistentConfig]
    _redis: Optional[redis.Redis] = None

    def __init__(
        self, redis_url: Optional[str] = None, redis_sentinels: Optional[list] = []
    ):
        super().__setattr__("_state", {})
        if redis_url:
            super().__setattr__(
                "_redis",
                get_redis_connection(redis_url, redis_sentinels, decode_responses=True),
            )

    def __setattr__(self, key, value):
        if isinstance(value, PersistentConfig):
            self._state[key] = value
        else:
            self._state[key].value = value
            self._state[key].save()

            if self._redis:
                redis_key = f"open-webui:config:{key}"
                self._redis.set(redis_key, json.dumps(self._state[key].value))

    def __getattr__(self, key):
        if key not in self._state:
            raise AttributeError(f"Config key '{key}' not found")

        # If Redis is available, check for an updated value
        if self._redis:
            redis_key = f"open-webui:config:{key}"
            redis_value = self._redis.get(redis_key)

            if redis_value is not None:
                try:
                    decoded_value = json.loads(redis_value)

                    # Update the in-memory value if different
                    if self._state[key].value != decoded_value:
                        self._state[key].value = decoded_value
                        log.info(f"Updated {key} from Redis: {decoded_value}")

                except json.JSONDecodeError:
                    log.error(f"Invalid JSON format in Redis for {key}: {redis_value}")

        return self._state[key].value


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

MICROSOFT_CLIENT_LOGIN_BASE_URL = PersistentConfig(
    "MICROSOFT_CLIENT_LOGIN_BASE_URL",
    "oauth.microsoft.login_base_url",
    os.environ.get(
        "MICROSOFT_CLIENT_LOGIN_BASE_URL", "https://login.microsoftonline.com"
    ),
)

MICROSOFT_CLIENT_PICTURE_URL = PersistentConfig(
    "MICROSOFT_CLIENT_PICTURE_URL",
    "oauth.microsoft.picture_url",
    os.environ.get(
        "MICROSOFT_CLIENT_PICTURE_URL",
        "https://graph.microsoft.com/v1.0/me/photo/$value",
    ),
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

OAUTH_CODE_CHALLENGE_METHOD = PersistentConfig(
    "OAUTH_CODE_CHALLENGE_METHOD",
    "oauth.oidc.code_challenge_method",
    os.environ.get("OAUTH_CODE_CHALLENGE_METHOD", None),
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

ENABLE_OAUTH_GROUP_CREATION = PersistentConfig(
    "ENABLE_OAUTH_GROUP_CREATION",
    "oauth.enable_group_creation",
    os.environ.get("ENABLE_OAUTH_GROUP_CREATION", "False").lower() == "true",
)


OAUTH_BLOCKED_GROUPS = PersistentConfig(
    "OAUTH_BLOCKED_GROUPS",
    "oauth.blocked_groups",
    os.environ.get("OAUTH_BLOCKED_GROUPS", "[]"),
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

OAUTH_UPDATE_PICTURE_ON_LOGIN = PersistentConfig(
    "OAUTH_UPDATE_PICTURE_ON_LOGIN",
    "oauth.update_picture_on_login",
    os.environ.get("OAUTH_UPDATE_PICTURE_ON_LOGIN", "False").lower() == "true",
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
                server_metadata_url=f"{MICROSOFT_CLIENT_LOGIN_BASE_URL.value}/{MICROSOFT_CLIENT_TENANT_ID.value}/v2.0/.well-known/openid-configuration?appid={MICROSOFT_CLIENT_ID.value}",
                client_kwargs={
                    "scope": MICROSOFT_OAUTH_SCOPE.value,
                },
                redirect_uri=MICROSOFT_REDIRECT_URI.value,
            )

        OAUTH_PROVIDERS["microsoft"] = {
            "redirect_uri": MICROSOFT_REDIRECT_URI.value,
            "picture_url": MICROSOFT_CLIENT_PICTURE_URL.value,
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
            client_kwargs = {
                "scope": OAUTH_SCOPES.value,
            }

            if (
                OAUTH_CODE_CHALLENGE_METHOD.value
                and OAUTH_CODE_CHALLENGE_METHOD.value == "S256"
            ):
                client_kwargs["code_challenge_method"] = "S256"
            elif OAUTH_CODE_CHALLENGE_METHOD.value:
                raise Exception(
                    'Code challenge methods other than "%s" not supported. Given: "%s"'
                    % ("S256", OAUTH_CODE_CHALLENGE_METHOD.value)
                )

            client.register(
                name="oidc",
                client_id=OAUTH_CLIENT_ID.value,
                client_secret=OAUTH_CLIENT_SECRET.value,
                server_metadata_url=OPENID_PROVIDER_URL.value,
                client_kwargs=client_kwargs,
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

for file_path in (FRONTEND_BUILD_DIR / "static").glob("**/*"):
    if file_path.is_file():
        target_path = STATIC_DIR / file_path.relative_to(
            (FRONTEND_BUILD_DIR / "static")
        )
        target_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copyfile(file_path, target_path)
        except Exception as e:
            logging.error(f"An error occurred: {e}")

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

LICENSE_KEY = os.environ.get("LICENSE_KEY", "")

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
    os.environ.get("S3_USE_ACCELERATE_ENDPOINT", "false").lower() == "true"
)
S3_ADDRESSING_STYLE = os.environ.get("S3_ADDRESSING_STYLE", None)
S3_ENABLE_TAGGING = os.getenv("S3_ENABLE_TAGGING", "false").lower() == "true"

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

UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


####################################
# Cache DIR
####################################

CACHE_DIR = DATA_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


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
# TOOL_SERVERS
####################################

try:
    tool_server_connections = json.loads(
        os.environ.get("TOOL_SERVER_CONNECTIONS", "[]")
    )
except Exception as e:
    log.exception(f"Error loading TOOL_SERVER_CONNECTIONS: {e}")
    tool_server_connections = []


TOOL_SERVER_CONNECTIONS = PersistentConfig(
    "TOOL_SERVER_CONNECTIONS",
    "tool_server.connections",
    tool_server_connections,
)

####################################
# WEBUI
####################################


WEBUI_URL = PersistentConfig("WEBUI_URL", "webui.url", os.environ.get("WEBUI_URL", ""))


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

try:
    default_prompt_suggestions = json.loads(
        os.environ.get("DEFAULT_PROMPT_SUGGESTIONS", "[]")
    )
except Exception as e:
    log.exception(f"Error loading DEFAULT_PROMPT_SUGGESTIONS: {e}")
    default_prompt_suggestions = []
if default_prompt_suggestions == []:
    default_prompt_suggestions = [
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
    ]

DEFAULT_PROMPT_SUGGESTIONS = PersistentConfig(
    "DEFAULT_PROMPT_SUGGESTIONS",
    "ui.prompt_suggestions",
    default_prompt_suggestions,
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

PENDING_USER_OVERLAY_TITLE = PersistentConfig(
    "PENDING_USER_OVERLAY_TITLE",
    "ui.pending_user_overlay_title",
    os.environ.get("PENDING_USER_OVERLAY_TITLE", ""),
)

PENDING_USER_OVERLAY_CONTENT = PersistentConfig(
    "PENDING_USER_OVERLAY_CONTENT",
    "ui.pending_user_overlay_content",
    os.environ.get("PENDING_USER_OVERLAY_CONTENT", ""),
)


RESPONSE_WATERMARK = PersistentConfig(
    "RESPONSE_WATERMARK",
    "ui.watermark",
    os.environ.get("RESPONSE_WATERMARK", ""),
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

USER_PERMISSIONS_WORKSPACE_MODELS_ALLOW_PUBLIC_SHARING = (
    os.environ.get(
        "USER_PERMISSIONS_WORKSPACE_MODELS_ALLOW_PUBLIC_SHARING", "False"
    ).lower()
    == "true"
)

USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ALLOW_PUBLIC_SHARING = (
    os.environ.get(
        "USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ALLOW_PUBLIC_SHARING", "False"
    ).lower()
    == "true"
)

USER_PERMISSIONS_WORKSPACE_PROMPTS_ALLOW_PUBLIC_SHARING = (
    os.environ.get(
        "USER_PERMISSIONS_WORKSPACE_PROMPTS_ALLOW_PUBLIC_SHARING", "False"
    ).lower()
    == "true"
)

USER_PERMISSIONS_WORKSPACE_TOOLS_ALLOW_PUBLIC_SHARING = (
    os.environ.get(
        "USER_PERMISSIONS_WORKSPACE_TOOLS_ALLOW_PUBLIC_SHARING", "False"
    ).lower()
    == "true"
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

USER_PERMISSIONS_CHAT_SHARE = (
    os.environ.get("USER_PERMISSIONS_CHAT_SHARE", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_EXPORT = (
    os.environ.get("USER_PERMISSIONS_CHAT_EXPORT", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_STT = (
    os.environ.get("USER_PERMISSIONS_CHAT_STT", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_TTS = (
    os.environ.get("USER_PERMISSIONS_CHAT_TTS", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_CALL = (
    os.environ.get("USER_PERMISSIONS_CHAT_CALL", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_MULTIPLE_MODELS = (
    os.environ.get("USER_PERMISSIONS_CHAT_MULTIPLE_MODELS", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_TEMPORARY = (
    os.environ.get("USER_PERMISSIONS_CHAT_TEMPORARY", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_TEMPORARY_ENFORCED = (
    os.environ.get("USER_PERMISSIONS_CHAT_TEMPORARY_ENFORCED", "False").lower()
    == "true"
)


USER_PERMISSIONS_FEATURES_DIRECT_TOOL_SERVERS = (
    os.environ.get("USER_PERMISSIONS_FEATURES_DIRECT_TOOL_SERVERS", "False").lower()
    == "true"
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

USER_PERMISSIONS_FEATURES_NOTES = (
    os.environ.get("USER_PERMISSIONS_FEATURES_NOTES", "True").lower() == "true"
)


DEFAULT_USER_PERMISSIONS = {
    "workspace": {
        "models": USER_PERMISSIONS_WORKSPACE_MODELS_ACCESS,
        "knowledge": USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ACCESS,
        "prompts": USER_PERMISSIONS_WORKSPACE_PROMPTS_ACCESS,
        "tools": USER_PERMISSIONS_WORKSPACE_TOOLS_ACCESS,
    },
    "sharing": {
        "public_models": USER_PERMISSIONS_WORKSPACE_MODELS_ALLOW_PUBLIC_SHARING,
        "public_knowledge": USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ALLOW_PUBLIC_SHARING,
        "public_prompts": USER_PERMISSIONS_WORKSPACE_PROMPTS_ALLOW_PUBLIC_SHARING,
        "public_tools": USER_PERMISSIONS_WORKSPACE_TOOLS_ALLOW_PUBLIC_SHARING,
    },
    "chat": {
        "controls": USER_PERMISSIONS_CHAT_CONTROLS,
        "file_upload": USER_PERMISSIONS_CHAT_FILE_UPLOAD,
        "delete": USER_PERMISSIONS_CHAT_DELETE,
        "edit": USER_PERMISSIONS_CHAT_EDIT,
        "share": USER_PERMISSIONS_CHAT_SHARE,
        "export": USER_PERMISSIONS_CHAT_EXPORT,
        "stt": USER_PERMISSIONS_CHAT_STT,
        "tts": USER_PERMISSIONS_CHAT_TTS,
        "call": USER_PERMISSIONS_CHAT_CALL,
        "multiple_models": USER_PERMISSIONS_CHAT_MULTIPLE_MODELS,
        "temporary": USER_PERMISSIONS_CHAT_TEMPORARY,
        "temporary_enforced": USER_PERMISSIONS_CHAT_TEMPORARY_ENFORCED,
    },
    "features": {
        "direct_tool_servers": USER_PERMISSIONS_FEATURES_DIRECT_TOOL_SERVERS,
        "web_search": USER_PERMISSIONS_FEATURES_WEB_SEARCH,
        "image_generation": USER_PERMISSIONS_FEATURES_IMAGE_GENERATION,
        "code_interpreter": USER_PERMISSIONS_FEATURES_CODE_INTERPRETER,
        "notes": USER_PERMISSIONS_FEATURES_NOTES,
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

ENABLE_NOTES = PersistentConfig(
    "ENABLE_NOTES",
    "notes.enable",
    os.environ.get("ENABLE_NOTES", "True").lower() == "true",
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

ENABLE_USER_WEBHOOKS = PersistentConfig(
    "ENABLE_USER_WEBHOOKS",
    "ui.enable_user_webhooks",
    os.environ.get("ENABLE_USER_WEBHOOKS", "True").lower() == "true",
)

# FastAPI / AnyIO settings
THREAD_POOL_SIZE = os.getenv("THREAD_POOL_SIZE", None)

if THREAD_POOL_SIZE is not None and isinstance(THREAD_POOL_SIZE, str):
    try:
        THREAD_POOL_SIZE = int(THREAD_POOL_SIZE)
    except ValueError:
        log.warning(
            f"THREAD_POOL_SIZE is not a valid integer: {THREAD_POOL_SIZE}. Defaulting to None."
        )
        THREAD_POOL_SIZE = None


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
# CORS_ALLOW_ORIGIN=http://localhost:5173;http://localhost:8080
# in your .env file depending on your frontend port, 5173 in this case.
CORS_ALLOW_ORIGIN = os.environ.get("CORS_ALLOW_ORIGIN", "*").split(";")

if CORS_ALLOW_ORIGIN == ["*"]:
    log.warning(
        "\n\nWARNING: CORS_ALLOW_ORIGIN IS SET TO '*' - NOT RECOMMENDED FOR PRODUCTION DEPLOYMENTS.\n"
    )
else:
    # You have to pick between a single wildcard or a list of origins.
    # Doing both will result in CORS errors in the browser.
    for origin in CORS_ALLOW_ORIGIN:
        validate_cors_origin(origin)


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

TASK_MODEL_EXTERNAL = PersistentConfig(
    "TASK_MODEL_EXTERNAL",
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
- Your entire response must consist solely of the JSON object, without any introductory or concluding text.
- The output must be a single, raw JSON object, without any markdown code fences or other encapsulating text.
- Ensure no conversational text, affirmations, or explanations precede or follow the raw JSON output, as this will cause direct parsing failure.
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


FOLLOW_UP_GENERATION_PROMPT_TEMPLATE = PersistentConfig(
    "FOLLOW_UP_GENERATION_PROMPT_TEMPLATE",
    "task.follow_up.prompt_template",
    os.environ.get("FOLLOW_UP_GENERATION_PROMPT_TEMPLATE", ""),
)

DEFAULT_FOLLOW_UP_GENERATION_PROMPT_TEMPLATE = """### Task:
Suggest 3-5 relevant follow-up questions or prompts that the user might naturally ask next in this conversation as a **user**, based on the chat history, to help continue or deepen the discussion.
### Guidelines:
- Write all follow-up questions from the user’s point of view, directed to the assistant.
- Make questions concise, clear, and directly related to the discussed topic(s).
- Only suggest follow-ups that make sense given the chat content and do not repeat what was already covered.
- If the conversation is very short or not specific, suggest more general (but relevant) follow-ups the user might ask.
- Use the conversation's primary language; default to English if multilingual.
- Response must be a JSON array of strings, no extra text or formatting.
### Output:
JSON format: { "follow_ups": ["Question 1?", "Question 2?", "Question 3?"] }
### Chat History:
<chat_history>
{{MESSAGES:END:6}}
</chat_history>"""

ENABLE_FOLLOW_UP_GENERATION = PersistentConfig(
    "ENABLE_FOLLOW_UP_GENERATION",
    "task.follow_up.enable",
    os.environ.get("ENABLE_FOLLOW_UP_GENERATION", "True").lower() == "true",
)

ENABLE_TAGS_GENERATION = PersistentConfig(
    "ENABLE_TAGS_GENERATION",
    "task.tags.enable",
    os.environ.get("ENABLE_TAGS_GENERATION", "True").lower() == "true",
)

ENABLE_TITLE_GENERATION = PersistentConfig(
    "ENABLE_TITLE_GENERATION",
    "task.title.enable",
    os.environ.get("ENABLE_TITLE_GENERATION", "True").lower() == "true",
)


ENABLE_SEARCH_QUERY_GENERATION = PersistentConfig(
    "ENABLE_SEARCH_QUERY_GENERATION",
    "task.query.search.enable",
    os.environ.get("ENABLE_SEARCH_QUERY_GENERATION", "True").lower() == "true",
)

ENABLE_RETRIEVAL_QUERY_GENERATION = PersistentConfig(
    "ENABLE_RETRIEVAL_QUERY_GENERATION",
    "task.query.retrieval.enable",
    os.environ.get("ENABLE_RETRIEVAL_QUERY_GENERATION", "True").lower() == "true",
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

ENABLE_AUTOCOMPLETE_GENERATION = PersistentConfig(
    "ENABLE_AUTOCOMPLETE_GENERATION",
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

ENABLE_CODE_EXECUTION = PersistentConfig(
    "ENABLE_CODE_EXECUTION",
    "code_execution.enable",
    os.environ.get("ENABLE_CODE_EXECUTION", "True").lower() == "true",
)

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
   - To use it, **you must enclose your code within `<code_interpreter type="code" lang="python">` XML tags** and stop right away. If you don't, the code won't execute. 
   - When writing code in the code_interpreter XML tag, Do NOT use the triple backticks code block for markdown formatting, example: ```py # python code ``` will cause an error because it is markdown formatting, it is not python code.
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

MILVUS_INDEX_TYPE = os.environ.get("MILVUS_INDEX_TYPE", "HNSW")
MILVUS_METRIC_TYPE = os.environ.get("MILVUS_METRIC_TYPE", "COSINE")
MILVUS_HNSW_M = int(os.environ.get("MILVUS_HNSW_M", "16"))
MILVUS_HNSW_EFCONSTRUCTION = int(os.environ.get("MILVUS_HNSW_EFCONSTRUCTION", "100"))
MILVUS_IVF_FLAT_NLIST = int(os.environ.get("MILVUS_IVF_FLAT_NLIST", "128"))

# Qdrant
QDRANT_URI = os.environ.get("QDRANT_URI", None)
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", None)
QDRANT_ON_DISK = os.environ.get("QDRANT_ON_DISK", "false").lower() == "true"
QDRANT_PREFER_GRPC = os.environ.get("QDRANT_PREFER_GRPC", "False").lower() == "true"
QDRANT_GRPC_PORT = int(os.environ.get("QDRANT_GRPC_PORT", "6334"))
ENABLE_QDRANT_MULTITENANCY_MODE = (
    os.environ.get("ENABLE_QDRANT_MULTITENANCY_MODE", "false").lower() == "true"
)

# OpenSearch
OPENSEARCH_URI = os.environ.get("OPENSEARCH_URI", "https://localhost:9200")
OPENSEARCH_SSL = os.environ.get("OPENSEARCH_SSL", "true").lower() == "true"
OPENSEARCH_CERT_VERIFY = (
    os.environ.get("OPENSEARCH_CERT_VERIFY", "false").lower() == "true"
)
OPENSEARCH_USERNAME = os.environ.get("OPENSEARCH_USERNAME", None)
OPENSEARCH_PASSWORD = os.environ.get("OPENSEARCH_PASSWORD", None)

# ElasticSearch
ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL", "https://localhost:9200")
ELASTICSEARCH_CA_CERTS = os.environ.get("ELASTICSEARCH_CA_CERTS", None)
ELASTICSEARCH_API_KEY = os.environ.get("ELASTICSEARCH_API_KEY", None)
ELASTICSEARCH_USERNAME = os.environ.get("ELASTICSEARCH_USERNAME", None)
ELASTICSEARCH_PASSWORD = os.environ.get("ELASTICSEARCH_PASSWORD", None)
ELASTICSEARCH_CLOUD_ID = os.environ.get("ELASTICSEARCH_CLOUD_ID", None)
SSL_ASSERT_FINGERPRINT = os.environ.get("SSL_ASSERT_FINGERPRINT", None)
ELASTICSEARCH_INDEX_PREFIX = os.environ.get(
    "ELASTICSEARCH_INDEX_PREFIX", "open_webui_collections"
)
# Pgvector
PGVECTOR_DB_URL = os.environ.get("PGVECTOR_DB_URL", DATABASE_URL)
if VECTOR_DB == "pgvector" and not PGVECTOR_DB_URL.startswith("postgres"):
    raise ValueError(
        "Pgvector requires setting PGVECTOR_DB_URL or using Postgres with vector extension as the primary database."
    )
PGVECTOR_INITIALIZE_MAX_VECTOR_LENGTH = int(
    os.environ.get("PGVECTOR_INITIALIZE_MAX_VECTOR_LENGTH", "1536")
)

PGVECTOR_PGCRYPTO = os.getenv("PGVECTOR_PGCRYPTO", "false").lower() == "true"
PGVECTOR_PGCRYPTO_KEY = os.getenv("PGVECTOR_PGCRYPTO_KEY", None)
if PGVECTOR_PGCRYPTO and not PGVECTOR_PGCRYPTO_KEY:
    raise ValueError(
        "PGVECTOR_PGCRYPTO is enabled but PGVECTOR_PGCRYPTO_KEY is not set. Please provide a valid key."
    )

# Pinecone
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY", None)
PINECONE_ENVIRONMENT = os.environ.get("PINECONE_ENVIRONMENT", None)
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "open-webui-index")
PINECONE_DIMENSION = int(os.getenv("PINECONE_DIMENSION", 1536))  # or 3072, 1024, 768
PINECONE_METRIC = os.getenv("PINECONE_METRIC", "cosine")
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")  # or "gcp" or "azure"

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

ONEDRIVE_SHAREPOINT_URL = PersistentConfig(
    "ONEDRIVE_SHAREPOINT_URL",
    "onedrive.sharepoint_url",
    os.environ.get("ONEDRIVE_SHAREPOINT_URL", ""),
)

ONEDRIVE_SHAREPOINT_TENANT_ID = PersistentConfig(
    "ONEDRIVE_SHAREPOINT_TENANT_ID",
    "onedrive.sharepoint_tenant_id",
    os.environ.get("ONEDRIVE_SHAREPOINT_TENANT_ID", ""),
)

# RAG Content Extraction
CONTENT_EXTRACTION_ENGINE = PersistentConfig(
    "CONTENT_EXTRACTION_ENGINE",
    "rag.CONTENT_EXTRACTION_ENGINE",
    os.environ.get("CONTENT_EXTRACTION_ENGINE", "").lower(),
)

DATALAB_MARKER_API_KEY = PersistentConfig(
    "DATALAB_MARKER_API_KEY",
    "rag.datalab_marker_api_key",
    os.environ.get("DATALAB_MARKER_API_KEY", ""),
)

DATALAB_MARKER_LANGS = PersistentConfig(
    "DATALAB_MARKER_LANGS",
    "rag.datalab_marker_langs",
    os.environ.get("DATALAB_MARKER_LANGS", ""),
)

DATALAB_MARKER_USE_LLM = PersistentConfig(
    "DATALAB_MARKER_USE_LLM",
    "rag.DATALAB_MARKER_USE_LLM",
    os.environ.get("DATALAB_MARKER_USE_LLM", "false").lower() == "true",
)

DATALAB_MARKER_SKIP_CACHE = PersistentConfig(
    "DATALAB_MARKER_SKIP_CACHE",
    "rag.datalab_marker_skip_cache",
    os.environ.get("DATALAB_MARKER_SKIP_CACHE", "false").lower() == "true",
)

DATALAB_MARKER_FORCE_OCR = PersistentConfig(
    "DATALAB_MARKER_FORCE_OCR",
    "rag.datalab_marker_force_ocr",
    os.environ.get("DATALAB_MARKER_FORCE_OCR", "false").lower() == "true",
)

DATALAB_MARKER_PAGINATE = PersistentConfig(
    "DATALAB_MARKER_PAGINATE",
    "rag.datalab_marker_paginate",
    os.environ.get("DATALAB_MARKER_PAGINATE", "false").lower() == "true",
)

DATALAB_MARKER_STRIP_EXISTING_OCR = PersistentConfig(
    "DATALAB_MARKER_STRIP_EXISTING_OCR",
    "rag.datalab_marker_strip_existing_ocr",
    os.environ.get("DATALAB_MARKER_STRIP_EXISTING_OCR", "false").lower() == "true",
)

DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION = PersistentConfig(
    "DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION",
    "rag.datalab_marker_disable_image_extraction",
    os.environ.get("DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION", "false").lower()
    == "true",
)

DATALAB_MARKER_OUTPUT_FORMAT = PersistentConfig(
    "DATALAB_MARKER_OUTPUT_FORMAT",
    "rag.datalab_marker_output_format",
    os.environ.get("DATALAB_MARKER_OUTPUT_FORMAT", "markdown"),
)

EXTERNAL_DOCUMENT_LOADER_URL = PersistentConfig(
    "EXTERNAL_DOCUMENT_LOADER_URL",
    "rag.external_document_loader_url",
    os.environ.get("EXTERNAL_DOCUMENT_LOADER_URL", ""),
)

EXTERNAL_DOCUMENT_LOADER_API_KEY = PersistentConfig(
    "EXTERNAL_DOCUMENT_LOADER_API_KEY",
    "rag.external_document_loader_api_key",
    os.environ.get("EXTERNAL_DOCUMENT_LOADER_API_KEY", ""),
)

TIKA_SERVER_URL = PersistentConfig(
    "TIKA_SERVER_URL",
    "rag.tika_server_url",
    os.getenv("TIKA_SERVER_URL", "http://tika:9998"),  # Default for sidecar deployment
)

DOCLING_SERVER_URL = PersistentConfig(
    "DOCLING_SERVER_URL",
    "rag.docling_server_url",
    os.getenv("DOCLING_SERVER_URL", "http://docling:5001"),
)

DOCLING_OCR_ENGINE = PersistentConfig(
    "DOCLING_OCR_ENGINE",
    "rag.docling_ocr_engine",
    os.getenv("DOCLING_OCR_ENGINE", "tesseract"),
)

DOCLING_OCR_LANG = PersistentConfig(
    "DOCLING_OCR_LANG",
    "rag.docling_ocr_lang",
    os.getenv("DOCLING_OCR_LANG", "eng,fra,deu,spa"),
)

DOCLING_DO_PICTURE_DESCRIPTION = PersistentConfig(
    "DOCLING_DO_PICTURE_DESCRIPTION",
    "rag.docling_do_picture_description",
    os.getenv("DOCLING_DO_PICTURE_DESCRIPTION", "False").lower() == "true",
)

DOCLING_PICTURE_DESCRIPTION_MODE = PersistentConfig(
    "DOCLING_PICTURE_DESCRIPTION_MODE",
    "rag.docling_picture_description_mode",
    os.getenv("DOCLING_PICTURE_DESCRIPTION_MODE", ""),
)


docling_picture_description_local = os.getenv("DOCLING_PICTURE_DESCRIPTION_LOCAL", "")
try:
    docling_picture_description_local = json.loads(docling_picture_description_local)
except json.JSONDecodeError:
    docling_picture_description_local = {}


DOCLING_PICTURE_DESCRIPTION_LOCAL = PersistentConfig(
    "DOCLING_PICTURE_DESCRIPTION_LOCAL",
    "rag.docling_picture_description_local",
    docling_picture_description_local,
)

docling_picture_description_api = os.getenv("DOCLING_PICTURE_DESCRIPTION_API", "")
try:
    docling_picture_description_api = json.loads(docling_picture_description_api)
except json.JSONDecodeError:
    docling_picture_description_api = {}


DOCLING_PICTURE_DESCRIPTION_API = PersistentConfig(
    "DOCLING_PICTURE_DESCRIPTION_API",
    "rag.docling_picture_description_api",
    docling_picture_description_api,
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

MISTRAL_OCR_API_KEY = PersistentConfig(
    "MISTRAL_OCR_API_KEY",
    "rag.mistral_ocr_api_key",
    os.getenv("MISTRAL_OCR_API_KEY", ""),
)

BYPASS_EMBEDDING_AND_RETRIEVAL = PersistentConfig(
    "BYPASS_EMBEDDING_AND_RETRIEVAL",
    "rag.bypass_embedding_and_retrieval",
    os.environ.get("BYPASS_EMBEDDING_AND_RETRIEVAL", "False").lower() == "true",
)


RAG_TOP_K = PersistentConfig(
    "RAG_TOP_K", "rag.top_k", int(os.environ.get("RAG_TOP_K", "3"))
)
RAG_TOP_K_RERANKER = PersistentConfig(
    "RAG_TOP_K_RERANKER",
    "rag.top_k_reranker",
    int(os.environ.get("RAG_TOP_K_RERANKER", "3")),
)
RAG_RELEVANCE_THRESHOLD = PersistentConfig(
    "RAG_RELEVANCE_THRESHOLD",
    "rag.relevance_threshold",
    float(os.environ.get("RAG_RELEVANCE_THRESHOLD", "0.0")),
)
RAG_HYBRID_BM25_WEIGHT = PersistentConfig(
    "RAG_HYBRID_BM25_WEIGHT",
    "rag.hybrid_bm25_weight",
    float(os.environ.get("RAG_HYBRID_BM25_WEIGHT", "0.5")),
)

ENABLE_RAG_HYBRID_SEARCH = PersistentConfig(
    "ENABLE_RAG_HYBRID_SEARCH",
    "rag.enable_hybrid_search",
    os.environ.get("ENABLE_RAG_HYBRID_SEARCH", "").lower() == "true",
)

RAG_FULL_CONTEXT = PersistentConfig(
    "RAG_FULL_CONTEXT",
    "rag.full_context",
    os.getenv("RAG_FULL_CONTEXT", "False").lower() == "true",
)

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

RAG_ALLOWED_FILE_EXTENSIONS = PersistentConfig(
    "RAG_ALLOWED_FILE_EXTENSIONS",
    "rag.file.allowed_extensions",
    [
        ext.strip()
        for ext in os.environ.get("RAG_ALLOWED_FILE_EXTENSIONS", "").split(",")
        if ext.strip()
    ],
)

RAG_EMBEDDING_ENGINE = PersistentConfig(
    "RAG_EMBEDDING_ENGINE",
    "rag.embedding_engine",
    os.environ.get("RAG_EMBEDDING_ENGINE", ""),
)

PDF_EXTRACT_IMAGES = PersistentConfig(
    "PDF_EXTRACT_IMAGES",
    "rag.pdf_extract_images",
    os.environ.get("PDF_EXTRACT_IMAGES", "False").lower() == "true",
)

RAG_EMBEDDING_MODEL = PersistentConfig(
    "RAG_EMBEDDING_MODEL",
    "rag.embedding_model",
    os.environ.get("RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
)
log.info(f"Embedding model set: {RAG_EMBEDDING_MODEL.value}")

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

RAG_EMBEDDING_QUERY_PREFIX = os.environ.get("RAG_EMBEDDING_QUERY_PREFIX", None)

RAG_EMBEDDING_CONTENT_PREFIX = os.environ.get("RAG_EMBEDDING_CONTENT_PREFIX", None)

RAG_EMBEDDING_PREFIX_FIELD_NAME = os.environ.get(
    "RAG_EMBEDDING_PREFIX_FIELD_NAME", None
)

RAG_RERANKING_ENGINE = PersistentConfig(
    "RAG_RERANKING_ENGINE",
    "rag.reranking_engine",
    os.environ.get("RAG_RERANKING_ENGINE", ""),
)

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

RAG_EXTERNAL_RERANKER_URL = PersistentConfig(
    "RAG_EXTERNAL_RERANKER_URL",
    "rag.external_reranker_url",
    os.environ.get("RAG_EXTERNAL_RERANKER_URL", ""),
)

RAG_EXTERNAL_RERANKER_API_KEY = PersistentConfig(
    "RAG_EXTERNAL_RERANKER_API_KEY",
    "rag.external_reranker_api_key",
    os.environ.get("RAG_EXTERNAL_RERANKER_API_KEY", ""),
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


CHUNK_SIZE = PersistentConfig(
    "CHUNK_SIZE", "rag.chunk_size", int(os.environ.get("CHUNK_SIZE", "1000"))
)
CHUNK_OVERLAP = PersistentConfig(
    "CHUNK_OVERLAP",
    "rag.chunk_overlap",
    int(os.environ.get("CHUNK_OVERLAP", "100")),
)

DEFAULT_RAG_TEMPLATE = """### Task:
Respond to the user query using the provided context, incorporating inline citations in the format [id] **only when the <source> tag includes an explicit id attribute** (e.g., <source id="1">).

### Guidelines:
- If you don't know the answer, clearly state that.
- If uncertain, ask the user for clarification.
- Respond in the same language as the user's query.
- If the context is unreadable or of poor quality, inform the user and provide the best possible answer.
- If the answer isn't present in the context but you possess the knowledge, explain this to the user and provide the answer using your own understanding.
- **Only include inline citations using [id] (e.g., [1], [2]) when the <source> tag includes an id attribute.**
- Do not cite if the <source> tag does not contain an id attribute.
- Do not use XML tags in your response.
- Ensure citations are concise and directly related to the information provided.

### Example of Citation:
If the user asks about a specific topic and the information is found in a source with a provided id attribute, the response should include the citation like in the following example:
* "According to the study, the proposed method increases efficiency by 20% [1]."

### Output:
Provide a clear and direct response to the user's query, including inline citations in the format [id] only when the <source> tag with id attribute is present in the context.

<context>
{{CONTEXT}}
</context>

<user_query>
{{QUERY}}
</user_query>
"""

RAG_TEMPLATE = PersistentConfig(
    "RAG_TEMPLATE",
    "rag.template",
    os.environ.get("RAG_TEMPLATE", DEFAULT_RAG_TEMPLATE),
)

RAG_OPENAI_API_BASE_URL = PersistentConfig(
    "RAG_OPENAI_API_BASE_URL",
    "rag.openai_api_base_url",
    os.getenv("RAG_OPENAI_API_BASE_URL", OPENAI_API_BASE_URL),
)
RAG_OPENAI_API_KEY = PersistentConfig(
    "RAG_OPENAI_API_KEY",
    "rag.openai_api_key",
    os.getenv("RAG_OPENAI_API_KEY", OPENAI_API_KEY),
)

RAG_AZURE_OPENAI_BASE_URL = PersistentConfig(
    "RAG_AZURE_OPENAI_BASE_URL",
    "rag.azure_openai.base_url",
    os.getenv("RAG_AZURE_OPENAI_BASE_URL", ""),
)
RAG_AZURE_OPENAI_API_KEY = PersistentConfig(
    "RAG_AZURE_OPENAI_API_KEY",
    "rag.azure_openai.api_key",
    os.getenv("RAG_AZURE_OPENAI_API_KEY", ""),
)
RAG_AZURE_OPENAI_API_VERSION = PersistentConfig(
    "RAG_AZURE_OPENAI_API_VERSION",
    "rag.azure_openai.api_version",
    os.getenv("RAG_AZURE_OPENAI_API_VERSION", ""),
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


####################################
# Web Search (RAG)
####################################

ENABLE_WEB_SEARCH = PersistentConfig(
    "ENABLE_WEB_SEARCH",
    "rag.web.search.enable",
    os.getenv("ENABLE_WEB_SEARCH", "False").lower() == "true",
)

WEB_SEARCH_ENGINE = PersistentConfig(
    "WEB_SEARCH_ENGINE",
    "rag.web.search.engine",
    os.getenv("WEB_SEARCH_ENGINE", ""),
)

BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL = PersistentConfig(
    "BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL",
    "rag.web.search.bypass_embedding_and_retrieval",
    os.getenv("BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL", "False").lower() == "true",
)


BYPASS_WEB_SEARCH_WEB_LOADER = PersistentConfig(
    "BYPASS_WEB_SEARCH_WEB_LOADER",
    "rag.web.search.bypass_web_loader",
    os.getenv("BYPASS_WEB_SEARCH_WEB_LOADER", "False").lower() == "true",
)

WEB_SEARCH_RESULT_COUNT = PersistentConfig(
    "WEB_SEARCH_RESULT_COUNT",
    "rag.web.search.result_count",
    int(os.getenv("WEB_SEARCH_RESULT_COUNT", "3")),
)


# You can provide a list of your own websites to filter after performing a web search.
# This ensures the highest level of safety and reliability of the information sources.
WEB_SEARCH_DOMAIN_FILTER_LIST = PersistentConfig(
    "WEB_SEARCH_DOMAIN_FILTER_LIST",
    "rag.web.search.domain.filter_list",
    [
        # "wikipedia.com",
        # "wikimedia.org",
        # "wikidata.org",
    ],
)

WEB_SEARCH_CONCURRENT_REQUESTS = PersistentConfig(
    "WEB_SEARCH_CONCURRENT_REQUESTS",
    "rag.web.search.concurrent_requests",
    int(os.getenv("WEB_SEARCH_CONCURRENT_REQUESTS", "10")),
)


WEB_LOADER_ENGINE = PersistentConfig(
    "WEB_LOADER_ENGINE",
    "rag.web.loader.engine",
    os.environ.get("WEB_LOADER_ENGINE", ""),
)

ENABLE_WEB_LOADER_SSL_VERIFICATION = PersistentConfig(
    "ENABLE_WEB_LOADER_SSL_VERIFICATION",
    "rag.web.loader.ssl_verification",
    os.environ.get("ENABLE_WEB_LOADER_SSL_VERIFICATION", "True").lower() == "true",
)

WEB_SEARCH_TRUST_ENV = PersistentConfig(
    "WEB_SEARCH_TRUST_ENV",
    "rag.web.search.trust_env",
    os.getenv("WEB_SEARCH_TRUST_ENV", "False").lower() == "true",
)


SEARXNG_QUERY_URL = PersistentConfig(
    "SEARXNG_QUERY_URL",
    "rag.web.search.searxng_query_url",
    os.getenv("SEARXNG_QUERY_URL", ""),
)

YACY_QUERY_URL = PersistentConfig(
    "YACY_QUERY_URL",
    "rag.web.search.yacy_query_url",
    os.getenv("YACY_QUERY_URL", ""),
)

YACY_USERNAME = PersistentConfig(
    "YACY_USERNAME",
    "rag.web.search.yacy_username",
    os.getenv("YACY_USERNAME", ""),
)

YACY_PASSWORD = PersistentConfig(
    "YACY_PASSWORD",
    "rag.web.search.yacy_password",
    os.getenv("YACY_PASSWORD", ""),
)

GOOGLE_PSE_API_KEY = PersistentConfig(
    "GOOGLE_PSE_API_KEY",
    "rag.web.search.google_pse_api_key",
    os.getenv("GOOGLE_PSE_API_KEY", ""),
)

GOOGLE_PSE_ENGINE_ID = PersistentConfig(
    "GOOGLE_PSE_ENGINE_ID",
    "rag.web.search.google_pse_engine_id",
    os.getenv("GOOGLE_PSE_ENGINE_ID", ""),
)

BRAVE_SEARCH_API_KEY = PersistentConfig(
    "BRAVE_SEARCH_API_KEY",
    "rag.web.search.brave_search_api_key",
    os.getenv("BRAVE_SEARCH_API_KEY", ""),
)

KAGI_SEARCH_API_KEY = PersistentConfig(
    "KAGI_SEARCH_API_KEY",
    "rag.web.search.kagi_search_api_key",
    os.getenv("KAGI_SEARCH_API_KEY", ""),
)

MOJEEK_SEARCH_API_KEY = PersistentConfig(
    "MOJEEK_SEARCH_API_KEY",
    "rag.web.search.mojeek_search_api_key",
    os.getenv("MOJEEK_SEARCH_API_KEY", ""),
)

BOCHA_SEARCH_API_KEY = PersistentConfig(
    "BOCHA_SEARCH_API_KEY",
    "rag.web.search.bocha_search_api_key",
    os.getenv("BOCHA_SEARCH_API_KEY", ""),
)

SERPSTACK_API_KEY = PersistentConfig(
    "SERPSTACK_API_KEY",
    "rag.web.search.serpstack_api_key",
    os.getenv("SERPSTACK_API_KEY", ""),
)

SERPSTACK_HTTPS = PersistentConfig(
    "SERPSTACK_HTTPS",
    "rag.web.search.serpstack_https",
    os.getenv("SERPSTACK_HTTPS", "True").lower() == "true",
)

SERPER_API_KEY = PersistentConfig(
    "SERPER_API_KEY",
    "rag.web.search.serper_api_key",
    os.getenv("SERPER_API_KEY", ""),
)

SERPLY_API_KEY = PersistentConfig(
    "SERPLY_API_KEY",
    "rag.web.search.serply_api_key",
    os.getenv("SERPLY_API_KEY", ""),
)

JINA_API_KEY = PersistentConfig(
    "JINA_API_KEY",
    "rag.web.search.jina_api_key",
    os.getenv("JINA_API_KEY", ""),
)

SEARCHAPI_API_KEY = PersistentConfig(
    "SEARCHAPI_API_KEY",
    "rag.web.search.searchapi_api_key",
    os.getenv("SEARCHAPI_API_KEY", ""),
)

SEARCHAPI_ENGINE = PersistentConfig(
    "SEARCHAPI_ENGINE",
    "rag.web.search.searchapi_engine",
    os.getenv("SEARCHAPI_ENGINE", ""),
)

SERPAPI_API_KEY = PersistentConfig(
    "SERPAPI_API_KEY",
    "rag.web.search.serpapi_api_key",
    os.getenv("SERPAPI_API_KEY", ""),
)

SERPAPI_ENGINE = PersistentConfig(
    "SERPAPI_ENGINE",
    "rag.web.search.serpapi_engine",
    os.getenv("SERPAPI_ENGINE", ""),
)

BING_SEARCH_V7_ENDPOINT = PersistentConfig(
    "BING_SEARCH_V7_ENDPOINT",
    "rag.web.search.bing_search_v7_endpoint",
    os.environ.get(
        "BING_SEARCH_V7_ENDPOINT", "https://api.bing.microsoft.com/v7.0/search"
    ),
)

BING_SEARCH_V7_SUBSCRIPTION_KEY = PersistentConfig(
    "BING_SEARCH_V7_SUBSCRIPTION_KEY",
    "rag.web.search.bing_search_v7_subscription_key",
    os.environ.get("BING_SEARCH_V7_SUBSCRIPTION_KEY", ""),
)

EXA_API_KEY = PersistentConfig(
    "EXA_API_KEY",
    "rag.web.search.exa_api_key",
    os.getenv("EXA_API_KEY", ""),
)

PERPLEXITY_API_KEY = PersistentConfig(
    "PERPLEXITY_API_KEY",
    "rag.web.search.perplexity_api_key",
    os.getenv("PERPLEXITY_API_KEY", ""),
)

PERPLEXITY_MODEL = PersistentConfig(
    "PERPLEXITY_MODEL",
    "rag.web.search.perplexity_model",
    os.getenv("PERPLEXITY_MODEL", "sonar"),
)

PERPLEXITY_SEARCH_CONTEXT_USAGE = PersistentConfig(
    "PERPLEXITY_SEARCH_CONTEXT_USAGE",
    "rag.web.search.perplexity_search_context_usage",
    os.getenv("PERPLEXITY_SEARCH_CONTEXT_USAGE", "medium"),
)

SOUGOU_API_SID = PersistentConfig(
    "SOUGOU_API_SID",
    "rag.web.search.sougou_api_sid",
    os.getenv("SOUGOU_API_SID", ""),
)

SOUGOU_API_SK = PersistentConfig(
    "SOUGOU_API_SK",
    "rag.web.search.sougou_api_sk",
    os.getenv("SOUGOU_API_SK", ""),
)

TAVILY_API_KEY = PersistentConfig(
    "TAVILY_API_KEY",
    "rag.web.search.tavily_api_key",
    os.getenv("TAVILY_API_KEY", ""),
)

TAVILY_EXTRACT_DEPTH = PersistentConfig(
    "TAVILY_EXTRACT_DEPTH",
    "rag.web.search.tavily_extract_depth",
    os.getenv("TAVILY_EXTRACT_DEPTH", "basic"),
)

PLAYWRIGHT_WS_URL = PersistentConfig(
    "PLAYWRIGHT_WS_URL",
    "rag.web.loader.playwright_ws_url",
    os.environ.get("PLAYWRIGHT_WS_URL", ""),
)

PLAYWRIGHT_TIMEOUT = PersistentConfig(
    "PLAYWRIGHT_TIMEOUT",
    "rag.web.loader.playwright_timeout",
    int(os.environ.get("PLAYWRIGHT_TIMEOUT", "10000")),
)

FIRECRAWL_API_KEY = PersistentConfig(
    "FIRECRAWL_API_KEY",
    "rag.web.loader.firecrawl_api_key",
    os.environ.get("FIRECRAWL_API_KEY", ""),
)

FIRECRAWL_API_BASE_URL = PersistentConfig(
    "FIRECRAWL_API_BASE_URL",
    "rag.web.loader.firecrawl_api_url",
    os.environ.get("FIRECRAWL_API_BASE_URL", "https://api.firecrawl.dev"),
)

EXTERNAL_WEB_SEARCH_URL = PersistentConfig(
    "EXTERNAL_WEB_SEARCH_URL",
    "rag.web.search.external_web_search_url",
    os.environ.get("EXTERNAL_WEB_SEARCH_URL", ""),
)

EXTERNAL_WEB_SEARCH_API_KEY = PersistentConfig(
    "EXTERNAL_WEB_SEARCH_API_KEY",
    "rag.web.search.external_web_search_api_key",
    os.environ.get("EXTERNAL_WEB_SEARCH_API_KEY", ""),
)

EXTERNAL_WEB_LOADER_URL = PersistentConfig(
    "EXTERNAL_WEB_LOADER_URL",
    "rag.web.loader.external_web_loader_url",
    os.environ.get("EXTERNAL_WEB_LOADER_URL", ""),
)

EXTERNAL_WEB_LOADER_API_KEY = PersistentConfig(
    "EXTERNAL_WEB_LOADER_API_KEY",
    "rag.web.loader.external_web_loader_api_key",
    os.environ.get("EXTERNAL_WEB_LOADER_API_KEY", ""),
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
WHISPER_MODEL = PersistentConfig(
    "WHISPER_MODEL",
    "audio.stt.whisper_model",
    os.getenv("WHISPER_MODEL", "base"),
)

WHISPER_MODEL_DIR = os.getenv("WHISPER_MODEL_DIR", f"{CACHE_DIR}/whisper/models")
WHISPER_MODEL_AUTO_UPDATE = (
    not OFFLINE_MODE
    and os.environ.get("WHISPER_MODEL_AUTO_UPDATE", "").lower() == "true"
)

WHISPER_VAD_FILTER = PersistentConfig(
    "WHISPER_VAD_FILTER",
    "audio.stt.whisper_vad_filter",
    os.getenv("WHISPER_VAD_FILTER", "False").lower() == "true",
)

WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "").lower() or None

# Add Deepgram configuration
DEEPGRAM_API_KEY = PersistentConfig(
    "DEEPGRAM_API_KEY",
    "audio.stt.deepgram.api_key",
    os.getenv("DEEPGRAM_API_KEY", ""),
)


AUDIO_STT_OPENAI_API_BASE_URL = PersistentConfig(
    "AUDIO_STT_OPENAI_API_BASE_URL",
    "audio.stt.openai.api_base_url",
    os.getenv("AUDIO_STT_OPENAI_API_BASE_URL", OPENAI_API_BASE_URL),
)

AUDIO_STT_OPENAI_API_KEY = PersistentConfig(
    "AUDIO_STT_OPENAI_API_KEY",
    "audio.stt.openai.api_key",
    os.getenv("AUDIO_STT_OPENAI_API_KEY", OPENAI_API_KEY),
)

AUDIO_STT_ENGINE = PersistentConfig(
    "AUDIO_STT_ENGINE",
    "audio.stt.engine",
    os.getenv("AUDIO_STT_ENGINE", ""),
)

AUDIO_STT_MODEL = PersistentConfig(
    "AUDIO_STT_MODEL",
    "audio.stt.model",
    os.getenv("AUDIO_STT_MODEL", ""),
)

AUDIO_STT_AZURE_API_KEY = PersistentConfig(
    "AUDIO_STT_AZURE_API_KEY",
    "audio.stt.azure.api_key",
    os.getenv("AUDIO_STT_AZURE_API_KEY", ""),
)

AUDIO_STT_AZURE_REGION = PersistentConfig(
    "AUDIO_STT_AZURE_REGION",
    "audio.stt.azure.region",
    os.getenv("AUDIO_STT_AZURE_REGION", ""),
)

AUDIO_STT_AZURE_LOCALES = PersistentConfig(
    "AUDIO_STT_AZURE_LOCALES",
    "audio.stt.azure.locales",
    os.getenv("AUDIO_STT_AZURE_LOCALES", ""),
)

AUDIO_STT_AZURE_BASE_URL = PersistentConfig(
    "AUDIO_STT_AZURE_BASE_URL",
    "audio.stt.azure.base_url",
    os.getenv("AUDIO_STT_AZURE_BASE_URL", ""),
)

AUDIO_STT_AZURE_MAX_SPEAKERS = PersistentConfig(
    "AUDIO_STT_AZURE_MAX_SPEAKERS",
    "audio.stt.azure.max_speakers",
    os.getenv("AUDIO_STT_AZURE_MAX_SPEAKERS", ""),
)

AUDIO_TTS_OPENAI_API_BASE_URL = PersistentConfig(
    "AUDIO_TTS_OPENAI_API_BASE_URL",
    "audio.tts.openai.api_base_url",
    os.getenv("AUDIO_TTS_OPENAI_API_BASE_URL", OPENAI_API_BASE_URL),
)
AUDIO_TTS_OPENAI_API_KEY = PersistentConfig(
    "AUDIO_TTS_OPENAI_API_KEY",
    "audio.tts.openai.api_key",
    os.getenv("AUDIO_TTS_OPENAI_API_KEY", OPENAI_API_KEY),
)

AUDIO_TTS_API_KEY = PersistentConfig(
    "AUDIO_TTS_API_KEY",
    "audio.tts.api_key",
    os.getenv("AUDIO_TTS_API_KEY", ""),
)

AUDIO_TTS_ENGINE = PersistentConfig(
    "AUDIO_TTS_ENGINE",
    "audio.tts.engine",
    os.getenv("AUDIO_TTS_ENGINE", ""),
)


AUDIO_TTS_MODEL = PersistentConfig(
    "AUDIO_TTS_MODEL",
    "audio.tts.model",
    os.getenv("AUDIO_TTS_MODEL", "tts-1"),  # OpenAI default model
)

AUDIO_TTS_VOICE = PersistentConfig(
    "AUDIO_TTS_VOICE",
    "audio.tts.voice",
    os.getenv("AUDIO_TTS_VOICE", "alloy"),  # OpenAI default voice
)

AUDIO_TTS_SPLIT_ON = PersistentConfig(
    "AUDIO_TTS_SPLIT_ON",
    "audio.tts.split_on",
    os.getenv("AUDIO_TTS_SPLIT_ON", "punctuation"),
)

AUDIO_TTS_AZURE_SPEECH_REGION = PersistentConfig(
    "AUDIO_TTS_AZURE_SPEECH_REGION",
    "audio.tts.azure.speech_region",
    os.getenv("AUDIO_TTS_AZURE_SPEECH_REGION", ""),
)

AUDIO_TTS_AZURE_SPEECH_BASE_URL = PersistentConfig(
    "AUDIO_TTS_AZURE_SPEECH_BASE_URL",
    "audio.tts.azure.speech_base_url",
    os.getenv("AUDIO_TTS_AZURE_SPEECH_BASE_URL", ""),
)

AUDIO_TTS_AZURE_SPEECH_OUTPUT_FORMAT = PersistentConfig(
    "AUDIO_TTS_AZURE_SPEECH_OUTPUT_FORMAT",
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

LDAP_VALIDATE_CERT = PersistentConfig(
    "LDAP_VALIDATE_CERT",
    "ldap.server.validate_cert",
    os.environ.get("LDAP_VALIDATE_CERT", "True").lower() == "true",
)

LDAP_CIPHERS = PersistentConfig(
    "LDAP_CIPHERS", "ldap.server.ciphers", os.environ.get("LDAP_CIPHERS", "ALL")
)
