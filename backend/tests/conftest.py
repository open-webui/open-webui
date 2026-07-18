import pytest


@pytest.fixture(autouse=True)
def _reset_env_flag():
    """
    Reset ENABLE_FORWARD_CHAT_ID to its default (False) before each test
    so test-to-test leakage of monkeypatched module state is impossible.
    """
    import open_webui.routers.openai as openai_router

    openai_router.ENABLE_FORWARD_CHAT_ID = False
    yield
