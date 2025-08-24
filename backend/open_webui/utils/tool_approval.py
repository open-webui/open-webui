import asyncio
import json
import time
import logging
from typing import Dict, List, Optional, Any
from uuid import uuid4

log = logging.getLogger(__name__)

class ToolApprovalManager:
    
    def __init__(self):
        self.pending_approvals: Dict[str, asyncio.Event] = {}
        self.approval_results: Dict[str, str] = {}
        self.approval_data: Dict[str, Dict[str, Any]] = {}
        self.auto_approval_chats: Dict[str, bool] = {}
    
    
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
            if event_key in self.pending_approvals:
                del self.pending_approvals[event_key]
            if event_key in self.approval_results:
                del self.approval_results[event_key]
            if event_key in self.approval_data:
                del self.approval_data[event_key]
    
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
        import time
        
        tools = []
        
        for event_key in self.pending_approvals.keys():
            if event_key.startswith(f"{chat_id}:"):
                approval_id = event_key.split(":", 1)[1]
                
                tool_data = self.approval_data.get(event_key, {})
                
                tools.append({
                    "approval_id": approval_id,
                    "tool_id": tool_data.get("tool_id", "unknown"),
                    "tool_name": tool_data.get("tool_name", "Unknown Tool"),
                    "tool_params": tool_data.get("tool_params", {})
                })
        
        if not tools:
            return None
        
        return {
            "chat_id": chat_id,
            "message_id": "restored",
            "tools": tools,
            "timestamp": int(time.time() * 1000)
        }
    
    def set_chat_auto_approval(self, chat_id: str, enabled: bool):
        self.auto_approval_chats[chat_id] = enabled
        self._broadcast_auto_approval_change(chat_id, enabled)
    
    def is_chat_auto_approval(self, chat_id: str) -> bool:
        return self.auto_approval_chats.get(chat_id, False)
    
    def remove_chat_auto_approval(self, chat_id: str):
        if chat_id in self.auto_approval_chats:
            del self.auto_approval_chats[chat_id]
            self._broadcast_auto_approval_change(chat_id, False)
    
    def _broadcast_auto_approval_change(self, chat_id: str, enabled: bool):
        try:
            import asyncio
            from open_webui.socket.main import sio
            
            async def broadcast_change():
                await sio.emit('tool:auto_approval_changed', {
                    'chat_id': chat_id,
                    'enabled': enabled
                })
            
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(broadcast_change())
            except RuntimeError:
                asyncio.create_task(broadcast_change())
            
        except Exception as e:
            log.error(f"Failed to broadcast auto-approval change: {e}")

approval_manager = ToolApprovalManager()