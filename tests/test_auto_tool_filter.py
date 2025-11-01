"""
Unit and integration tests for AutoTool Filter

Tests semantic tool matching, similarity scoring, auto-injection,
caching, and performance.
"""

import pytest
import time
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from open_webui.functions.auto_tool_filter import Filter
from open_webui.models.tools import Tools


@pytest.fixture
def autotool_filter():
    """Create AutoTool filter instance"""
    filter_instance = Filter()
    filter_instance.valves.enabled = True
    filter_instance.valves.auto_select = False
    filter_instance.valves.top_k = 3
    filter_instance.valves.similarity_threshold = 0.5
    return filter_instance


@pytest.fixture
def test_user():
    """Mock user for testing"""
    return {
        "id": "test-user-456",
        "email": "test@example.com"
    }


@pytest.fixture
def sample_tools():
    """Create sample tools for testing"""
    return [
        Mock(
            id="weather-tool",
            name="Get Weather",
            meta={"description": "Get current weather for a location"},
            specs=[{"name": "get_weather", "parameters": {}}]
        ),
        Mock(
            id="calculator-tool",
            name="Calculator",
            meta={"description": "Perform mathematical calculations"},
            specs=[{"name": "calculate", "parameters": {}}]
        ),
        Mock(
            id="email-tool",
            name="Send Email",
            meta={"description": "Send email messages to recipients"},
            specs=[{"name": "send_email", "parameters": {}}]
        ),
        Mock(
            id="calendar-tool",
            name="Calendar Manager",
            meta={"description": "Manage calendar events and appointments"},
            specs=[{"name": "add_event", "parameters": {}}]
        ),
        Mock(
            id="translator-tool",
            name="Language Translator",
            meta={"description": "Translate text between languages"},
            specs=[{"name": "translate", "parameters": {}}]
        )
    ]


class TestAutoToolSemanticMatching:
    """Test semantic similarity matching"""

    @pytest.mark.asyncio
    async def test_weather_query_matches_weather_tool(self, autotool_filter, test_user, sample_tools):
        """Test that weather queries match weather tool"""
        with patch.object(Tools, "get_tools_by_user_id", return_value=sample_tools):
            with patch.object(Tools, "get_global_tools", return_value=[]):
                body = {
                    "messages": [
                        {"role": "user", "content": "What's the weather in Paris?"}
                    ]
                }

                result = await autotool_filter.inlet(body, test_user)

                suggestions = result.get("__metadata__", {}).get("tool_suggestions", [])

                assert len(suggestions) > 0
                assert suggestions[0]["name"] == "Get Weather"
                assert suggestions[0]["score"] > 0.5

    @pytest.mark.asyncio
    async def test_math_query_matches_calculator_tool(self, autotool_filter, test_user, sample_tools):
        """Test that math queries match calculator tool"""
        with patch.object(Tools, "get_tools_by_user_id", return_value=sample_tools):
            with patch.object(Tools, "get_global_tools", return_value=[]):
                body = {
                    "messages": [
                        {"role": "user", "content": "Calculate 25 * 47"}
                    ]
                }

                result = await autotool_filter.inlet(body, test_user)

                suggestions = result.get("__metadata__", {}).get("tool_suggestions", [])

                assert len(suggestions) > 0
                assert any("Calculator" in s["name"] for s in suggestions)

    @pytest.mark.asyncio
    async def test_email_query_matches_email_tool(self, autotool_filter, test_user, sample_tools):
        """Test that email queries match email tool"""
        with patch.object(Tools, "get_tools_by_user_id", return_value=sample_tools):
            with patch.object(Tools, "get_global_tools", return_value=[]):
                body = {
                    "messages": [
                        {"role": "user", "content": "Send an email to john@example.com"}
                    ]
                }

                result = await autotool_filter.inlet(body, test_user)

                suggestions = result.get("__metadata__", {}).get("tool_suggestions", [])

                assert any("Email" in s["name"] for s in suggestions)

    @pytest.mark.asyncio
    async def test_multi_match_ranking(self, autotool_filter, test_user, sample_tools):
        """Test that multiple matches are ranked by score"""
        with patch.object(Tools, "get_tools_by_user_id", return_value=sample_tools):
            with patch.object(Tools, "get_global_tools", return_value=[]):
                body = {
                    "messages": [
                        {"role": "user", "content": "Schedule a meeting"}
                    ]
                }

                result = await autotool_filter.inlet(body, test_user)

                suggestions = result.get("__metadata__", {}).get("tool_suggestions", [])

                # Should be ranked by score (descending)
                for i in range(len(suggestions) - 1):
                    assert suggestions[i]["score"] >= suggestions[i + 1]["score"]

    @pytest.mark.asyncio
    async def test_no_match_below_threshold(self, autotool_filter, test_user, sample_tools):
        """Test that tools below similarity threshold are not suggested"""
        autotool_filter.valves.similarity_threshold = 0.9  # Very high threshold

        with patch.object(Tools, "get_tools_by_user_id", return_value=sample_tools):
            with patch.object(Tools, "get_global_tools", return_value=[]):
                body = {
                    "messages": [
                        {"role": "user", "content": "Random unrelated query xyz123"}
                    ]
                }

                result = await autotool_filter.inlet(body, test_user)

                suggestions = result.get("__metadata__", {}).get("tool_suggestions", [])

                # Should have few or no suggestions with high threshold
                assert len(suggestions) <= 1


