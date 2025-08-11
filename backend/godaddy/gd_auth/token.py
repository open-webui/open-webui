# -*- coding: utf-8 -*-

import json
import logging
from datetime import datetime, timedelta
from ssl import SSLError
from typing import Any, AnyStr, Dict, List, Optional, Type
from urllib.error import HTTPError, URLError

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from gd_auth import public_cert_url
from gd_auth.exceptions import InvalidPublicKeyError, SSOServiceError, TokenExpiredException
from gd_auth.key_cache import PublicKeyCache
from gd_auth.utils import DAY_OLD, EncodingUtils, HOUR_OLD, MINUTE_OLD, safe_get

logger = logging.getLogger(__name__)


class TokenBusinessLevel:
    """ Business Impact Level for JWT expiry determination """

    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class AuthToken:
    """ Base Token class """

    @classmethod
    def payload(cls, raw_token: AnyStr) -> Optional[dict]:
        raw_token_decoded = EncodingUtils.decode_to_utf8(raw_token)
        try:
            raw_payload = raw_token_decoded.split(".")[1]
        except IndexError:
            logger.warning("Improperly structured token")
            return None

        try:
            decoded_payload = EncodingUtils.b64decode(raw_payload)
            string_payload = EncodingUtils.decode_to_utf8(decoded_payload)
            payload_dict = json.loads(string_payload)
        except TypeError:
            logger.warning("Encoding was incorrect")
            return None  # incorrect token again.
        except ValueError:  # includes JSONDecodeError
            return None

        return payload_dict

    @classmethod
    def parse(
        cls,
        raw_token: AnyStr,
        sso_host: str,
        app: str,
        typ: str = "idp",
        level: int = TokenBusinessLevel.NONE,
        accepted_auths: Optional[List[str]] = None,
        public_key_cache: Optional[Any] = None,
        datetime_cls: Optional[Any] = None,
        forced_heartbeat: bool = False,
        raise_for_reason: bool = False,
        filter_by_typ: bool = True,
        client_cert: Optional[str] = None,
        client_cert_key: Optional[str] = None,
    ) -> Optional["BaseAuthToken"]:

        if accepted_auths is None:
            accepted_auths = ["basic"]

        payload_dict = AuthToken.payload(raw_token)
        if not payload_dict:
            return None

        token_type = payload_dict["typ"].lower()
        auth = payload_dict.get("auth", "basic").lower()
        token_cls: Optional[Type["BaseAuthToken"]] = None

        if filter_by_typ and typ != token_type:
            return None

        if token_type in ["jomax", "dc1"]:
            token_cls = EmployeeAuthToken

        elif token_type == "idp" and auth in accepted_auths:
            if auth == "basic":
                token_cls = ShopperAuthToken
            elif auth == "e2s":
                token_cls = E2SDelegationAuthToken
            elif auth == "s2s":
                token_cls = S2SDelegationAuthToken
            elif auth == "e2s2s":
                token_cls = E2S2SDelegationAuthToken
            elif auth == "s2snpr":
                token_cls = S2SNPRDelegationAuthToken
            elif auth == "e2s2snpr":
                token_cls = E2S2SNPRDelegationAuthToken
            elif auth == "cert2s":
                token_cls = Cert2SDelegationAuthToken

        elif token_type == "pass" and auth in accepted_auths:
            if auth == "basic":
                token_cls = PassAuthToken
            elif auth == "s2p":
                token_cls = S2PDelegationAuthToken
            elif auth == "e2p":
                token_cls = E2PDelegationAuthToken
            elif auth == "e2s2p":
                token_cls = E2S2PDelegationAuthToken
            elif auth == "s2s2p":
                token_cls = S2S2PDelegationAuthToken
            elif auth == "e2s2s2p":
                token_cls = E2S2S2PDelegationAuthToken

        elif token_type == "cert" and auth in accepted_auths:
            if auth == "basic":
                token_cls = CertAuthToken

        elif typ == "lls_idp":
            token_cls = LLSIDPAuthToken

        elif token_type == 'awsiam':
            if auth == 'basic':
                token_cls = AwsIamAuthToken

        token = token_cls(
            raw_token,  # type: ignore
            payload_dict,
            sso_host,
            app,
            forced_heartbeat,
            public_key_cache,
            datetime_cls,
            client_cert,
            client_cert_key,
        )

        try:
            token._is_valid()
        except InvalidPublicKeyError:
            logger.warning(f"Invalid Public Key requested.  Token: '{token}'")
            return None
        except Exception as err:
            logger.warning(
                f"Token is not valid for unknown reason: '{str(err)}'.  Token: '{str(raw_token)}'"
            )
            return None

        try:
            token.is_expired(level)
        except TokenExpiredException as ex:
            if raise_for_reason:
                raise ex
            else:
                return None

        return token


