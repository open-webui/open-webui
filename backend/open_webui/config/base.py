import json
import logging
import os
from typing import Generic, Optional, TypeVar, Union
from open_webui.config.database import (
    get_config,
    save_to_db
)
from open_webui.utils.redis import get_redis_connection
import redis

log = logging.getLogger(__name__)


PERSISTENT_CONFIG_REGISTRY = []

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

ENABLE_OAUTH_PERSISTENT_CONFIG = (
    os.environ.get("ENABLE_OAUTH_PERSISTENT_CONFIG", "False").lower() == "true"
)

class PersistentConfig(Generic[T]):
    def __init__(self, env_name: str, config_path: str, env_value: T):
        self.env_name = env_name
        self.config_path = config_path
        self.env_value = env_value
        self.config_value = get_config_value(config_path)

        if self.config_value is not None and ENABLE_PERSISTENT_CONFIG:
            if (
                self.config_path.startswith("oauth.")
                and not ENABLE_OAUTH_PERSISTENT_CONFIG
            ):
                log.info(
                    f"Skipping loading of '{env_name}' as OAuth persistent config is disabled"
                )
                self.value = env_value
            else:
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
    _redis: Union[redis.Redis, redis.cluster.RedisCluster] = None
    _redis_key_prefix: str

    def __init__(
        self,
        redis_url: Optional[str] = None,
        redis_sentinels: Optional[list] = [],
        redis_cluster: Optional[bool] = False,
        redis_key_prefix: str = "open-webui",
    ):
        super().__setattr__("_state", {})
        super().__setattr__("_redis_key_prefix", redis_key_prefix)
        if redis_url:
            super().__setattr__(
                "_redis",
                get_redis_connection(
                    redis_url,
                    redis_sentinels,
                    redis_cluster,
                    decode_responses=True,
                ),
            )

    def __setattr__(self, key, value):
        if isinstance(value, PersistentConfig):
            self._state[key] = value
        else:
            self._state[key].value = value
            self._state[key].save()

            if self._redis:
                redis_key = f"{self._redis_key_prefix}:config:{key}"
                self._redis.set(redis_key, json.dumps(self._state[key].value))

    def __getattr__(self, key):
        if key not in self._state:
            raise AttributeError(f"Config key '{key}' not found")

        # If Redis is available, check for an updated value
        if self._redis:
            redis_key = f"{self._redis_key_prefix}:config:{key}"
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
