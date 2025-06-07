import ssl
import aiohttp
import requests
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from open_webui.config import (
    HTTP_CLIENT_TIMEOUT,
    HTTP_CLIENT_CA_CERT,
    HTTP_CLIENT_CLIENT_CERT,
    HTTP_CLIENT_CLIENT_KEY,
    HTTP_CLIENT_CLIENT_KEY_PASSWORD,
)

ssl_context = ssl.create_default_context()
if HTTP_CLIENT_CLIENT_CERT.value and HTTP_CLIENT_CLIENT_KEY.value:
    if HTTP_CLIENT_CA_CERT.value:
        ssl_context.load_verify_locations(cafile=HTTP_CLIENT_CA_CERT.value)

    ssl_context.load_cert_chain(
        certfile=HTTP_CLIENT_CLIENT_CERT.value,
        keyfile=HTTP_CLIENT_CLIENT_KEY.value,
        password=HTTP_CLIENT_CLIENT_KEY_PASSWORD.value,
    )


class SSLContextAdapter(HTTPAdapter):
    def __init__(self, ssl_context=None, **kwargs):
        self.ssl_context = ssl_context
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        pool_kwargs["ssl_context"] = self.ssl_context
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, **pool_kwargs
        )


request_session = requests.Session()
request_session.mount("https://", SSLContextAdapter(ssl_context=ssl_context))
request_session.timeout = HTTP_CLIENT_TIMEOUT.value
_aiohttp_session = None


async def get_aiohttp_session() -> aiohttp.ClientSession:
    global _aiohttp_session
    if _aiohttp_session is None or _aiohttp_session.closed:
        _aiohttp_session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=ssl_context),
        )

    return _aiohttp_session