class BaseAuthToken:
    """
    This class implements the core authentication token from the SSO team. Given a cookie value,
    this object is constructed and then used to verify and process components of the token.
    """

    def __init__(
        self,
        raw_token: AnyStr,
        payload_dict: dict,
        sso_host: str,
        app: str,
        forced_heartbeat: bool = False,
        public_key_cache: Any = None,
        datetime_cls: Optional[Any] = None,
        client_cert: Optional[str] = None,
        client_cert_key: Optional[str] = None,
    ) -> None:
        """
        Constructor to initialize the token.  Parameters are:
        raw_token           = The unparsed cookie
        payload_dict        = The parsed dictionary from the cookie
        sso_host            = The root domain of the host. For example, sso.godaddy.com
        app                 = The app to associate the parsed tokens with
        forced_heartbeat    = Should forced heartbeat be enabled
        public_key_cache    = The functional client for caching the public keys
        datetime_cls        = A functional client for processing date operations (for testing plug)
        client_cert         = Client certificate for Authenticating with the end-point
        client_cert_key     = Client certificate private key
        """
        raw_token_decoded = EncodingUtils.decode_to_utf8(raw_token)
        self.raw_header, self.raw_payload, self.raw_signature = raw_token_decoded.split(".")

        if public_key_cache is None:
            public_key_cache = PublicKeyCache.get_cache()

        if datetime_cls is None:
            datetime_cls = datetime

        self.public_key_cache = public_key_cache
        self._payload_dict = payload_dict
        self.sso_host = sso_host
        self.client_cert = client_cert
        self.client_cert_key = client_cert_key
        self.app = app
        self.forced_heartbeat = forced_heartbeat
        self.datetime_cls = datetime_cls

    @property
    def _decoded_payload(self) -> Optional[bytes]:
        """ Will return the payload of the token as a string. """
        return EncodingUtils.b64decode(self.raw_payload)

    @property
    def _key_id(self) -> Optional[str]:
        try:
            return json.loads(self._header)["kid"]
        except ValueError:
            return None

    @property
    def _header(self) -> str:
        return EncodingUtils.decode_to_utf8(EncodingUtils.b64decode(self.raw_header))

    @property
    def _public_key(self) -> RSAPublicKey:
        key_id = self._key_id
        if key_id is None:
            raise InvalidPublicKeyError()

        self.fetch_certificate()
        key = self.public_key_cache.get(key_id)
        return key

    @property
    def _signature(self) -> Optional[bytes]:
        return EncodingUtils.b64decode(self.raw_signature)

    @property
    def _signing_input(self) -> str:
        return ".".join([self.raw_header, self.raw_payload])

    @property
    def token_type(self) -> str:
        return self.payload["auth"]

    @property
    def payload(self) -> Dict:
        """ Returns a dictionary of the full payload of the token. """
        return self._payload_dict

    @property
    def auth_entity_payload(self) -> Optional[Dict]:
        """
        Returns a dictionary for the portion of the token payload
        corresponding to the authenticating entity.
        """
        return None

    def _is_valid(self) -> None:
        """ Will verify the validity of the auth token. """
        try:
            self._public_key.verify(
                self._signature, self._signing_input.encode(), padding.PKCS1v15(), hashes.SHA256()
            )

        except InvalidSignature:
            logger.warning("Signature was found invalid")
            raise InvalidPublicKeyError

        except (HTTPError, SSLError) as err:
            logger.warning(f"Connection Error: {err.reason}")
            raise

    def _timestamp_expired(self, token_timestamp: int, time_delta: int) -> bool:
        current_time = self.datetime_cls.utcnow()
        expiration = self.datetime_cls.utcfromtimestamp(token_timestamp) + timedelta(
            seconds=time_delta
        )
        return current_time > expiration

    def _is_vat_expired(self) -> bool:
        """
        VAT check now takes precedence in token expiration.
        If forced_heartbeat, tokens need to verified every 5 min, and is checked
        to see if the token has been revoked.  If it is revoked, the token will be rejected.
        """
        payload = self.payload
        # 5 mins for heartbeat, 10 mins if heartbeat off, for parity
        time_policy = 5 * MINUTE_OLD if self.forced_heartbeat else 10 * MINUTE_OLD
        vat_expired = self._timestamp_expired(payload.get("vat", payload.get("iat")), time_policy)

        if vat_expired:
            token_type = payload["typ"].lower()
            auth = payload.get("auth", "basic").lower()
            if token_type == "idp" and auth == "basic" and self.forced_heartbeat:
                raise TokenExpiredException(TokenExpiredException.VAT)

        return vat_expired

    def is_expired(self, level: int) -> bool:
        """
        Token age ranges.  Keep in sync with recommendations here:
        https://confluence.godaddy.com/display/AUTH/Security+Tokens#SecurityTokens-TokenStrength%2FExpiration
        """
        expiration = 0
        payload = self.payload
        per = payload.get("per", False)  # Determine if issued as a permanent cookie

        # Check the vat first!
        vat_expired = self._is_vat_expired()

        # Determine the expiration given the Business/Impact Level
        if level == TokenBusinessLevel.NONE:
            return False

        # Keep in sync with Low Impact scenarios in
        # https://confluence.godaddy.com/display/AUTH/Security+Tokens#SecurityTokens-TokenStrength%2FExpiration
        elif level == TokenBusinessLevel.LOW:
            if hasattr(self, "iam_principal_arn"):
                expiration = 2 * HOUR_OLD
            # Low operations when the cookie is permanent and there is a fresh VAT never expire
            elif per and not vat_expired:
                return False
            elif per or not vat_expired:
                expiration = 180 * DAY_OLD
            else:
                expiration = 24 * HOUR_OLD

        # Keep in sync with Medium Impact scenarios in
        # https://confluence.godaddy.com/display/AUTH/Security+Tokens#SecurityTokens-TokenStrength%2FExpiration
        elif level == TokenBusinessLevel.MEDIUM:
            if hasattr(self, "iam_principal_arn"):
                expiration = 2 * HOUR_OLD
            # Medium operations when cookie isn't impersonated,
            # permanent and is fresh VAT will never expire
            elif hasattr(self, "cert_payload"):
                expiration = DAY_OLD
            elif self.payload.get("del"):
                expiration = 2 * HOUR_OLD
            elif per and not vat_expired:
                return False
            elif per or not vat_expired:
                expiration = 7 * DAY_OLD
            else:
                expiration = 12 * HOUR_OLD

        # Keep in sync with High Impact scenarios in
        # https://confluence.godaddy.com/display/AUTH/Security+Tokens#SecurityTokens-TokenStrength%2FExpiration
        elif level == TokenBusinessLevel.HIGH:
            if hasattr(self, "iam_principal_arn"):
                expiration = 1 * HOUR_OLD
            # High operations are only good for an hour regardless of how the user signed in
            # Token must have an HBI claim, and be current
            elif "hbi" in payload:
                hbi_expired = self._timestamp_expired(payload["hbi"], HOUR_OLD)
                if hbi_expired:
                    raise TokenExpiredException(TokenExpiredException.HBI)
                else:
                    return False
            else:
                # No hbi claim in a HIGH Impact is considered expired
                raise TokenExpiredException(TokenExpiredException.REAUTH)

        else:
            # Not sure how you got here, but consider this an expired token
            raise TokenExpiredException(TokenExpiredException.REAUTH)

        iat_expired = self._timestamp_expired(payload["iat"], expiration)
        if iat_expired:
            raise TokenExpiredException(TokenExpiredException.REAUTH)
        else:
            return False

    def fetch_certificate(self, key_id: Optional[str] = None) -> None:
        key_id = key_id if key_id else self._key_id

        if key_id in self.public_key_cache:
            return  # type: ignore

        try:
            logger.debug(f"Key '{key_id}' not found in cache")
            public_cert = safe_get(
                public_cert_url(self.sso_host, key_id),
                self.app,
                self.forced_heartbeat,
                self.client_cert,
                self.client_cert_key,
            )
        except (HTTPError, URLError) as err:
            if err.code == 403:  # type: ignore
                raise
            raise SSOServiceError()

        if not public_cert or not isinstance(public_cert, dict):
            raise ValueError(f"Invalid public cert requested for key id: '{key_id}'")

        try:
            # Get key from cert not the arg; it is different in certain cases (e.g. key_id=="latest")
            public_cert_id = public_cert["id"]
            # cache the public cert rsa key
            e = EncodingUtils.rsa_encode(public_cert["data"]["e"])
            n = EncodingUtils.rsa_encode(public_cert["data"]["n"])
            public_key_value = rsa.RSAPublicNumbers(e, n).public_key(default_backend())
            self.public_key_cache.set(public_cert_id, public_key_value)
            logger.debug(f"Cached public rsa key for: '{public_cert_id}'")

        except IndexError:
            raise InvalidPublicKeyError(f"Invalid public cert response for key id: '{key_id}'")

        except Exception:
            logger.error(f"Unknown error fetching cert: '{key_id}'")
            raise

    def fetch_latest_certificate(self) -> None:
        """
        Fetch the latest public key, and add to cache.  This can help with lambda warmup.
        Note, that the public cert id will be cached (not key_id = 'latest')
              we will always load a cert when asking for 'latest'
        """
        self.fetch_certificate("latest")


