"""
Regression tests for the OOM fix: ensures that previously unbounded queries
now correctly respect limit/skip and do NOT return the full dataset when
a smaller limit is specified.
"""

import pytest
from test.util.abstract_integration_test import AbstractPostgresTest
from test.util.mock_user import mock_webui_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chats(cls, user_id: str, n: int):
    """Insert n minimal chats for the given user and return the list of models."""
    chats = []
    for i in range(n):
        chat = cls.chats.insert_new_chat(
            user_id=user_id,
            form_data=type(
                "ChatForm",
                (),
                {"chat": {"title": f"Chat {i}", "messages": []}, "folder_id": None},
            )(),
        )
        chats.append(chat)
    return chats


# ---------------------------------------------------------------------------
# Chat pagination tests
# ---------------------------------------------------------------------------


class TestGetChatsPagination(AbstractPostgresTest):
    """Verify that Chats.get_chats() honours limit/skip."""

    BASE_PATH = "/api/v1/chats"

    def setup_class(cls):
        super().setup_class()
        from open_webui.models.chats import Chats
        from open_webui.models.users import Users

        cls.chats = Chats
        cls.users = Users

    def setup_method(self):
        super().setup_method()
        self.users.insert_new_user(
            id="u1",
            name="Test User",
            email="test@example.com",
            profile_image_url="/user.png",
            role="user",
        )

    def test_get_chats_limited(self):
        """get_chats(limit=5) must not return more than 5 rows."""
        for i in range(20):
            with mock_webui_user(id="u1"):
                self.fast_api_client.post(
                    self.create_url(""),
                    json={"chat": {"title": f"Chat {i}", "messages": []}, "folder_id": None},
                )

        result = self.chats.get_chats(skip=0, limit=5)
        assert len(result) <= 5, f"Expected ≤5 chats, got {len(result)}"

    def test_get_chats_skip(self):
        """get_chats with skip should return different pages."""
        for i in range(10):
            with mock_webui_user(id="u1"):
                self.fast_api_client.post(
                    self.create_url(""),
                    json={"chat": {"title": f"Chat {i}", "messages": []}, "folder_id": None},
                )

        page1 = self.chats.get_chats(skip=0, limit=5)
        page2 = self.chats.get_chats(skip=5, limit=5)

        ids1 = {c.id for c in page1}
        ids2 = {c.id for c in page2}

        assert len(ids1) > 0
        assert len(ids2) > 0
        # Pages should not overlap
        assert ids1.isdisjoint(ids2), "Page 1 and Page 2 have overlapping IDs"


class TestArchivedChatsPagination(AbstractPostgresTest):
    """Verify that get_archived_chats_by_user_id honours limit/skip."""

    BASE_PATH = "/api/v1/chats"

    def setup_class(cls):
        super().setup_class()
        from open_webui.models.chats import Chats
        from open_webui.models.users import Users

        cls.chats = Chats
        cls.users = Users

    def setup_method(self):
        super().setup_method()
        self.users.insert_new_user(
            id="u1",
            name="Test User",
            email="test@example.com",
            profile_image_url="/user.png",
            role="user",
        )

    def test_archived_chats_limited(self):
        """get_archived_chats_by_user_id(limit=3) must return ≤3 rows."""
        # Create 10 chats and archive them via the API
        for i in range(10):
            with mock_webui_user(id="u1"):
                resp = self.fast_api_client.post(
                    self.create_url(""),
                    json={"chat": {"title": f"Chat {i}", "messages": []}, "folder_id": None},
                )
            chat_id = resp.json()["id"]
            with mock_webui_user(id="u1"):
                self.fast_api_client.post(self.create_url(f"/{chat_id}/archive"))

        result = self.chats.get_archived_chats_by_user_id("u1", skip=0, limit=3)
        assert len(result) <= 3, f"Expected ≤3 archived chats, got {len(result)}"


# ---------------------------------------------------------------------------
# Memory pagination tests
# ---------------------------------------------------------------------------


