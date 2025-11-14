"""
Message Queue Manager for Open WebUI

Handles queuing of chat messages when a chat is already processing a response.
Messages are stored in Redis (if available) with in-memory fallback.
"""

import json
import logging
import time
from typing import Optional, Dict, Any, List
from redis import asyncio as aioredis

from open_webui.env import REDIS_KEY_PREFIX

log = logging.getLogger(__name__)

# In-memory fallback when Redis is not available
_memory_queue: Dict[str, List[Dict[str, Any]]] = {}


class MessageQueue:
    """Message queue manager for chat completions"""

    def __init__(self, redis: Optional[aioredis.Redis] = None):
        self.redis = redis

    def _get_queue_key(self, chat_id: str) -> str:
        """Get Redis key for chat queue"""
        return f"{REDIS_KEY_PREFIX}:message_queue:{chat_id}"

    async def enqueue(
        self, chat_id: str, message_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add a message to the queue for a chat.

        Args:
            chat_id: Chat identifier
            message_data: Message payload to queue

        Returns:
            Dict with queue_id, position, and timestamp
        """
        queue_id = f"{chat_id}:{int(time.time() * 1000)}"
        queue_item = {
            "queue_id": queue_id,
            "chat_id": chat_id,
            "data": message_data,
            "timestamp": time.time(),
        }

        if self.redis:
            try:
                key = self._get_queue_key(chat_id)
                await self.redis.rpush(key, json.dumps(queue_item))
                # Set TTL of 1 hour to prevent stale queues
                await self.redis.expire(key, 3600)
                position = await self.redis.llen(key)
                log.info(f"✅ Message queued for chat {chat_id}: position {position}")
                return {"queue_id": queue_id, "position": position, "timestamp": queue_item["timestamp"]}
            except Exception as e:
                log.error(f"Redis queue error, falling back to memory: {e}")
                # Fallback to memory
                pass

        # Memory fallback
        if chat_id not in _memory_queue:
            _memory_queue[chat_id] = []
        _memory_queue[chat_id].append(queue_item)
        position = len(_memory_queue[chat_id])
        log.info(f"✅ Message queued in memory for chat {chat_id}: position {position}")
        return {"queue_id": queue_id, "position": position, "timestamp": queue_item["timestamp"]}

    async def dequeue(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """
        Remove and return the next message from the queue.

        Args:
            chat_id: Chat identifier

        Returns:
            Message data or None if queue is empty
        """
        if self.redis:
            try:
                key = self._get_queue_key(chat_id)
                item_json = await self.redis.lpop(key)
                if item_json:
                    item = json.loads(item_json)
                    log.info(f"📤 Dequeued message for chat {chat_id}")
                    return item
                return None
            except Exception as e:
                log.error(f"Redis dequeue error, falling back to memory: {e}")
                # Fallback to memory
                pass

        # Memory fallback
        if chat_id in _memory_queue and _memory_queue[chat_id]:
            item = _memory_queue[chat_id].pop(0)
            if not _memory_queue[chat_id]:
                del _memory_queue[chat_id]
            log.info(f"📤 Dequeued message from memory for chat {chat_id}")
            return item
        return None

    async def get_queue_length(self, chat_id: str) -> int:
        """Get the number of messages in the queue for a chat."""
        if self.redis:
            try:
                key = self._get_queue_key(chat_id)
                length = await self.redis.llen(key)
                return length
            except Exception as e:
                log.error(f"Redis queue length error: {e}")
                pass

        # Memory fallback
        return len(_memory_queue.get(chat_id, []))

    async def get_queue(self, chat_id: str) -> List[Dict[str, Any]]:
        """Get all messages in the queue (without removing them)."""
        if self.redis:
            try:
                key = self._get_queue_key(chat_id)
                items_json = await self.redis.lrange(key, 0, -1)
                return [json.loads(item) for item in items_json]
            except Exception as e:
                log.error(f"Redis get queue error: {e}")
                pass

        # Memory fallback
        return list(_memory_queue.get(chat_id, []))

    async def clear_queue(self, chat_id: str) -> int:
        """Clear all messages from the queue. Returns number of items removed."""
        count = await self.get_queue_length(chat_id)

        if self.redis:
            try:
                key = self._get_queue_key(chat_id)
                await self.redis.delete(key)
                log.info(f"🗑️  Cleared {count} messages from queue for chat {chat_id}")
                return count
            except Exception as e:
                log.error(f"Redis clear queue error: {e}")
                pass

        # Memory fallback
        if chat_id in _memory_queue:
            del _memory_queue[chat_id]
            log.info(f"🗑️  Cleared {count} messages from memory queue for chat {chat_id}")
        return count

    async def remove_from_queue(self, chat_id: str, queue_id: str) -> bool:
        """Remove a specific message from the queue by queue_id."""
        if self.redis:
            try:
                key = self._get_queue_key(chat_id)
                items_json = await self.redis.lrange(key, 0, -1)
                for item_json in items_json:
                    item = json.loads(item_json)
                    if item["queue_id"] == queue_id:
                        await self.redis.lrem(key, 1, item_json)
                        log.info(f"🗑️  Removed message {queue_id} from queue")
                        return True
                return False
            except Exception as e:
                log.error(f"Redis remove from queue error: {e}")
                pass

        # Memory fallback
        if chat_id in _memory_queue:
            original_length = len(_memory_queue[chat_id])
            _memory_queue[chat_id] = [
                item for item in _memory_queue[chat_id] if item["queue_id"] != queue_id
            ]
            if len(_memory_queue[chat_id]) < original_length:
                log.info(f"🗑️  Removed message {queue_id} from memory queue")
                return True
        return False


# Global queue instance
_message_queue: Optional[MessageQueue] = None


def get_message_queue(redis: Optional[aioredis.Redis] = None) -> MessageQueue:
    """Get or create the global message queue instance."""
    global _message_queue
    if _message_queue is None:
        _message_queue = MessageQueue(redis)
    elif redis and _message_queue.redis is None:
        # Update with redis if it becomes available
        _message_queue.redis = redis
    return _message_queue