class CertAuthToken(BaseAuthToken):
    """ Certificate (type = cert, auth = basic) """

    @property
    def cert_payload(self) -> Dict:
        return self.payload

    @property
    def subject(self) -> str:
        return self.payload["sbj"]


class EmployeeAuthToken(BaseAuthToken):
    """ Jomax tokens (typ = jomax/dc1, auth = basic) """

    @property
    def auth_entity_payload(self) -> Dict:
        return self.payload

    @property
    def accountname(self) -> str:
        return self.payload["accountName"]


# Shopper auth tokens (type = idp, auth = basic, s2s, e2s, e2s2s, cert2s)
class ShopperBaseAuthToken(BaseAuthToken):
    @property
    def shopper_payload(self) -> Optional[dict]:
        return None

    @property
    def shopper_id(self) -> str:
        return self.shopper_payload["shopperId"]

    @property
    def pl_id(self) -> str:
        return self.shopper_payload["plid"]

    @property
    def firstname(self) -> str:
        return self.shopper_payload["firstname"]

    @property
    def lastname(self) -> str:
        return self.shopper_payload["lastname"]

    @property
    def username(self) -> str:
        return self.shopper_payload["username"]

    @property
    def displayname(self) -> str:
        return self.shopper_payload["disp"]


class ShopperAuthToken(ShopperBaseAuthToken):
    @property
    def shopper_payload(self) -> Dict:
        return self.payload

    @property
    def auth_entity_payload(self) -> Dict:
        return self.payload


