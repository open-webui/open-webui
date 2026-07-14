import datetime as dt
import logging

import jwt as pyjwt

log = logging.getLogger(__name__)


def _get_id_token_expiry(token: dict | None) -> int | float | None:
    if not isinstance(token, dict) or not token.get('id_token'):
        return None

    try:
        claims = pyjwt.decode(token['id_token'], options={'verify_signature': False})
        expiry = claims.get('exp')
        if isinstance(expiry, bool) or not isinstance(expiry, (int, float)):
            return None
        return expiry
    except Exception as e:
        log.debug(f'Unable to decode OAuth id_token expiry: {e}')
        return None


def _is_oauth_token_refresh_needed(session, force_refresh: bool = False) -> bool:
    refresh_cutoff = dt.datetime.now() + dt.timedelta(minutes=5)

    if force_refresh or session.expires_at is None or refresh_cutoff >= dt.datetime.fromtimestamp(session.expires_at):
        return True

    id_token_expiry = _get_id_token_expiry(session.token)
    return id_token_expiry is not None and refresh_cutoff.timestamp() >= id_token_expiry