class TestAutoToolAutoInjection:
    """Test automatic tool injection"""

    @pytest.mark.asyncio
    async def test_auto_inject_enabled(self, autotool_filter, test_user, sample_tools):
        """Test that auto_select injects tools into body"""
        autotool_filter.valves.auto_select = True

        with patch.object(Tools, "get_tools_by_user_id", return_value=sample_tools):
            with patch.object(Tools, "get_global_tools", return_value=[]):
                body = {
                    "messages": [
                        {"role": "user", "content": "What's the weather?"}
                    ]
                }

                result = await autotool_filter.inlet(body, test_user)

                # Tools should be injected
                assert "tools" in result
                assert len(result["tools"]) > 0
                assert result["tools"][0]["name"] == "get_weather"

    @pytest.mark.asyncio
    async def test_auto_inject_disabled(self, autotool_filter, test_user, sample_tools):
        """Test that tools are not injected when auto_select is False"""
        autotool_filter.valves.auto_select = False

        with patch.object(Tools, "get_tools_by_user_id", return_value=sample_tools):
            with patch.object(Tools, "get_global_tools", return_value=[]):
                body = {
                    "messages": [
                        {"role": "user", "content": "What's the weather?"}
                    ]
                }

                result = await autotool_filter.inlet(body, test_user)

                # Tools should not be injected (only suggested)
                assert "tools" not in result or len(result.get("tools", [])) == 0

    @pytest.mark.asyncio
    async def test_top_k_limiting(self, autotool_filter, test_user, sample_tools):
        """Test that only top_k tools are suggested"""
        autotool_filter.valves.top_k = 2

        with patch.object(Tools, "get_tools_by_user_id", return_value=sample_tools):
            with patch.object(Tools, "get_global_tools", return_value=[]):
                body = {
                    "messages": [
                        {"role": "user", "content": "General query"}
                    ]
                }

                result = await autotool_filter.inlet(body, test_user)

                suggestions = result.get("__metadata__", {}).get("tool_suggestions", [])

                # Should respect top_k
                assert len(suggestions) <= 2


class TestAutoToolCaching:
    """Test tool embedding caching"""

    @pytest.mark.asyncio
    async def test_tool_embeddings_cached(self, autotool_filter, test_user, sample_tools):
        """Test that tool embeddings are cached"""
        with patch.object(Tools, "get_tools_by_user_id", return_value=sample_tools):
            with patch.object(Tools, "get_global_tools", return_value=[]):
                body = {
                    "messages": [
                        {"role": "user", "content": "Query 1"}
                    ]
                }

                # First call
                await autotool_filter.inlet(body, test_user)
                initial_cache_size = len(autotool_filter.tool_cache)

                # Second call with same tools
                body["messages"][0]["content"] = "Query 2"
                await autotool_filter.inlet(body, test_user)

                # Cache should not grow (tools already cached)
                assert len(autotool_filter.tool_cache) == initial_cache_size

    @pytest.mark.asyncio
    async def test_cache_hit_performance(self, autotool_filter, test_user, sample_tools):
        """Test that cached embeddings improve performance"""
        with patch.object(Tools, "get_tools_by_user_id", return_value=sample_tools):
            with patch.object(Tools, "get_global_tools", return_value=[]):
                body = {
                    "messages": [
                        {"role": "user", "content": "What's the weather?"}
                    ]
                }

                # First call (cold cache)
                start = time.time()
                await autotool_filter.inlet(body, test_user)
                cold_duration = time.time() - start

                # Second call (warm cache)
                start = time.time()
                await autotool_filter.inlet(body, test_user)
                warm_duration = time.time() - start

                # Warm cache should be faster (or at least not slower)
                assert warm_duration <= cold_duration * 1.2  # Allow 20% variance


