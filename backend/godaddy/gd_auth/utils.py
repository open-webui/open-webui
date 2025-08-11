# -*- coding: utf-8 -*-

import base64
import json
import logging
import ssl
import sys
from typing import AnyStr, Dict, Optional
from urllib.error import URLError
from urllib.request import HTTPSHandler, Request, build_opener

import pkg_resources

logger = logging.getLogger(__name__)

# TIME CONSTANTS
MINUTE_OLD = 60
HOUR_OLD = 60 * 60
DAY_OLD = 24 * HOUR_OLD
WEEK_OLD = 7 * DAY_OLD
MONTH_OLD = 30 * DAY_OLD


def safe_get(
    url: str,
    app: str,
    force_heartbeat: bool,
    client_cert: Optional[str] = None,
    client_cert_key: Optional[str] = None,
) -> Dict:
    logger.debug(f"Loading client cert '{client_cert}'")
    user_agent = build_user_agent(app, force_heartbeat)
    # URLErrors might be thrown... so lets try a few times
    retries = 4
    for i in range(retries):  # incase this fails
        try:
            request = Request(url, headers={"User-Agent": user_agent})
            context = ssl.create_default_context()
            if client_cert is not None:
                context.load_cert_chain(client_cert, client_cert_key)

            opener = build_opener(HTTPSHandler(context=context))
            response = opener.open(request).read()
            return json.loads(response.decode())

        except URLError:
            if i == retries - 1:
                logger.error(f"Max retries exceeded. Unable to load client cert '{client_cert}'")
                raise
            logger.debug(f"Retrying load client cert '{client_cert}'")

    # If it hasn't worked yet, give it one more try, else just throw the error
    return json.loads(response.decode())


def build_user_agent(app: str, force_heartbeat: bool) -> str:
    return (
        f"Python{get_python_ver()} PyAuth{get_pyauth_ver()} App{app} Heartbeat{str(force_heartbeat)}"
    )


def get_python_ver() -> str:
    return f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}"


def get_pyauth_ver() -> str:
    return pkg_resources.get_distribution("gd-auth").version


class EncodingUtils:
    @staticmethod
    def b64decode(payload: AnyStr) -> Optional[bytes]:
        if not payload:
            return None

        decoded_payload = EncodingUtils.decode_to_utf8(payload)
        padded_payload = decoded_payload.ljust(len(payload) + (len(payload) % 4), "=")
        return base64.urlsafe_b64decode(padded_payload.encode("utf-8"))

    @staticmethod
    def rsa_encode(encode_input: AnyStr) -> int:
        return int(base64.b16encode(EncodingUtils.b64decode(encode_input)), 16)

    @staticmethod
    def decode_to_utf8(text: AnyStr) -> str:
        if type(text) == str:
            return text  # type: ignore
        else:
            try:
                result = text.decode()  # type: ignore
            except AttributeError:
                result = str(text, encoding="utf-8")  # type: ignore
            return result
