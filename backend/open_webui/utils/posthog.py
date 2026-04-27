from open_webui.config import POSTHOG_API_KEY, POSTHOG_HOST

_client = None


def get_client():
    global _client
    if not POSTHOG_API_KEY:
        return None
    if _client is None:
        from posthog import Posthog

        _client = Posthog(api_key=POSTHOG_API_KEY, host=POSTHOG_HOST)
    return _client


def capture(distinct_id: str, event: str, properties: dict = {}):
    client = get_client()
    if client:
        client.capture(distinct_id, event, properties)


def identify(distinct_id: str, properties: dict = {}):
    client = get_client()
    if client:
        client.identify(distinct_id, properties)