class TestAutoToolConfiguration:
    """Test configuration and valves"""

    @pytest.mark.asyncio
    async def test_filter_disabled(self, autotool_filter, test_user, sample_tools):
        """Test that filter can be disabled"""
        autotool_filter.valves.enabled = False

        with patch.object(Tools, "get_tools_by_user_id", return_value=sample_tools):
            with patch.object(Tools, "get_global_tools", return_value=[]):
                body = {
                    "messages": [
                        {"role": "user", "content": "What's the weather?"}
                    ]
                }

                result = await autotool_filter.inlet(body, test_user)

                # Should not process when disabled
                assert "__metadata__" not in result or \
                       "tool_suggestions" not in result.get("__metadata__", {})

    @pytest.mark.asyncio
    async def test_custom_threshold(self, autotool_filter, test_user, sample_tools):
        """Test custom similarity threshold"""
        autotool_filter.valves.similarity_threshold = 0.8  # High threshold

        with patch.object(Tools, "get_tools_by_user_id", return_value=sample_tools):
            with patch.object(Tools, "get_global_tools", return_value=[]):
                body = {
                    "messages": [
                        {"role": "user", "content": "Vague query"}
                    ]
                }

                result = await autotool_filter.inlet(body, test_user)

                suggestions = result.get("__metadata__", {}).get("tool_suggestions", [])

                # All suggestions should meet threshold
                assert all(s["score"] >= 0.8 for s in suggestions)

    @pytest.mark.asyncio
    async def test_large_top_k(self, autotool_filter, test_user, sample_tools):
        """Test top_k larger than available tools"""
        autotool_filter.valves.top_k = 100  # More than available

        with patch.object(Tools, "get_tools_by_user_id", return_value=sample_tools):
            with patch.object(Tools, "get_global_tools", return_value=[]):
                body = {
                    "messages": [
                        {"role": "user", "content": "General query"}
                    ]
                }

                result = await autotool_filter.inlet(body, test_user)

                suggestions = result.get("__metadata__", {}).get("tool_suggestions", [])

                # Should not exceed available tools
                assert len(suggestions) <= len(sample_tools)


class TestAutoToolEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_no_tools_available(self, autotool_filter, test_user):
        """Test handling when no tools are available"""
        with patch.object(Tools, "get_tools_by_user_id", return_value=[]):
            with patch.object(Tools, "get_global_tools", return_value=[]):
                body = {
                    "messages": [
                        {"role": "user", "content": "Any query"}
                    ]
                }

                result = await autotool_filter.inlet(body, test_user)

                # Should handle gracefully
                assert result == body

    @pytest.mark.asyncio
    async def test_no_user_provided(self, autotool_filter):
        """Test handling when user is None"""
        body = {
            "messages": [
                {"role": "user", "content": "Query"}
            ]
        }

        result = await autotool_filter.inlet(body, user=None)

        # Should return unchanged
        assert result == body

    @pytest.mark.asyncio
    async def test_non_user_message(self, autotool_filter, test_user, sample_tools):
        """Test handling non-user messages"""
        with patch.object(Tools, "get_tools_by_user_id", return_value=sample_tools):
            with patch.object(Tools, "get_global_tools", return_value=[]):
                body = {
                    "messages": [
                        {"role": "assistant", "content": "Response"}
                    ]
                }

                result = await autotool_filter.inlet(body, test_user)

                # Should not process assistant messages
                assert "__metadata__" not in result or \
                       "tool_suggestions" not in result.get("__metadata__", {})

    @pytest.mark.asyncio
    async def test_empty_message(self, autotool_filter, test_user, sample_tools):
        """Test handling empty message content"""
        with patch.object(Tools, "get_tools_by_user_id", return_value=sample_tools):
            with patch.object(Tools, "get_global_tools", return_value=[]):
                body = {
                    "messages": [
                        {"role": "user", "content": ""}
                    ]
                }

                result = await autotool_filter.inlet(body, test_user)

                # Should handle gracefully
                assert result == body

    @pytest.mark.asyncio
    async def test_tool_missing_specs(self, autotool_filter, test_user):
        """Test handling tools without specs"""
        broken_tool = Mock(
            id="broken-tool",
            name="Broken Tool",
            meta={"description": "A tool without specs"},
            specs=[]  # Empty specs
        )

        with patch.object(Tools, "get_tools_by_user_id", return_value=[broken_tool]):
            with patch.object(Tools, "get_global_tools", return_value=[]):
                body = {
                    "messages": [
                        {"role": "user", "content": "Test query"}
                    ]
                }

                # Should not crash
                result = await autotool_filter.inlet(body, test_user)

                # Should handle gracefully
                assert "messages" in result


