"""
Heartbeat utility for streaming responses.
Sends periodic heartbeat events to indicate connection is alive during model reasoning.

This module is designed for minimal intrusion - easy to add/remove during upstream merges.
"""
import asyncio
import time
import json
import logging
from typing import AsyncIterator
import aiohttp

log = logging.getLogger(__name__)

# Heartbeat interval in seconds
HEARTBEAT_INTERVAL = 5.0


def create_heartbeat_event() -> bytes:
    """Create a heartbeat SSE event."""
    data = {
        "type": "heartbeat",
        "status": "model_thinking",
        "timestamp": int(time.time())
    }
    return f"data: {json.dumps(data)}\n".encode("utf-8")


class HeartbeatStreamWrapper:
    """
    Wrapper around aiohttp.StreamReader that adds heartbeat support.
    
    Provides iter_chunks() method compatible with stream_chunks_handler.
    When no data is received within the heartbeat interval, yields a heartbeat event
    to keep the connection alive and inform the frontend that the model is still thinking.
    
    Usage:
        wrapped = HeartbeatStreamWrapper(r.content)
        stream_chunks_handler(wrapped)  # Works because we have iter_chunks()
    """
    
    def __init__(self, stream: aiohttp.StreamReader, heartbeat_interval: float = HEARTBEAT_INTERVAL):
        self._stream = stream
        self._heartbeat_interval = heartbeat_interval
    
    def iter_chunks(self):
        """
        Return an async generator that yields (data, end_of_chunk) tuples.
        Compatible with aiohttp.StreamReader.iter_chunks() interface.
        Injects heartbeat events when idle.
        """
        return self._iter_chunks_with_heartbeat()
    
    async def _iter_chunks_with_heartbeat(self) -> AsyncIterator[tuple[bytes, bool]]:
        """Internal async generator that wraps iter_chunks with heartbeat."""
        original_iter = self._stream.iter_chunks()
        it = original_iter.__aiter__()
        
        while True:
            try:
                # Wait for next chunk with timeout
                chunk = await asyncio.wait_for(
                    it.__anext__(),
                    timeout=self._heartbeat_interval
                )
                yield chunk
            except StopAsyncIteration:
                # Stream ended normally
                break
            except asyncio.TimeoutError:
                # No data within interval - send heartbeat
                log.debug("💭 心跳信号 - 模型正在思考中...")
                yield (create_heartbeat_event(), False)
            except Exception as e:
                log.debug(f"Stream error: {e}")
                break
    
    # Support direct async iteration (for when stream is returned directly)
    def __aiter__(self):
        return self._direct_iter()
    
    async def _direct_iter(self) -> AsyncIterator[bytes]:
        """Direct async iteration with heartbeat support."""
        it = self._stream.__aiter__()
        
        while True:
            try:
                chunk = await asyncio.wait_for(
                    it.__anext__(),
                    timeout=self._heartbeat_interval
                )
                yield chunk
            except StopAsyncIteration:
                break
            except asyncio.TimeoutError:
                log.debug("💭 心跳信号 - 模型正在思考中...")
                yield create_heartbeat_event()
            except Exception as e:
                log.debug(f"Stream error: {e}")
                break


def wrap_stream_with_heartbeat(stream: aiohttp.StreamReader) -> HeartbeatStreamWrapper:
    """
    Convenience function to wrap a stream with heartbeat support.
    
    Args:
        stream: The aiohttp StreamReader to wrap
        
    Returns:
        HeartbeatStreamWrapper that can be used with stream_chunks_handler
    """
    return HeartbeatStreamWrapper(stream)
