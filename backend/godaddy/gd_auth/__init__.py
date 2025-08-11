# -*- coding: utf-8 -*-

DEFAULT_REALM = "idp"


# Helper functions
def cookie_name(realm: str = DEFAULT_REALM) -> str:
    """ Get the name of the SSO/CAuth cookie """
    return f"auth_{realm}"


def login_url(sso_host: str, realm: str = DEFAULT_REALM) -> str:
    """
    Helper function to get the login url.

    sso_host is the host name (e.g. sso.godaddy.com)
    realm is either "idp", "jomax" or "pass"
    """
    return f"https://{sso_host}/login?realm={realm}"


def logout_url(sso_host: str, realm: str = DEFAULT_REALM) -> str:
    """
    Helper function to get the login out.

    sso_host is the host name (e.g. sso.godaddy.com)
    realm is either "idp", "jomax" or "pass"
    """
    return f"https://{sso_host}/logout?realm={realm}"


def public_cert_url(sso_host: str, public_key_id: str) -> str:
    return f"https://{sso_host}/v1/api/key/{public_key_id}"