class TestMemoriesPagination(AbstractPostgresTest):
    """Verify that Memories.get_memories_by_user_id honours limit/skip."""

    BASE_PATH = "/api/v1/memories"

    def setup_class(cls):
        super().setup_class()
        from open_webui.models.memories import Memories
        from open_webui.models.users import Users

        cls.memories = Memories
        cls.users = Users

    def setup_method(self):
        super().setup_method()
        self.users.insert_new_user(
            id="u1",
            name="Test User",
            email="test@example.com",
            profile_image_url="/user.png",
            role="user",
        )

    def test_get_memories_limited(self):
        """get_memories(limit=5) must return ≤5 rows even if DB has more."""
        for i in range(20):
            self.memories.insert_new_memory(user_id="u1", content=f"Memory {i}")

        result = self.memories.get_memories(skip=0, limit=5)
        assert len(result) <= 5, f"Expected ≤5 memories, got {len(result)}"

    def test_get_memories_by_user_id_limited(self):
        """get_memories_by_user_id(limit=5) must return ≤5 rows for the user."""
        for i in range(20):
            self.memories.insert_new_memory(user_id="u1", content=f"Memory {i}")

        result = self.memories.get_memories_by_user_id("u1", skip=0, limit=5)
        assert len(result) <= 5, f"Expected ≤5 memories, got {len(result)}"

    def test_get_memories_pagination_offset(self):
        """get_memories_by_user_id with skip should produce non-overlapping pages."""
        for i in range(12):
            self.memories.insert_new_memory(user_id="u1", content=f"Memory {i}")

        page1 = self.memories.get_memories_by_user_id("u1", skip=0, limit=5)
        page2 = self.memories.get_memories_by_user_id("u1", skip=5, limit=5)

        ids1 = {m.id for m in page1}
        ids2 = {m.id for m in page2}
        assert ids1.isdisjoint(ids2), "Page 1 and Page 2 have overlapping memory IDs"


# ---------------------------------------------------------------------------
# Feedback pagination tests
# ---------------------------------------------------------------------------


class TestFeedbacksPagination(AbstractPostgresTest):
    """Verify that Feedbacks.get_all_feedbacks honours limit/skip."""

    BASE_PATH = "/api/v1/evaluations"

    def setup_class(cls):
        super().setup_class()
        from open_webui.models.feedbacks import Feedbacks, FeedbackForm
        from open_webui.models.users import Users

        cls.feedbacks = Feedbacks
        cls.feedback_form_cls = FeedbackForm
        cls.users = Users

    def setup_method(self):
        super().setup_method()
        self.users.insert_new_user(
            id="u1",
            name="Test User",
            email="test@example.com",
            profile_image_url="/user.png",
            role="user",
        )

    def _make_feedbacks(self, n: int):
        for i in range(n):
            self.feedbacks.insert_new_feedback(
                user_id="u1",
                form_data=self.feedback_form_cls(
                    type="rating",
                    data={"rating": 1, "model_id": f"model-{i}"},
                    meta=None,
                    snapshot=None,
                ),
            )

    def test_get_all_feedbacks_limited(self):
        """get_all_feedbacks(limit=5) must return ≤5 rows."""
        self._make_feedbacks(20)
        result = self.feedbacks.get_all_feedbacks(skip=0, limit=5)
        assert len(result) <= 5, f"Expected ≤5 feedbacks, got {len(result)}"

    def test_get_feedbacks_by_user_limited(self):
        """get_feedbacks_by_user_id(limit=5) must return ≤5 rows."""
        self._make_feedbacks(20)
        result = self.feedbacks.get_feedbacks_by_user_id("u1", skip=0, limit=5)
        assert len(result) <= 5, f"Expected ≤5 user feedbacks, got {len(result)}"

    def test_get_feedbacks_by_type_limited(self):
        """get_feedbacks_by_type(limit=5) must return ≤5 rows."""
        self._make_feedbacks(20)
        result = self.feedbacks.get_feedbacks_by_type("rating", skip=0, limit=5)
        assert len(result) <= 5, f"Expected ≤5 feedbacks by type, got {len(result)}"
