"""
Async database utilities with connection pooling for batch operations
"""

import asyncio
import aiosqlite
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, List, Tuple, Any
import logging

from open_webui.config import DATA_DIR

log = logging.getLogger(__name__)


class AsyncDatabase:
    """Async database wrapper with connection pooling and transaction support"""
    
    def __init__(self, db_path: str, pool_size: int = 5):
        self.db_path = db_path
        self.pool_size = pool_size
        self._pool: List[aiosqlite.Connection] = []
        self._semaphore = asyncio.Semaphore(pool_size)
        
    async def initialize(self):
        """Initialize connection pool"""
        for _ in range(self.pool_size):
            conn = await aiosqlite.connect(self.db_path)
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA synchronous=NORMAL")
            self._pool.append(conn)
            
    async def close(self):
        """Close all connections in the pool"""
        for conn in self._pool:
            await conn.close()
        self._pool.clear()
        
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Get a connection from the pool"""
        async with self._semaphore:
            conn = self._pool.pop()
            try:
                yield conn
            finally:
                self._pool.append(conn)
                
    async def execute(self, query: str, params: Optional[Tuple] = None) -> None:
        """Execute a single query"""
        async with self.get_connection() as conn:
            await conn.execute(query, params or ())
            await conn.commit()
            
    async def executemany(self, query: str, params_list: List[Tuple]) -> None:
        """Execute multiple queries in a single transaction"""
        async with self.get_connection() as conn:
            await conn.executemany(query, params_list)
            await conn.commit()
            
    async def fetchone(self, query: str, params: Optional[Tuple] = None) -> Optional[Tuple]:
        """Fetch a single row"""
        async with self.get_connection() as conn:
            cursor = await conn.execute(query, params or ())
            return await cursor.fetchone()
            
    async def fetchall(self, query: str, params: Optional[Tuple] = None) -> List[Tuple]:
        """Fetch all rows"""
        async with self.get_connection() as conn:
            cursor = await conn.execute(query, params or ())
            return await cursor.fetchall()
            
    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Execute operations in a transaction with automatic rollback on error"""
        async with self.get_connection() as conn:
            try:
                await conn.execute("BEGIN")
                yield conn
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise


# Singleton instance
_async_db: Optional[AsyncDatabase] = None


async def get_async_db() -> AsyncDatabase:
    """Get or create the async database instance"""
    global _async_db
    if _async_db is None:
        _async_db = AsyncDatabase(f"{DATA_DIR}/webui.db")
        await _async_db.initialize()
    return _async_db