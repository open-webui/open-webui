"""
title: Content Moderation
author: Open WebUI
author_url: https://github.com/open-webui/open-webui
funding_url: https://github.com/open-webui/open-webui
version: 0.1.0
description: Configurable content moderation supporting keyword matching, regex patterns, and OpenAI-compatible Moderation API.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import re
import logging

log = logging.getLogger(__name__)


class Filter:
    class Valves(BaseModel):
        priority: int = Field(default=1, description="Filter execution priority")
        enabled: bool = Field(default=True, description="Enable content moderation")

        # Action on violation: "block", "flag", "log"
        action: str = Field(
            default="block",
            description="Action on safety policy violation: 'block', 'flag', or 'log'",
            json_schema_extra={
                "input": {
                    "type": "select",
                    "options": [
                        {"value": "block", "label": "Block Request"},
                        {"value": "flag", "label": "Flag Metadata"},
                        {"value": "log", "label": "Log Warning Only"},
                    ],
                }
            },
        )

        # Keyword-based detection
        blocked_keywords: str = Field(
            default="",
            description="Comma-separated list of keywords/phrases to block. Case-insensitive.",
        )
        blocked_patterns: str = Field(
            default="",
            description="Newline-separated regex patterns to block. Case-insensitive.",
        )

        # OpenAI Moderation API
        openai_moderation_enabled: bool = Field(
            default=False,
            description="Use OpenAI-compatible Moderation API for content verification.",
        )
        openai_moderation_url: str = Field(
            default="https://api.openai.com/v1/moderations",
            description="OpenAI-compatible moderation API endpoint URL.",
        )
        openai_api_key: str = Field(
            default="",
            description="API key for the moderation endpoint (optional if self-hosted).",
        )
        moderation_threshold: float = Field(
            default=0.0,
            description="Score threshold (0.0 to 1.0) for custom category flags. Set to 0.0 to use the API's default flags.",
        )
        check_categories: str = Field(
            default="hate,harassment,self-harm,sexual,violence,hate/threatening,harassment/threatening,self-harm/intent,self-harm/instructions,sexual/minors,violence/graphic",
            description="Comma-separated moderation categories to enforce.",
        )

        # Response custom messages
        violation_message: str = Field(
            default="Your message was blocked by content moderation policy.",
            description="Response message returned to the user when content is blocked.",
        )

    def __init__(self):
        self.valves = self.Valves()

    async def inlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """Pre-process: Check user message against moderation rules."""
        if not self.valves.enabled:
            return body

        messages = body.get("messages", [])
        if not messages:
            return body

        # Extract the last user message
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    user_message = content
                elif isinstance(content, list):
                    user_message = " ".join(
                        p.get("text", "")
                        for p in content
                        if isinstance(p, dict) and p.get("type") == "text"
                    )
                break

        if not user_message:
            return body

        # 1. Check keywords
        violation = self._check_keywords(user_message)
        if violation:
            return self._handle_violation(body, violation, __user__)

        # 2. Check regex patterns
        violation = self._check_patterns(user_message)
        if violation:
            return self._handle_violation(body, violation, __user__)

        # 3. Check OpenAI Moderation API (if enabled)
        if self.valves.openai_moderation_enabled:
            violation = await self._check_openai_moderation(user_message)
            if violation:
                return self._handle_violation(body, violation, __user__)

        return body

    def _check_keywords(self, text: str) -> Optional[str]:
        """Check text against blocked keywords."""
        if not self.valves.blocked_keywords:
            return None

        # Clean and filter keywords
        keywords = [
            k.strip().lower()
            for k in self.valves.blocked_keywords.split(",")
            if k.strip()
        ]
        text_lower = text.lower()

        for keyword in keywords:
            if keyword in text_lower:
                return f"Blocked keyword detected: '{keyword}'"
        return None

    def _check_patterns(self, text: str) -> Optional[str]:
        """Check text against blocked regex patterns."""
        if not self.valves.blocked_patterns:
            return None

        patterns = [
            p.strip() for p in self.valves.blocked_patterns.split("\n") if p.strip()
        ]

        for pattern in patterns:
            try:
                if re.search(pattern, text, re.IGNORECASE):
                    return f"Blocked pattern matched: '{pattern}'"
            except re.error as e:
                log.warning(
                    f"Invalid regex pattern in content moderation filter: '{pattern}'. Error: {e}"
                )
        return None

    async def _check_openai_moderation(self, text: str) -> Optional[str]:
        """Check text using OpenAI's Moderation API."""
        import aiohttp

        headers = {
            "Content-Type": "application/json",
        }
        if self.valves.openai_api_key:
            headers["Authorization"] = f"Bearer {self.valves.openai_api_key}"

        ssl_context = None
        try:
            from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL

            ssl_context = AIOHTTP_CLIENT_SESSION_SSL
        except ImportError:
            pass

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.valves.openai_moderation_url,
                    headers=headers,
                    json={"input": text},
                    ssl=ssl_context,
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        log.error(
                            f"Moderation API request failed with status {resp.status}: {error_text}"
                        )
                        return None
                    data = await resp.json()

            results = data.get("results", [{}])[0]
            categories = [
                c.strip().lower()
                for c in self.valves.check_categories.split(",")
                if c.strip()
            ]
            category_scores = results.get("category_scores", {})
            category_flags = results.get("categories", {})

            for category in categories:
                # Support exact category matching
                score = category_scores.get(category, 0.0)
                is_flagged = category_flags.get(category, False)

                # Check custom threshold first (if > 0.0)
                if (
                    self.valves.moderation_threshold > 0.0
                    and score >= self.valves.moderation_threshold
                ):
                    return f"Moderation flag: '{category}' (score {score:.4f} >= threshold {self.valves.moderation_threshold})"
                # Fallback to API default flags if threshold is 0.0
                elif self.valves.moderation_threshold == 0.0 and is_flagged:
                    return f"Moderation flag: '{category}' by API policy threshold (score {score:.4f})"

        except Exception as e:
            log.exception(f"Error during OpenAI moderation API check: {e}")

        return None

    def _handle_violation(
        self, body: dict, reason: str, user: Optional[dict] = None
    ) -> dict:
        """Handle a moderation violation based on configured action."""
        user_id = user.get("id", "unknown") if user else "unknown"
        user_email = user.get("email", "unknown") if user else "unknown"

        log.warning(
            f"Content moderation violation: '{reason}' by user '{user_email}' ({user_id}). Action: {self.valves.action}"
        )

        if self.valves.action == "block":
            raise Exception(self.valves.violation_message)

        elif self.valves.action == "flag":
            # Add safety metadata to body for downstream storage or auditing
            if "metadata" not in body:
                body["metadata"] = {}
            body["metadata"]["content_moderation"] = {
                "flagged": True,
                "reason": reason,
            }

        # For "log" action, we already logged the warning above, so just return
        return body
