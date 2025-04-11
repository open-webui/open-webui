import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from dotenv import load_dotenv
from feddersen.entra.groups import Cache, UserGroupsRetriever


@pytest.fixture
def user_display_name():
    display_name = os.getenv("USER_DISPLAY_NAME_TO_TEST_PERMISSIONS")
    if not display_name:
        pytest.skip(
            "USER_DISPLAY_NAME_TO_TEST_PERMISSIONS environment variable not set"
        )
    return display_name


@pytest.fixture
def user_email():
    email = os.getenv("USER_MAIL_NOT_DISPLAY_NAME_TO_TEST_PERMISSIONS")
    if not email:
        pytest.skip(
            "USER_MAIL_NOT_DISPLAY_NAME_TO_TEST_PERMISSIONS environment variable not set"
        )
    return email


@pytest.fixture
def user_groups_retriever_fn():
    load_dotenv(Path(__file__).parent.parent / ".env.test", verbose=True)

    # retrning function in order to avoid caching between tests
    def get_retriever():
        return UserGroupsRetriever(
            sso_app_tenant_id=os.getenv("MICROSOFT_CLIENT_TENANT_ID"),
            sso_app_client_id=os.getenv("MICROSOFT_CLIENT_ID"),
            sso_app_client_secret=os.getenv("MICROSOFT_CLIENT_SECRET"),
        )

    return get_retriever


@pytest.mark.integration
class TestGroupRetriever:
    def test_get_user_groups_real(self, user_groups_retriever_fn, user_display_name):
        retriever = user_groups_retriever_fn()
        groups = retriever.get_user_groups(user_display_name)
        assert groups is not None
        assert len(groups) > 0

        assert retriever._user_group_cache[user_display_name]

    def test_get_user_groups_real_with_filter(
        self, user_groups_retriever_fn, user_display_name
    ):
        retriever = user_groups_retriever_fn()
        groups = retriever.get_user_groups(user_display_name, group_prefix="ailio")
        assert groups is not None
        assert len(groups) == 1

        assert retriever._user_group_cache[user_display_name]

    def test_get_user_groups_real_extra_user_lookup(
        self, user_groups_retriever_fn, user_email
    ):
        retriever = user_groups_retriever_fn()

        groups = retriever.get_user_groups(user_email)
        assert groups is not None
        assert len(groups) > 0

        assert retriever._user_group_cache[user_email]

    def test_get_user_groups_not_existing_user(self, user_groups_retriever_fn, caplog):
        retriever = user_groups_retriever_fn()
        with caplog.at_level(logging.WARNING):
            groups = retriever.get_user_groups("test@test.de")

        assert "Could not find" in caplog.text
        assert groups is not None
        assert groups == []

    @pytest.mark.asyncio
    async def test_get_app_token_real(self, user_groups_retriever_fn):
        retriever = user_groups_retriever_fn()
        token = await retriever._get_app_token()
        assert token is not None
        assert len(token) > 0


class TestCache:
    @pytest.fixture
    def cache(
        self,
    ):
        return Cache(cache_duration=3600)

    def test_cache_set_and_get(self, cache):
        cache["test_key"] = "test_value"
        assert cache["test_key"] == "test_value"

    def test_cache_expiration(self, cache):
        cache["test_key"] = "test_value"
        # Simulate time passing
        cache._cache["test_key"] = (
            "test_value",
            datetime.now() - timedelta(seconds=3601),
        )
        assert cache["test_key"] is None

    def test_cache_update(self, cache):
        cache["test_key"] = "test_value"
        cache["test_key"] = "new_value"
        assert cache["test_key"] == "new_value"

    def test_cache_no_expiration(self, cache):
        cache["test_key"] = "test_value"
        # Simulate time passing within cache duration
        cache._cache["test_key"] = (
            "test_value",
            datetime.now() - timedelta(seconds=3599),
        )
        assert cache["test_key"] == "test_value"
