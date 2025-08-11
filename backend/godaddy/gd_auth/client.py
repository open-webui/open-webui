# -*- coding: utf-8 -*-

from abc import abstractmethod
from datetime import datetime, timedelta
from json import loads
from logging import getLogger
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.session import Session

from gd_auth.exceptions import SSOClientError, SSOServiceError

logger = getLogger(__name__)


class AuthTokenClient(object):
    """
    This class implements the core authentication token client from the SSO team.
    """

    def __init__(self, sso_host: str, refresh_min: float) -> None:
        """
        Constructor to initialize token clients.
        refresh_min = How often to refresh SSO Tokens
        sso_host = The root domain of the host. For example, sso.godaddy.com
        """
        self._sso_host = sso_host
        self._refresh_delta = timedelta(minutes=refresh_min)
        self._token = str()
        self._refresh_time = datetime.utcnow()

    @abstractmethod
    def _get_token(self) -> str:
        # must be defined by token type specific classes
        raise NotImplementedError("_get_token")

    def _need_refresh(self) -> bool:
        current_time = datetime.utcnow()
        return current_time >= self._refresh_time

    @property
    def token(self) -> str:
        if not self._token or self._need_refresh():
            logger.info("Fetching new SSO JWT...")
            current_time = datetime.utcnow()
            self._token = self._get_token()
            self._refresh_time = current_time + self._refresh_delta
            logger.info(f"Successfully retrieved SSO JWT, will be cached until {self._refresh_time}")
        return self._token


class AwsIamAuthTokenClient(AuthTokenClient):
    """ Handles AWS SigV4 signing and requesting AWS IAM JWTs """

    def __init__(self,
                 sso_host: str,
                 refresh_min: float = 45.0,
                 primary_region: str = "us-west-2",
                 secondary_region: str = "us-east-1") -> None:
        self._primary_region = primary_region
        self._secondary_region = secondary_region
        self._session_credentials = Session().get_credentials()
        if self._session_credentials is None:
            raise SSOClientError("AWS session credentials not found!")
        (super(AwsIamAuthTokenClient, self).__init__(sso_host=sso_host, refresh_min=refresh_min))

    def _attempt_regional_call(self, region: str) -> str:
        url = f"https://iam-token.{region}.{self._sso_host}/v2/tokens/AWS_IAM"
        try:
            aws_request = AWSRequest(method="POST", url=url)
            sigv4_credentials = self._session_credentials.get_frozen_credentials()
            SigV4Auth(sigv4_credentials, "execute-api", region).add_auth(aws_request)
            aws_auth_headers = dict(aws_request.headers.items())
            sso_request = Request(
                url,
                method="POST",
                headers=aws_auth_headers
            )
            return urlopen(sso_request).read().decode()
        except HTTPError as error:
            if error.code < 500:
                # This is mostly defensive coding for the unit tests, but just in case
                # the HTTPError doesn't have a .fp response body:
                error_body = error.read() if getattr(error, "fp", None) else ""
                error_body = repr(error_body.decode() if error_body else "")
                raise SSOClientError(
                    f"Failed to retrieve IAM Token due to SSO client error: "
                    f"{error.reason} - {error_body}"
                ) from error
            raise SSOServiceError(
                f"Failed to retrieve IAM Token due to SSO service error: {error.reason}"
            ) from error
        except URLError as error:
            raise SSOClientError(f"Bad SSO URL {url} - {error}") from error
        except Exception as error:
            raise SSOClientError(
                f"Failed to retrieve IAM Token due to unknown error: {error}"
            ) from error

    def _get_token(self) -> str:
        try:
            logger.warning(f"Attempting call to SSO IAM Token service in {self._primary_region}...")
            sso_resp = self._attempt_regional_call(self._primary_region)
            return loads(sso_resp)["token"]
        except SSOServiceError as error:
            logger.warning(f"Failed call to SSO IAM Token service in {self._primary_region}: {error}")
            logger.warning(f"Attempting call to SSO IAM Token service in {self._secondary_region}...")
            sso_resp = self._attempt_regional_call(self._secondary_region)
        return loads(sso_resp)["token"]