class E2SDelegationAuthToken(ShopperBaseAuthToken):
    @property
    def shopper_payload(self) -> Dict:
        return self.payload["e2s"]

    @property
    def auth_entity_payload(self) -> Dict:
        return self.payload["del"]


class Cert2SDelegationAuthToken(ShopperBaseAuthToken):
    @property
    def shopper_payload(self) -> Dict:
        return self.payload["cert2s"]

    @property
    def auth_entity_payload(self) -> Dict:
        return self.payload["del"]


class S2SDelegationAuthToken(ShopperBaseAuthToken):
    @property
    def shopper_payload(self) -> Dict:
        return self.payload["s2s"]

    @property
    def auth_entity_payload(self) -> Dict:
        return self.payload["del"]


class E2S2SDelegationAuthToken(ShopperBaseAuthToken):
    @property
    def shopper_payload(self) -> Dict:
        return self.payload["e2s2s"]

    @property
    def delegate_payload(self) -> Dict:
        return self.payload["del"]["e2s"]

    @property
    def auth_entity_payload(self) -> Dict:
        return self.payload["del"]["del"]


class S2SNPRDelegationAuthToken(ShopperBaseAuthToken):
    @property
    def shopper_payload(self) -> Dict:
        return self.payload["s2snpr"]

    @property
    def auth_entity_payload(self) -> Dict:
        return self.payload["del"]