class TestAutoToolPerformance:
    """Test performance and scalability"""

    @pytest.mark.asyncio
    async def test_large_tool_set(self, autotool_filter, test_user):
        """Test performance with 100+ tools"""
        # Create 100 mock tools
        large_tool_set = [
            Mock(
                id=f"tool-{i}",
                name=f"Tool {i}",
                meta={"description": f"Tool for task {i}"},
                specs=[{"name": f"func_{i}"}]
            )
            for i in range(100)
        ]

        with patch.object(Tools, "get_tools_by_user_id", return_value=large_tool_set):
            with patch.object(Tools, "get_global_tools", return_value=[]):
                body = {
                    "messages": [
                        {"role": "user", "content": "Generic query"}
                    ]
                }

                start = time.time()
                result = await autotool_filter.inlet(body, test_user)
                duration = time.time() - start

                # Should complete in reasonable time (<1s)
                assert duration < 1.0

                suggestions = result.get("__metadata__", {}).get("tool_suggestions", [])
                assert len(suggestions) <= autotool_filter.valves.top_k

    @pytest.mark.asyncio
    async def test_long_query_handling(self, autotool_filter, test_user, sample_tools):
        """Test handling very long queries"""
        long_query = "What is the weather like? " * 500  # 2500+ words

        with patch.object(Tools, "get_tools_by_user_id", return_value=sample_tools):
            with patch.object(Tools, "get_global_tools", return_value=[]):
                body = {
                    "messages": [
                        {"role": "user", "content": long_query}
                    ]
                }

                start = time.time()
                result = await autotool_filter.inlet(body, test_user)
                duration = time.time() - start

                # Should handle long queries efficiently
                assert duration < 2.0

                suggestions = result.get("__metadata__", {}).get("tool_suggestions", [])
                assert len(suggestions) > 0

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, autotool_filter, test_user, sample_tools):
        """Test handling concurrent requests"""
        import asyncio

        with patch.object(Tools, "get_tools_by_user_id", return_value=sample_tools):
            with patch.object(Tools, "get_global_tools", return_value=[]):
                bodies = [
                    {
                        "messages": [
                            {"role": "user", "content": f"Query {i}"}
                        ]
                    }
                    for i in range(50)
                ]

                tasks = [autotool_filter.inlet(body, test_user) for body in bodies]

                start = time.time()
                results = await asyncio.gather(*tasks)
                duration = time.time() - start

                # Should handle 50 concurrent requests efficiently
                assert duration < 5.0
                assert all("__metadata__" in r for r in results)


class TestAutoToolIntegration:
    """Integration tests with real embedding model"""

    @pytest.mark.asyncio
    async def test_real_embedding_model(self, autotool_filter, test_user, sample_tools):
        """Test with real sentence-transformers model"""
        # Force model loading
        autotool_filter._load_model()
        assert autotool_filter.model is not None

        with patch.object(Tools, "get_tools_by_user_id", return_value=sample_tools):
            with patch.object(Tools, "get_global_tools", return_value=[]):
                body = {
                    "messages": [
                        {"role": "user", "content": "What's the temperature outside?"}
                    ]
                }

                result = await autotool_filter.inlet(body, test_user)

                suggestions = result.get("__metadata__", {}).get("tool_suggestions", [])

                # Should correctly match weather-related query
                assert len(suggestions) > 0
                assert suggestions[0]["name"] == "Get Weather"

    @pytest.mark.asyncio
    async def test_semantic_similarity_accuracy(self, autotool_filter, test_user, sample_tools):
        """Test semantic similarity accuracy with synonyms"""
        autotool_filter._load_model()

        with patch.object(Tools, "get_tools_by_user_id", return_value=sample_tools):
            with patch.object(Tools, "get_global_tools", return_value=[]):
                # Use synonyms for "weather"
                queries = [
                    "What's the climate like?",
                    "Show me the forecast",
                    "Is it raining?",
                    "Temperature check"
                ]

                for query in queries:
                    body = {
                        "messages": [
                            {"role": "user", "content": query}
                        ]
                    }

                    result = await autotool_filter.inlet(body, test_user)
                    suggestions = result.get("__metadata__", {}).get("tool_suggestions", [])

                    # Weather tool should be in top suggestions
                    assert any("Weather" in s["name"] for s in suggestions[:3])


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
