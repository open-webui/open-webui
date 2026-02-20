import asyncio
import json
import time
import logging
from typing import Dict, Set, Union, Optional, Any
from uuid import uuid4

log = logging.getLogger(__name__)

PARENT_WILDCARD = "*"


class ToolApprovalManager:

    def __init__(self):
        self.pending_approvals: Dict[str, asyncio.Event] = {}
        self.approval_results: Dict[str, str] = {}
        self.approval_data: Dict[str, Dict[str, Any]] = {}

        # Nested dict: chat_id -> { parent_tool_id -> set of child function names }
        # A set containing PARENT_WILDCARD ("*") means the entire parent is approved.
        self.always_approved: Dict[str, Dict[str, Set[str]]] = {}

        # YOLO mode: chat_id -> set of function names, or PARENT_WILDCARD for all
        # Same nested structure as always_approved for per-tool YOLO,
        # plus a top-level "all" flag via yolo_all_chats.
        self.yolo_functions: Dict[str, Dict[str, Set[str]]] = {}
        self.yolo_all_chats: Set[str] = set()

    # ---- Approval wait/response (unchanged logic) ----

    async def wait_for_approval(
        self,
        chat_id: str,
        approval_id: str,
        tool_data: Dict[str, Any] = None
    ) -> str:
        event_key = f"{chat_id}:{approval_id}"

        if tool_data:
            self.approval_data[event_key] = tool_data

        event = asyncio.Event()
        self.pending_approvals[event_key] = event

        try:
            await event.wait()
            result = self.approval_results.get(event_key, "denied")
            return result
        finally:
            self.pending_approvals.pop(event_key, None)
            self.approval_results.pop(event_key, None)
            self.approval_data.pop(event_key, None)

    async def handle_approval_response(
        self,
        chat_id: str,
        approval_id: str,
        decision: str
    ):
        event_key = f"{chat_id}:{approval_id}"
        self.approval_results[event_key] = decision

        if event_key in self.pending_approvals:
            self.pending_approvals[event_key].set()
        else:
            log.warning(f"No pending approval found for {event_key}")

    def get_pending_approvals_for_chat(self, chat_id: str) -> Dict[str, Any] | None:
        tools = []

        for event_key in self.pending_approvals.keys():
            if event_key.startswith(f"{chat_id}:"):
                approval_id = event_key.split(":", 1)[1]
                tool_data = self.approval_data.get(event_key, {})

                tools.append({
                    "approval_id": approval_id,
                    "tool_id": tool_data.get("tool_id", "unknown"),
                    "tool_name": tool_data.get("tool_name", "Unknown Tool"),
                    "tool_params": tool_data.get("tool_params", {}),
                    "parent_tool_id": tool_data.get("parent_tool_id", "unknown"),
                })

        if not tools:
            return None

        return {
            "chat_id": chat_id,
            "message_id": "restored",
            "tools": tools,
            "timestamp": int(time.time() * 1000)
        }

    # ---- Auto-approve checks (YOLO first, then always-approved) ----

    def should_auto_approve(self, chat_id: str, function_name: str, parent_tool_id: str) -> bool:
        # YOLO all trumps everything
        if chat_id in self.yolo_all_chats:
            return True

        # Per-tool YOLO (same nested structure as always_approved)
        yolo = self.yolo_functions.get(chat_id)
        if yolo is not None:
            parent_yolo = yolo.get(parent_tool_id)
            if parent_yolo is not None:
                if PARENT_WILDCARD in parent_yolo or function_name in parent_yolo:
                    return True

        # Always-approved
        chat_approvals = self.always_approved.get(chat_id)
        if chat_approvals is not None:
            parent = chat_approvals.get(parent_tool_id)
            if parent is not None:
                if PARENT_WILDCARD in parent or function_name in parent:
                    return True

        return False

    def add_always_approved_function(self, chat_id: str, parent_tool_id: str, function_name: str):
        chat_approvals = self.always_approved.setdefault(chat_id, {})
        children = chat_approvals.setdefault(parent_tool_id, set())
        children.add(function_name)

    def add_always_approved_parent(self, chat_id: str, parent_tool_id: str):
        chat_approvals = self.always_approved.setdefault(chat_id, {})
        chat_approvals[parent_tool_id] = {PARENT_WILDCARD}

    def remove_always_approved_function(self, chat_id: str, parent_tool_id: str, function_name: str):
        chat_approvals = self.always_approved.get(chat_id)
        if chat_approvals is None:
            return
        children = chat_approvals.get(parent_tool_id)
        if children is None:
            return
        children.discard(function_name)
        if not children:
            del chat_approvals[parent_tool_id]
            if not chat_approvals:
                del self.always_approved[chat_id]

    def remove_always_approved_parent(self, chat_id: str, parent_tool_id: str):
        chat_approvals = self.always_approved.get(chat_id)
        if chat_approvals is None:
            return
        chat_approvals.pop(parent_tool_id, None)
        if not chat_approvals:
            del self.always_approved[chat_id]

    def clear_always_approved(self, chat_id: str):
        self.always_approved.pop(chat_id, None)

    def get_always_approved(self, chat_id: str) -> Dict[str, list]:
        """Return always-approved data for a chat as JSON-serializable dict.
        Format: { parent_tool_id: [child_names...] } where ["*"] means parent-level.
        """
        chat_approvals = self.always_approved.get(chat_id, {})
        return {parent: sorted(children) for parent, children in chat_approvals.items()}


    # ---- YOLO mode ----

    def set_yolo_all(self, chat_id: str, enabled: bool):
        if enabled:
            self.yolo_all_chats.add(chat_id)
        else:
            self.yolo_all_chats.discard(chat_id)

    def is_yolo_all(self, chat_id: str) -> bool:
        return chat_id in self.yolo_all_chats

    def set_yolo_function(self, chat_id: str, parent_tool_id: str, function_name: str, enabled: bool):
        chat_yolo = self.yolo_functions.setdefault(chat_id, {})
        children = chat_yolo.setdefault(parent_tool_id, set())
        if enabled:
            children.add(function_name)
        else:
            children.discard(function_name)
            if not children:
                del chat_yolo[parent_tool_id]
                if not chat_yolo:
                    del self.yolo_functions[chat_id]

    def set_yolo_parent(self, chat_id: str, parent_tool_id: str, enabled: bool):
        chat_yolo = self.yolo_functions.setdefault(chat_id, {})
        if enabled:
            chat_yolo[parent_tool_id] = {PARENT_WILDCARD}
        else:
            chat_yolo.pop(parent_tool_id, None)
            if not chat_yolo:
                del self.yolo_functions[chat_id]

    def clear_yolo(self, chat_id: str):
        self.yolo_all_chats.discard(chat_id)
        self.yolo_functions.pop(chat_id, None)

    def get_yolo_status(self, chat_id: str) -> Dict[str, Any]:
        """Return YOLO status for a chat as JSON-serializable dict."""
        return {
            "yolo_all": chat_id in self.yolo_all_chats,
            "yolo_functions": {
                parent: sorted(children)
                for parent, children in self.yolo_functions.get(chat_id, {}).items()
            }
        }


approval_manager = ToolApprovalManager()
