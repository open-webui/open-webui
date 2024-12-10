import json
import redis


class RedisDict:
    def __init__(self, name, redis_url):
        self.name = name
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)

    def __setitem__(self, key, value):
        serialized_value = json.dumps(value)
        self.redis.hset(self.name, key, serialized_value)

    def __getitem__(self, key):
        value = self.redis.hget(self.name, key)
        if value is None:
            raise KeyError(key)
        return json.loads(value)

    def __delitem__(self, key):
        result = self.redis.hdel(self.name, key)
        if result == 0:
            raise KeyError(key)

    def __contains__(self, key):
        return self.redis.hexists(self.name, key)

    def __len__(self):
        return self.redis.hlen(self.name)

    def keys(self):
        return self.redis.hkeys(self.name)

    def values(self):
        return [json.loads(v) for v in self.redis.hvals(self.name)]

    def items(self):
        return [(k, json.loads(v)) for k, v in self.redis.hgetall(self.name).items()]

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

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
