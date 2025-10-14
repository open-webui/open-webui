"""
SQLite + Supabase Sync System - State Manager
Phase 1: Cache-Aside State Management

This module implements a cache-aside pattern with Supabase PostgreSQL as the
authoritative state source. Local caching provides resilience, while Supabase
ensures cluster-wide consistency.

Key Features:
- Cache-aside pattern with configurable TTL
- Supabase as authoritative source (write-through)
- Cluster-wide cache invalidation via events
- Async operations with asyncpg
"""

import asyncio
import time
from typing import Dict, Optional, Any
from datetime import datetime
import logging
import json

import asyncpg
from metrics import (
    record_cache_operation,
    state_cache_invalidations_total,
    state_cache_size,
    state_sync_lag_seconds
)

logger = logging.getLogger(__name__)


class StateManager:
    """
    Manages deployment state with cache-aside pattern.

    Supabase is the authoritative source for all state. Local cache provides
    fast reads and resilience during network issues.

    Invariant: All writes go to Supabase FIRST, then cache is invalidated.
    This ensures that if a write succeeds but cache invalidation fails,
    the next read will fetch correct state from Supabase.
    """

    def __init__(self, db_url: str, host_id: str, cluster_name: str = None, ttl: int = 300):
        """
        Initialize StateManager.

        Args:
            db_url: PostgreSQL connection URL (Supabase)
            host_id: Unique identifier for this host
            cluster_name: Cluster name for RLS policy filtering (optional)
            ttl: Cache time-to-live in seconds (default: 5 minutes)
        """
        self.db_url = db_url
        self.host_id = host_id
        self.cluster_name = cluster_name
        self.ttl = ttl

        # Local cache
        self.cache: Dict[str, Any] = {}
        self.cache_expiry: Dict[str, float] = {}

        # Connection pool
        self.pool: Optional[asyncpg.Pool] = None

        # Last sync timestamp
        self.last_sync_at: Optional[float] = None

        logger.info(f"StateManager initialized with TTL={ttl}s, host_id={host_id}, cluster={cluster_name}")

    async def initialize(self):
        """
        Initialize database connection pool.

        Creates an asyncpg connection pool with optimal settings for
        long-lived connections. Each connection is initialized with
        session context for RLS policies.
        """
        try:
            self.pool = await asyncpg.create_pool(
                self.db_url,
                min_size=2,
                max_size=10,
                max_queries=50000,
                max_inactive_connection_lifetime=300,
                command_timeout=30,
                # Set session context on every new connection
                init=self._init_connection
            )
            logger.info("Database connection pool created successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise

    async def _init_connection(self, conn):
        """
        Initialize each new connection with session context for RLS.

        This is called automatically for every connection acquired from the pool.
        """
        result = await conn.fetchval(
            "SELECT sync_metadata.set_sync_context($1::uuid, NULL, $2, NULL)",
            self.host_id,
            self.cluster_name
        )
        logger.debug(f"Connection initialized with session context: {result}")

    async def get_state(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get state with cache-aside pattern.

        Flow:
        1. Check local cache (with TTL validation)
        2. If cache miss or expired, fetch from Supabase
        3. Update local cache
        4. Return state

        Args:
            key: State key

        Returns:
            State dictionary or None if not found
        """
        # Check cache first
        if self._is_cache_valid(key):
            record_cache_operation(hit=True)
            logger.debug(f"Cache HIT for key: {key}")
            return self.cache[key]

        # Cache miss - fetch from Supabase (authoritative source)
        record_cache_operation(hit=False)
        logger.debug(f"Cache MISS for key: {key}, fetching from Supabase")

        state = await self._fetch_from_supabase(key)

        if state is not None:
            # Update local cache
            self._update_cache(key, state)

        return state

    async def update_state(self, key: str, state: Dict[str, Any]) -> bool:
        """
        Update state - Supabase first, then invalidate cache.

        CRITICAL INVARIANT: Update authoritative source (Supabase) FIRST,
        then invalidate local cache. This ensures that if cache invalidation
        fails, the next read will fetch correct state from Supabase.

        Args:
            key: State key
            state: State data to store

        Returns:
            True if update successful, False otherwise
        """
        logger.debug(f"Updating state for key: {key}")

        # CRITICAL: Update Supabase first (authoritative source)
        success = await self._update_supabase(key, state)

        if success:
            # Invalidate local cache to force refresh on next read
            self._invalidate_cache(key, reason='update')

            # Notify other containers in cluster via cache event
            await self._notify_cluster(key, 'invalidate')

            logger.info(f"State updated successfully for key: {key}")
        else:
            logger.error(f"Failed to update state for key: {key}")

        return success

    def _is_cache_valid(self, key: str) -> bool:
        """
        Check if cache entry is valid (exists and not expired).

        Args:
            key: Cache key

        Returns:
            True if cache hit and not expired
        """
        if key not in self.cache:
            return False

        if key not in self.cache_expiry:
            return False

        return time.time() < self.cache_expiry[key]

    async def _fetch_from_supabase(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Fetch state from Supabase (authoritative source).

        Args:
            key: State key

        Returns:
            State data or None if not found
        """
        try:
            async with self.pool.acquire() as conn:
                # Note: We're using a generic state table here
                # In production, you'd query specific tables based on key pattern
                # For now, using deployment state as example

                # Parse key to determine table and ID
                # Example key format: "deployment.acme-corp"
                if key.startswith("deployment."):
                    client_name = key.split(".", 1)[1]
                    row = await conn.fetchrow(
                        """SELECT deployment_id, client_name, sync_enabled, sync_interval,
                                  last_sync_at, status, config
                           FROM sync_metadata.client_deployments
                           WHERE client_name = $1""",
                        client_name
                    )

                    if row:
                        return dict(row)

                # Generic key-value state (would need a state_cache table for this)
                # For MVP, return None for unknown keys
                return None

        except Exception as e:
            logger.error(f"Error fetching state from Supabase for key {key}: {e}")
            return None

    async def _update_supabase(self, key: str, state: Dict[str, Any]) -> bool:
        """
        Update state in Supabase (authoritative source).

        Args:
            key: State key
            state: State data

        Returns:
            True if update successful
        """
        try:
            async with self.pool.acquire() as conn:
                # Parse key to determine table and update
                if key.startswith("deployment."):
                    client_name = key.split(".", 1)[1]

                    # Update deployment state
                    await conn.execute(
                        """UPDATE sync_metadata.client_deployments
                           SET sync_enabled = COALESCE($2, sync_enabled),
                               sync_interval = COALESCE($3, sync_interval),
                               status = COALESCE($4, status),
                               config = COALESCE($5::jsonb, config),
                               updated_at = NOW()
                           WHERE client_name = $1""",
                        client_name,
                        state.get('sync_enabled'),
                        state.get('sync_interval'),
                        state.get('status'),
                        json.dumps(state.get('config')) if state.get('config') else None
                    )

                    self.last_sync_at = time.time()
                    state_sync_lag_seconds.labels(host_id=self.host_id).set(0)

                    return True

                # Unknown key pattern
                logger.warning(f"Unknown key pattern for update: {key}")
                return False

        except Exception as e:
            logger.error(f"Error updating Supabase for key {key}: {e}")
            return False

    def _update_cache(self, key: str, state: Dict[str, Any]):
        """
        Update local cache with state data.

        Args:
            key: Cache key
            state: State data to cache
        """
        self.cache[key] = state
        self.cache_expiry[key] = time.time() + self.ttl

        # Update metrics
        state_cache_size.set(len(self.cache))

        logger.debug(f"Cache updated for key: {key}, expires in {self.ttl}s")

    def _invalidate_cache(self, key: str, reason: str = 'manual'):
        """
        Invalidate cache entry.

        Args:
            key: Cache key
            reason: Reason for invalidation (for metrics)
        """
        if key in self.cache:
            del self.cache[key]

        if key in self.cache_expiry:
            del self.cache_expiry[key]

        # Update metrics
        state_cache_invalidations_total.labels(reason=reason).inc()
        state_cache_size.set(len(self.cache))

        logger.debug(f"Cache invalidated for key: {key}, reason: {reason}")

    async def _notify_cluster(self, key: str, action: str):
        """
        Notify other containers in cluster via cache_events table.

        This allows secondary containers to invalidate their caches when
        the primary updates state.

        Args:
            key: Cache key
            action: Action to notify (invalidate, refresh, delete)
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO sync_metadata.cache_events (host_id, cache_key, action)
                       VALUES ($1::uuid, $2, $3)""",
                    self.host_id,
                    key,
                    action
                )

                logger.debug(f"Cluster notified: key={key}, action={action}")

        except Exception as e:
            logger.error(f"Error notifying cluster for key {key}: {e}")
            # Don't fail the operation if notification fails

    async def process_cache_events(self):
        """
        Process cache invalidation events from other containers.

        This should be called periodically (e.g., every 5 seconds) to process
        cache events from other containers in the cluster.
        """
        try:
            async with self.pool.acquire() as conn:
                # Fetch unprocessed events for this host
                events = await conn.fetch(
                    """SELECT event_id, cache_key, action, created_at
                       FROM sync_metadata.cache_events
                       WHERE host_id = $1::uuid
                         AND processed_at IS NULL
                       ORDER BY created_at ASC
                       LIMIT 100""",
                    self.host_id
                )

                for event in events:
                    event_id = event['event_id']
                    cache_key = event['cache_key']
                    action = event['action']

                    # Process event
                    if action == 'invalidate':
                        self._invalidate_cache(cache_key, reason='cluster_event')
                    elif action == 'delete':
                        self._invalidate_cache(cache_key, reason='cluster_delete')
                    elif action == 'refresh':
                        # Force refresh by invalidating cache
                        self._invalidate_cache(cache_key, reason='cluster_refresh')

                    # Mark event as processed
                    await conn.execute(
                        """UPDATE sync_metadata.cache_events
                           SET processed_at = NOW(),
                               processed_by = $2
                           WHERE event_id = $1""",
                        event_id,
                        self.host_id
                    )

                if events:
                    logger.info(f"Processed {len(events)} cache events from cluster")

        except Exception as e:
            logger.error(f"Error processing cache events: {e}")

    async def cleanup_expired_cache(self):
        """
        Remove expired entries from local cache.

        This should be called periodically (e.g., every minute) to free memory.
        """
        now = time.time()
        expired_keys = [
            key for key, expiry in self.cache_expiry.items()
            if expiry < now
        ]

        for key in expired_keys:
            self._invalidate_cache(key, reason='expiry')

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

    async def get_deployment_state(self, client_name: str) -> Optional[Dict[str, Any]]:
        """
        Convenience method to get deployment state.

        Args:
            client_name: Client name

        Returns:
            Deployment state or None
        """
        return await self.get_state(f"deployment.{client_name}")

    async def update_deployment_state(self, client_name: str, **updates) -> bool:
        """
        Convenience method to update deployment state.

        Args:
            client_name: Client name
            **updates: Fields to update

        Returns:
            True if successful
        """
        return await self.update_state(f"deployment.{client_name}", updates)

    async def close(self):
        """
        Close database connection pool and clean up resources.
        """
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")

    def __repr__(self):
        return f"StateManager(host_id={self.host_id}, ttl={self.ttl}s, cache_size={len(self.cache)})"