class E2S2SNPRDelegationAuthToken(ShopperBaseAuthToken):
    @property
    def shopper_payload(self) -> Dict:
        return self.payload["e2s2snpr"]

    @property
    def delegate_payload(self) -> Dict:
        return self.payload["del"]["e2s"]

    @property
    def auth_entity_payload(self) -> Dict:
        return self.payload["del"]["del"]


# Pass Auth tokens (type = pass, auth = [basic, s2p, s2s2p, e2s2p, e2s2s2p, e2p)
class PassBaseAuthToken(BaseAuthToken):
    @property
    def pass_payload(self) -> Optional[dict]:
        return None

    @property
    def username(self) -> str:
        return self.pass_payload["username"]

    @property
    def pl_id(self) -> str:
        return self.pass_payload["plid"]

    @property
    def pass_id(self) -> str:
        return self.pass_payload["passId"]


class PassAuthToken(PassBaseAuthToken):
    @property
    def pass_payload(self) -> Dict:
        return self.payload

    @property
    def auth_entity_payload(self) -> Dict:
        return self.payload


class S2PDelegationAuthToken(PassBaseAuthToken):
    @property
    def pass_payload(self) -> Dict:
        return self.payload["s2p"]

    @property
    def auth_entity_payload(self) -> Dict:
        return self.payload["del"]


class S2S2PDelegationAuthToken(PassBaseAuthToken):
    @property
    def pass_payload(self) -> Dict:
        return self.payload["s2s2p"]

    @property
    def auth_entity_payload(self) -> Dict:
        return self.payload["del"]["del"]


class E2S2PDelegationAuthToken(PassBaseAuthToken):
    @property
    def pass_payload(self) -> Dict:
        return self.payload["e2s2p"]

    @property
    def auth_entity_payload(self) -> Dict:
        return self.payload["del"]["del"]


class E2S2S2PDelegationAuthToken(PassBaseAuthToken):
    @property
    def pass_payload(self) -> Dict:
        return self.payload["e2s2s2p"]

    @property
    def auth_entity_payload(self) -> Dict:
        return self.payload["del"]["del"]["del"]


class E2PDelegationAuthToken(PassBaseAuthToken):
    @property
    def pass_payload(self) -> Dict:
        return self.payload["e2p"]

    @property
    def auth_entity_payload(self) -> Dict:
        return self.payload["del"]


class LLSIDPAuthToken(BaseAuthToken):
    """
    Last Logged in ShopperId (typ = llsidp, auth= basic)
    """

    @property
    def llsidp_payload(self) -> Dict:
        return self.payload

    @property
    def lls_shopper_id(self) -> str:
        return self.payload["lls_shopperId"]

    @property
    def firstname(self) -> str:
        return self.payload["firstname"]

    @property
    def lastname(self) -> str:
        return self.payload["lastname"]

    @property
    def pl_id(self) -> str:
        return self.payload["plid"]

    @property
    def username(self) -> str:
        return self.payload["username"]

    def is_iat_expired(self, seconds: int) -> bool:
        return False


class AwsIamAuthToken(BaseAuthToken):
    """ AWS IAM Principal (typ = awsiam, auth = basic) """

    @property
    def iam_principal_arn(self) -> str:
        return self.payload["sub"]
