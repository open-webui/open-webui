"""
Heartbeat utility for streaming responses.
Sends periodic heartbeat events to indicate connection is alive during model reasoning.

This module is designed for minimal intrusion - easy to add/remove during upstream merges.
"""
import asyncio
import time
import json
import logging
from typing import AsyncIterator, Optional
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
    return f"data: {json.dumps(data)}\n\n".encode("utf-8")


async def stream_with_heartbeat(
    stream: aiohttp.StreamReader,
    heartbeat_interval: float = HEARTBEAT_INTERVAL
) -> AsyncIterator[bytes]:
    """
    Wrap a stream to send heartbeat events when waiting for data.
    
    This is useful for reasoning models that may take a long time to respond,
    allowing the frontend to know the connection is still alive.
    
    Args:
        stream: The aiohttp StreamReader
        heartbeat_interval: Seconds between heartbeat events when idle
        
    Yields:
        Original stream data interspersed with heartbeat events when idle
    """
    buffer = b""
    
    while True:
        try:
            # Try to read with timeout
            chunk = await asyncio.wait_for(
                stream.read(8192),
                timeout=heartbeat_interval
            )
            
            if not chunk:
                # Stream ended
                if buffer:
                    yield buffer
                break
            
            # Yield the data
            yield chunk
            
        except asyncio.TimeoutError:
            # No data received within interval, send heartbeat
            log.debug("Sending heartbeat - model is still thinking")
            yield create_heartbeat_event()
        except Exception as e:
            log.debug(f"Stream error: {e}")
            break
