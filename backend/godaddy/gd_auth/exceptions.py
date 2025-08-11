# Exceptions
from typing import Dict


class InvalidPublicKeyError(Exception):
    """ Exception thrown when there is an invalid public key """

    pass


class SSOServiceError(Exception):
    """ Exception thrown when SSO Service is down """

    pass


class TokenExpiredException(Exception):
    """ Exception thrown denoting how token expired """

    REAUTH = 1  # IAT is expired, and shopper needs to re-auth (e.g. get a new token)
    HBI = 2  # High Business Impact verification expired, token needs to be refreshed via (/v1/hbi)
    VAT = 3  # Verified time has expired, and token needs to refreshed

    EXPIRATION_MESSAGE: Dict[int, str] = {
        REAUTH: "Token has expired, and requires login",
        HBI: "High Business Impact token expired, and needs to be refreshed",
        VAT: "Token verification ('vat') has expired, and needs to be refreshed",
    }

    def __init__(self, code: int) -> None:
        self.code = code
        self.message = self.EXPIRATION_MESSAGE.get(
            self.code, f"Token Expired Code: '{str(self.code)}'"
        )
        (super(TokenExpiredException, self).__init__(self.message))


class SSOClientError(Exception):
    """ Exception thrown when SSO Client fails """

    pass
