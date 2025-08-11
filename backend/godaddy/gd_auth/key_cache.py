# -*- coding: utf-8 -*-
from typing import Dict, Optional

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey


class PublicKeyCache(object):
    """
    PublicKeyCache implements a simple get/set cache used for caching
    public keys based on an id.

    The key associated with an id never changes.
    """

    def __init__(self) -> None:
        self.cache: Dict[str, RSAPublicKey] = {}

    @classmethod
    def get_cache(cls) -> "PublicKeyCache":
        return _globalCache

    @classmethod
    def reset_cache(cls) -> None:
        global _globalCache
        _globalCache = PublicKeyCache()

    def get(self, key: str) -> Optional[RSAPublicKey]:
        return self.cache.get(key, None)

    def set(self, key: str, rsa_public_key_value: RSAPublicKey) -> None:
        self.cache[key] = rsa_public_key_value

    def __contains__(self, key: str) -> bool:
        return key in self.cache


_globalCache = PublicKeyCache()
