"""
title: AutoTool Filter
description: Automatically suggest relevant tools for user queries using semantic similarity
author: open-webui
version: 1.0.0
requirements: sentence-transformers>=2.2.0,scikit-learn>=1.3.0
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import logging
import numpy as np

log = logging.getLogger(__name__)


class Filter:
    """
    AutoTool Inlet Filter

    Analyzes user queries and automatically suggests/selects the most
    relevant tools using semantic similarity matching.
    """

    class Valves(BaseModel):
        """Configuration for AutoTool filter"""
        enabled: bool = Field(
            default=True,
            description="Enable/disable automatic tool suggestion"
        )
        auto_select: bool = Field(
            default=False,
            description="Automatically inject tools into request (vs just suggest)"
        )
        top_k: int = Field(
            default=3,
            ge=1,
            le=10,
            description="Number of top tools to suggest"
        )
        similarity_threshold: float = Field(
            default=0.5,
            ge=0.0,
            le=1.0,
            description="Minimum similarity score for tool matching"
        )
        model_name: str = Field(
            default="all-MiniLM-L6-v2",
            description="Sentence transformer model to use"
        )
        cache_embeddings: bool = Field(
            default=True,
            description="Cache tool embeddings for performance"
        )

    def __init__(self):
        """Initialize the AutoTool filter"""
        self.valves = self.Valves()
        self.model = None
        self.tool_cache = {}  # Cache for tool embeddings

    def _load_model(self):
        """Lazy load sentence transformer model"""
        if self.model is None:
            try:
                from sentence_transformers import SentenceTransformer

                log.info(f"Loading sentence transformer model: {self.valves.model_name}")
                self.model = SentenceTransformer(self.valves.model_name)
                log.info("Sentence transformer model loaded successfully")

            except Exception as e:
                log.error(f"Failed to load sentence transformer model: {str(e)}")
                raise

    def _get_tool_embedding(self, tool: Any) -> np.ndarray:
        """
        Get or compute embedding for a tool

        Args:
            tool: Tool object with id, name, and meta

        Returns:
            Embedding vector
        """
        tool_id = tool.id

        # Check cache
        if self.valves.cache_embeddings and tool_id in self.tool_cache:
            return self.tool_cache[tool_id]

        # Compute embedding
        tool_description = f"{tool.name}: {tool.meta.get('description', '')}"
        embedding = self.model.encode([tool_description])[0]

        # Cache it
        if self.valves.cache_embeddings:
            self.tool_cache[tool_id] = embedding

        return embedding

    def _compute_similarity(
        self,
        query_embedding: np.ndarray,
        tool_embedding: np.ndarray
    ) -> float:
        """
        Compute cosine similarity between query and tool

        Args:
            query_embedding: Query embedding vector
            tool_embedding: Tool embedding vector

        Returns:
            Similarity score (0-1)
        """
        from sklearn.metrics.pairwise import cosine_similarity

        similarity = cosine_similarity(
            query_embedding.reshape(1, -1),
            tool_embedding.reshape(1, -1)
        )[0][0]

        return float(similarity)

    def _get_available_tools(self, user: dict) -> List[Any]:
        """
        Get all available tools for the user

        Args:
            user: User dict with id

        Returns:
            List of tool objects
        """
        try:
            from open_webui.models.tools import Tools

            # Get user's tools
            user_tools = Tools.get_tools_by_user_id(user["id"])

            # Get global tools
            global_tools = Tools.get_global_tools()

            # Combine and deduplicate
            all_tools = user_tools + global_tools
            seen_ids = set()
            unique_tools = []

            for tool in all_tools:
                if tool.id not in seen_ids:
                    unique_tools.append(tool)
                    seen_ids.add(tool.id)

            return unique_tools

        except Exception as e:
            log.error(f"Failed to get available tools: {str(e)}")
            return []

    def _rank_tools(
        self,
        query: str,
        tools: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        Rank tools by semantic similarity to query

        Args:
            query: User query
            tools: List of available tools

        Returns:
            List of ranked tools with scores
        """
        if not tools or not query.strip():
            return []

        self._load_model()

        # Encode query
        query_embedding = self.model.encode([query])[0]

        # Compute similarities
        tool_scores = []

        for tool in tools:
            try:
                tool_embedding = self._get_tool_embedding(tool)
                similarity = self._compute_similarity(query_embedding, tool_embedding)

                # Filter by threshold
                if similarity >= self.valves.similarity_threshold:
                    tool_scores.append({
                        "tool_id": tool.id,
                        "name": tool.name,
                        "description": tool.meta.get("description", ""),
                        "score": similarity,
                        "spec": tool.specs[0] if tool.specs else None
                    })

            except Exception as e:
                log.error(f"Error processing tool {tool.id}: {str(e)}")
                continue

        # Sort by score (descending)
        tool_scores.sort(key=lambda x: x["score"], reverse=True)

        # Return top k
        return tool_scores[:self.valves.top_k]

    async def inlet(
        self,
        body: dict,
        user: Optional[dict] = None,
        __event_emitter__=None
    ) -> dict:
        """
        Analyze query and suggest relevant tools

        This is the main filter function that processes user queries.

        Args:
            body: Message body containing messages array
            user: User dict with id and other info
            __event_emitter__: Optional event emitter

        Returns:
            Modified body with tool suggestions or injected tools
        """
        # Skip if disabled or no user
        if not self.valves.enabled or not user:
            return body

        try:
            # Extract user query
            messages = body.get("messages", [])
            if not messages:
                return body

            last_message = messages[-1]
            if last_message.get("role") != "user":
                return body

            query = last_message.get("content", "")
            if not query or not query.strip():
                return body

            # Get available tools
            tools = self._get_available_tools(user)
            if not tools:
                log.debug("No tools available for user")
                return body

            # Rank tools by similarity
            ranked_tools = self._rank_tools(query, tools)

            if not ranked_tools:
                # No tools match the query
                body["__metadata__"] = body.get("__metadata__", {})
                body["__metadata__"]["tool_suggestions"] = []
                return body

            # Prepare suggestions for metadata
            suggestions = [
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "score": round(tool["score"], 3)
                }
                for tool in ranked_tools
            ]

            # Add to metadata
            body["__metadata__"] = body.get("__metadata__", {})
            body["__metadata__"]["tool_suggestions"] = suggestions

            # Auto-inject tools if enabled
            if self.valves.auto_select:
                tool_specs = [
                    tool["spec"]
                    for tool in ranked_tools
                    if tool["spec"] is not None
                ]

                if tool_specs:
                    body["tools"] = tool_specs
                    log.info(f"Auto-injected {len(tool_specs)} tools for query")

            # Emit event if available
            if __event_emitter__:
                tool_names = [t["name"] for t in suggestions]
                await __event_emitter__({
                    "type": "status",
                    "data": {
                        "description": f"Suggested tools: {', '.join(tool_names[:2])}",
                        "done": True
                    }
                })

            log.info(f"AutoTool: Suggested {len(suggestions)} tools for user {user['id']}")

        except Exception as e:
            log.error(f"AutoTool error: {str(e)}")
            # Don't fail the request, just log error
            body["__metadata__"] = body.get("__metadata__", {})
            body["__metadata__"]["tool_suggestions"] = []
            body["__metadata__"]["tool_error"] = str(e)

        return body
