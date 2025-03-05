import base64
from datetime import datetime, timedelta, timezone
import json
import redis
import uuid
import logging

from open_webui.env import (
    WEBSOCKET_REDIS_AZURE_CREDENTIALS,
    SRC_LOG_LEVELS
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["SOCKET"])

class AzureCredentialService:
    def __init__(self):
        from azure.identity import DefaultAzureCredential
        self.credential = DefaultAzureCredential()
        self.azure_token = { "access_token": None, "expiry_time": None }
        self.resource = "https://redis.azure.com/.default"
        self.get_token()

    # get a token from credential provider, if new token received update azure token cache
    def get_token(self):
        token = self.credential.get_token(self.resource)
        if not token:
            log.error(f"Failed to retrieve Microsoft Entra token for resource: {self.resource}")
            return None
        if token.token != self.azure_token["access_token"]:
            self.azure_token.update({
                'access_token': token.token,
                'expiry_time': token.expires_on
            })
            expires_on = datetime.fromtimestamp(self.azure_token["expiry_time"]).strftime('%Y-%m-%d %H:%M:%S')
            log.info(f"Receive Microsoft Entra token for resource: {self.resource}, expires on: {expires_on}")
        return self.azure_token["access_token"]

    def get_time_to_expire(self):
        if not self.azure_token["expiry_time"]:
            return 0
        time_to_expire = self.azure_token["expiry_time"] - datetime.now(timezone.utc).timestamp() - 300 # 5 mins grace
        return max(time_to_expire, 0)

    def is_expired(self):
        if not self.azure_token["expiry_time"]:
            return True
        expiry_time = datetime.fromtimestamp(self.azure_token["expiry_time"], tz=timezone.utc)
        return datetime.now(timezone.utc) >= (expiry_time - timedelta(minutes=5))

    # extract username from token
    @staticmethod
    def get_username(token):
        parts = token.split('.')
        base64_str = parts[1]

        if len(base64_str) % 4 == 2:
            base64_str += "=="
        elif len(base64_str) % 4 == 3:
            base64_str += "="

        json_bytes = base64.b64decode(base64_str)
        json_str = json_bytes.decode('utf-8')
        jwt = json.loads(json_str)

        return jwt['oid']


# Initialze global Azure credentials provider if enabled
global azure_credential_service
azure_credential_service = None
if WEBSOCKET_REDIS_AZURE_CREDENTIALS:
    azure_credential_service = AzureCredentialService()


class RedisService:

    def __init__(self, redis_url, redis_options={}):
        self.redis_url = redis_url
        self.ssl_ca_certs = redis_options.get("ssl_ca_certs", None)
        self.username = redis_options.get("username", None)
        self.password = redis_options.get("password", None)
        self.init_redis()

    def init_redis(self, get_credentials=False):
        token = None
        if get_credentials and azure_credential_service:
            token = azure_credential_service.get_token()
            self.username = azure_credential_service.get_username(token)
        else:
            token = self.password
        try:
            log.debug(f"redis_url: {self.redis_url}")
            parameters = {
                "url": self.redis_url,
                "decode_responses": True,
                "socket_timeout": 5,
            }
            if self.username and token:
                log.debug(f"redis_username: {self.username}")
                masked_password = f"{token[:3]}***{token[-3:]}" if token else None
                log.debug(f"redis_password: {masked_password}")
                parameters["username"] = self.username
                parameters["password"] = token
            if self.redis_url.startswith("rediss://"):
                log.debug(f"redis_ssl_ca_certs: {self.ssl_ca_certs}")
                parameters["ssl_ca_certs"] = self.ssl_ca_certs
            self.client = redis.Redis.from_url(**parameters)

            if self.client.ping():
                log.info(f"Connected to Redis: {self.redis_url}")
            else:
                log.error(f"Failed to connect to Redis: {self.redis_url}")
                raise e

        except ConnectionError as e:
            log.error(f"Failed to connect to Redis: {self.redis_url} {e}")
            raise e
        except TimeoutError as e:
            log.error(f"Timed out connecting to Redis: {self.redis_url} {e}")
            raise e
        except redis.AuthenticationError as e:
            log.error(f"Authentication failed connecting to Redis: {self.redis_url} {e}")
            raise e
        except Exception as e:
            log.error(f"Failed to connect to Redis: {self.redis_url} {e}")
            raise e

    def get_client(self):
        return self.client

# reinitialize the redis connection if an exception occurs
def reinit_onerror(func):
    def wrapper(*args, **kwargs):
        # Get the instance of the class
        instance = args[0]
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log.exception(f'{func.__name__} error: {e}')
            log.info(f"Re-authenticate and initialize Redis Cache connection")
            instance.redis_service.init_redis(True)
            instance.redis = instance.redis_service.get_client()
            return func(*args, **kwargs)
    return wrapper

class RedisLock:
    def __init__(self, redis_url, lock_name, timeout_secs, **redis_kwargs):
        self.lock_name = lock_name
        self.lock_id = str(uuid.uuid4())
        self.timeout_secs = timeout_secs
        self.lock_obtained = False
        self.redis_service = RedisService(redis_url, **redis_kwargs)
        self.redis = self.redis_service.get_client()

    @reinit_onerror
    def aquire_lock(self):
        # nx=True will only set this key if it _hasn't_ already been set
        self.lock_obtained = self.redis.set(
            self.lock_name, self.lock_id, nx=True, ex=self.timeout_secs
        )
        return self.lock_obtained

    @reinit_onerror
    def renew_lock(self):
        # xx=True will only set this key if it _has_ already been set
        return self.redis.set(
            self.lock_name, self.lock_id, xx=True, ex=self.timeout_secs
        )

    @reinit_onerror
    def release_lock(self):
        lock_value = self.redis.get(self.lock_name)
        if lock_value and lock_value == self.lock_id:
            self.redis.delete(self.lock_name)


class RedisDict:
    def __init__(self, name, redis_url, **redis_kwargs):
        self.name = name
        self.redis_service = RedisService(redis_url, **redis_kwargs)
        self.redis = self.redis_service.get_client()

    @reinit_onerror
    def __setitem__(self, key, value):
        serialized_value = json.dumps(value)
        self.redis.hset(self.name, key, serialized_value)

    @reinit_onerror
    def __getitem__(self, key):
        value = self.redis.hget(self.name, key)
        if value is None:
            raise KeyError(key)
        return json.loads(value)

    @reinit_onerror
    def __delitem__(self, key):
        result = self.redis.hdel(self.name, key)
        if result == 0:
            raise KeyError(key)

    @reinit_onerror
    def __contains__(self, key):
        return self.redis.hexists(self.name, key)

    @reinit_onerror
    def __len__(self):
        return self.redis.hlen(self.name)

    @reinit_onerror
    def keys(self):
        return self.redis.hkeys(self.name)

    @reinit_onerror
    def values(self):
        return [json.loads(v) for v in self.redis.hvals(self.name)]

    @reinit_onerror
    def items(self):
        return [(k, json.loads(v)) for k, v in self.redis.hgetall(self.name).items()]

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    @reinit_onerror
    def clear(self):
        self.redis.delete(self.name)

    def update(self, other=None, **kwargs):
        if other is not None:
            for k, v in other.items() if hasattr(other, "items") else other:
                self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]
