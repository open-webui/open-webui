"""
SQLite + Supabase Sync System - Leader Election
Phase 1: High Availability via PostgreSQL Atomic Operations

This module implements distributed leader election using PostgreSQL's
atomic operations. This provides strong consistency guarantees without
requiring external coordination services like etcd or Zookeeper.

Key Features:
- Atomic leader acquisition via INSERT...ON CONFLICT
- Lease-based leadership with automatic expiration
- Heartbeat mechanism for lease renewal
- Automatic failover on leader failure
- No split-brain scenarios (PostgreSQL guarantees atomicity)
"""

import asyncio
import asyncpg
from typing import Optional, Callable
from datetime import datetime, timedelta
import logging
import time

from metrics import (
    record_leader_election,
    leader_lease_expires_timestamp,
    heartbeat_failures_total,
    failover_events_total,
    container_uptime_seconds
)

logger = logging.getLogger(__name__)


class LeaderElection:
    """
    Manages distributed leader election using PostgreSQL.

    Uses PostgreSQL's atomic INSERT...ON CONFLICT to ensure only one leader
    exists per cluster. Leader holds a time-bound lease that must be renewed
    via heartbeats.

    Architecture:
    - Lease duration: 60 seconds
    - Heartbeat interval: 30 seconds (renew before expiry)
    - Failover time: ~35 seconds maximum (lease expiry + one heartbeat interval)
    """

    def __init__(
        self,
        cluster_name: str,
        node_id: str,
        host_id: str,
        db_url: str,
        lease_duration: int = 60,
        heartbeat_interval: int = 30,
        on_become_leader: Optional[Callable] = None,
        on_lose_leadership: Optional[Callable] = None
    ):
        """
        Initialize LeaderElection.

        Args:
            cluster_name: Cluster identifier (usually hostname)
            node_id: Unique node identifier (e.g., "openwebui-sync-primary")
            host_id: Host UUID for RLS context
            db_url: PostgreSQL connection URL
            lease_duration: Lease duration in seconds (default: 60)
            heartbeat_interval: Heartbeat interval in seconds (default: 30)
            on_become_leader: Callback when this node becomes leader
            on_lose_leadership: Callback when this node loses leadership
        """
        self.cluster_name = cluster_name
        self.node_id = node_id
        self.host_id = host_id
        self.db_url = db_url
        self.lease_duration = lease_duration
        self.heartbeat_interval = heartbeat_interval

        # Leadership state
        self.is_leader = False
        self.current_leader_id: Optional[str] = None

        # Callbacks
        self.on_become_leader = on_become_leader
        self.on_lose_leadership = on_lose_leadership

        # Connection pool
        self.pool: Optional[asyncpg.Pool] = None

        # Background task
        self.election_task: Optional[asyncio.Task] = None
        self.running = False

        # Start time for uptime metric
        self.start_time = time.time()

        # Heartbeat failure counter
        self.consecutive_failures = 0
        self.max_consecutive_failures = 3

        logger.info(
            f"LeaderElection initialized: cluster={cluster_name}, "
            f"node={node_id}, lease={lease_duration}s, heartbeat={heartbeat_interval}s"
        )

    async def initialize(self):
        """
        Initialize database connection pool and register host.
        """
        try:
            self.pool = await asyncpg.create_pool(
                self.db_url,
                min_size=1,
                max_size=3,
                max_queries=10000,
                command_timeout=10,
                # Set session context on every new connection
                init=self._init_connection
            )
            logger.info("Leader election database pool created")

            # Register this host in sync_metadata.hosts
            await self._register_host()

        except Exception as e:
            logger.error(f"Failed to initialize leader election: {e}")
            raise

    async def _init_connection(self, conn):
        """
        Initialize each new connection with session context for RLS.

        This is called automatically for every connection acquired from the pool.
        Sets session-level PostgreSQL variables for RLS policies.
        """
        # Set session parameters directly (persists for the life of the connection)
        await conn.execute(f"SET app.current_host_id = '{self.host_id}'")
        await conn.execute(f"SET app.current_hostname = '{self.node_id}'")
        await conn.execute(f"SET app.current_cluster_name = '{self.cluster_name}'")
        logger.info(f"Session context set for connection: host_id={self.host_id}, cluster={self.cluster_name}")

    async def _register_host(self):
        """
        Register this host in sync_metadata.hosts table.

        This creates or updates the host record for RLS and monitoring.
        If the host already exists (by hostname + cluster_name), retrieves
        the existing host_id to maintain consistency across container restarts.
        """
        # First, query for existing host_id
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                """INSERT INTO sync_metadata.hosts (host_id, hostname, cluster_name, status, last_heartbeat)
                   VALUES ($1::uuid, $2, $3, 'active', NOW())
                   ON CONFLICT (hostname, cluster_name) DO UPDATE
                   SET status = 'active',
                       last_heartbeat = NOW()
                   RETURNING host_id""",
                self.host_id,
                self.node_id,
                self.cluster_name
            )

        # Update self.host_id with the stable host_id from the database
        # This ensures consistency across container restarts
        if result:
            db_host_id = str(result['host_id'])

            if db_host_id != self.host_id:
                old_host_id = self.host_id
                self.host_id = db_host_id
                logger.info(f"Using existing host_id {db_host_id} for {self.node_id} (was {old_host_id})")

                # Update session context on all existing connections in the pool
                # This is critical because _init_connection was called with the old host_id
                logger.info(f"About to update pool session context...")
                await self._update_pool_session_context()
                logger.info(f"Pool session context update complete")
            else:
                logger.info(f"Host registered: {self.node_id} with host_id {self.host_id}")

    async def _update_pool_session_context(self):
        """
        Update session context on all connections in the pool.

        Called after host_id is updated to the database value to ensure
        all pooled connections use the correct host_id for RLS policies.

        Since asyncpg pools don't provide direct access to modify all connections,
        we terminate all connections and let the pool recreate them with the
        correct host_id via the init callback.
        """
        logger.info(f"Updating session context to host_id={self.host_id}")

        if self.pool:
            # Close all connections in the pool (they'll be recreated on next use)
            await self.pool.expire_connections()
            logger.info("Pool connections expired - new connections will use updated host_id")

    async def start(self):
        """
        Start leader election background task.

        This launches an async task that continuously participates in
        leader election.
        """
        if self.running:
            logger.warning("Leader election already running")
            return

        self.running = True
        self.election_task = asyncio.create_task(self._participate())
        logger.info("Leader election started")

    async def stop(self):
        """
        Stop leader election and release leadership if held.
        """
        self.running = False

        if self.election_task:
            self.election_task.cancel()
            try:
                await self.election_task
            except asyncio.CancelledError:
                pass

        # Release leadership if we hold it
        if self.is_leader:
            await self._release_leadership()

        logger.info("Leader election stopped")

    async def _participate(self):
        """
        Participate in leader election (background task).

        This runs continuously, attempting to acquire or renew leadership
        at each heartbeat interval.
        """
        logger.info(f"Node {self.node_id} participating in leader election")

        iteration = 0
        while self.running:
            try:
                iteration += 1
                logger.info(f"Leader election loop iteration {iteration} starting")

                # Update uptime metric
                uptime = time.time() - self.start_time
                container_uptime_seconds.labels(node_id=self.node_id).set(uptime)

                # Attempt to acquire or renew leadership
                logger.info(f"Attempting to acquire/renew leadership...")
                acquired = await self._try_acquire_leadership()
                logger.info(f"Leadership acquisition result: {acquired}")

                previous_state = self.is_leader

                if acquired:
                    if not previous_state:
                        # Became leader
                        logger.info(f"🎉 Node {self.node_id} became LEADER for cluster {self.cluster_name}")
                        self.is_leader = True
                        self.consecutive_failures = 0

                        record_leader_election(
                            node_id=self.node_id,
                            cluster=self.cluster_name,
                            result='acquired',
                            is_leader_now=True
                        )

                        # Call callback
                        if self.on_become_leader:
                            try:
                                if asyncio.iscoroutinefunction(self.on_become_leader):
                                    await self.on_become_leader()
                                else:
                                    self.on_become_leader()
                            except Exception as e:
                                logger.error(f"Error in on_become_leader callback: {e}")

                    else:
                        # Renewed leadership
                        logger.info(f"Node {self.node_id} renewed leadership (iteration {iteration})")
                        record_leader_election(
                            node_id=self.node_id,
                            cluster=self.cluster_name,
                            result='renewed',
                            is_leader_now=True
                        )

                    self.is_leader = True
                    logger.info(f"Calling _perform_leader_duties...")
                    await self._perform_leader_duties()
                    logger.info(f"_perform_leader_duties completed")

                else:
                    if previous_state:
                        # Lost leadership
                        logger.warning(f"⚠️  Node {self.node_id} LOST leadership, now FOLLOWER")

                        record_leader_election(
                            node_id=self.node_id,
                            cluster=self.cluster_name,
                            result='lost',
                            is_leader_now=False
                        )

                        # Call callback
                        if self.on_lose_leadership:
                            try:
                                if asyncio.iscoroutinefunction(self.on_lose_leadership):
                                    await self.on_lose_leadership()
                                else:
                                    self.on_lose_leadership()
                            except Exception as e:
                                logger.error(f"Error in on_lose_leadership callback: {e}")

                    self.is_leader = False
                    logger.info(f"Calling _perform_follower_duties...")
                    await self._perform_follower_duties()
                    logger.info(f"_perform_follower_duties completed")

                # Sleep half the lease duration (renew before expiry)
                logger.info(f"Sleeping for {self.heartbeat_interval} seconds before next iteration")
                await asyncio.sleep(self.heartbeat_interval)
                logger.info(f"Woke up from sleep, starting iteration {iteration + 1}")

            except asyncio.CancelledError:
                logger.info("Leader election task cancelled")
                break

            except Exception as e:
                logger.error(f"Leader election error: {e}", exc_info=True)
                self.consecutive_failures += 1

                heartbeat_failures_total.labels(node_id=self.node_id).inc()

                if self.consecutive_failures >= self.max_consecutive_failures:
                    logger.error(f"Too many consecutive failures ({self.consecutive_failures}), stepping down")
                    self.is_leader = False

                    record_leader_election(
                        node_id=self.node_id,
                        cluster=self.cluster_name,
                        result='failed',
                        is_leader_now=False
                    )

                # Back off before retry
                await asyncio.sleep(5)

    async def _try_acquire_leadership(self) -> bool:
        """
        Try to acquire or renew leadership via atomic DB operation.

        Uses PostgreSQL's INSERT...ON CONFLICT with WHERE clause to ensure
        atomic leader election. Only succeeds if:
        1. No current leader (first to claim), OR
        2. Current lease expired (previous leader failed), OR
        3. This node is the current leader (renewal)

        Returns:
            True if this node is now the leader
        """
        query = """
        INSERT INTO sync_metadata.leader_election
            (cluster_name, leader_id, leader_host_id, acquired_at, expires_at, heartbeat_count)
        VALUES
            ($1, $2, $3::uuid, NOW(), NOW() + INTERVAL '%s seconds', 1)
        ON CONFLICT (cluster_name) DO UPDATE
        SET
            leader_id = EXCLUDED.leader_id,
            leader_host_id = EXCLUDED.leader_host_id,
            acquired_at = CASE
                WHEN leader_election.leader_id != EXCLUDED.leader_id THEN NOW()
                ELSE leader_election.acquired_at
            END,
            expires_at = NOW() + INTERVAL '%s seconds',
            heartbeat_count = CASE
                WHEN leader_election.leader_id = EXCLUDED.leader_id
                    THEN leader_election.heartbeat_count + 1
                ELSE 1
            END
        WHERE
            leader_election.expires_at < NOW()
            OR leader_election.leader_id = EXCLUDED.leader_id
        RETURNING
            leader_id = $2 as is_leader,
            expires_at,
            heartbeat_count;
        """ % (self.lease_duration, self.lease_duration)

        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow(
                    query,
                    self.cluster_name,
                    self.node_id,
                    self.host_id
                )

                if result:
                    is_leader_result = result['is_leader']
                    expires_at = result['expires_at']
                    heartbeat_count = result['heartbeat_count']

                    # Update metrics
                    if expires_at:
                        leader_lease_expires_timestamp.labels(
                            cluster=self.cluster_name
                        ).set(expires_at.timestamp())

                    # Check if another node became leader
                    await self._check_current_leader()

                    return is_leader_result
                else:
                    # No result means another node won the election
                    return False

        except Exception as e:
            logger.error(f"Error during leader election: {e}", exc_info=True)
            return False

    async def _check_current_leader(self):
        """
        Check who the current leader is.

        This is useful for follower nodes to know who to communicate with.
        """
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """SELECT leader_id, expires_at
                       FROM sync_metadata.leader_election
                       WHERE cluster_name = $1""",
                    self.cluster_name
                )

                if row:
                    self.current_leader_id = row['leader_id']

                    # Check if lease is expired
                    if row['expires_at'] < datetime.now():
                        logger.warning(f"Current leader {self.current_leader_id} lease EXPIRED")
                        self.current_leader_id = None

        except Exception as e:
            logger.error(f"Error checking current leader: {e}")

    async def _perform_leader_duties(self):
        """
        Perform leader-specific tasks.

        Override this method or use callbacks to implement leader-specific logic.
        """
        # Update host heartbeat
        try:
            logger.info(f"Updating heartbeat for host_id={self.host_id}")
            async with self.pool.acquire() as conn:
                # EXPLICITLY set session context before UPDATE
                # This ensures the correct host_id is used for RLS
                await conn.execute(f"SET app.current_host_id = '{self.host_id}'")
                await conn.execute(f"SET app.current_hostname = '{self.node_id}'")
                await conn.execute(f"SET app.current_cluster_name = '{self.cluster_name}'")

                result = await conn.execute(
                    """UPDATE sync_metadata.hosts
                       SET last_heartbeat = NOW(),
                           status = 'active'
                       WHERE host_id = $1::uuid""",
                    self.host_id
                )
                logger.info(f"Heartbeat update result: {result}")
        except Exception as e:
            logger.error(f"Error updating host heartbeat: {e}", exc_info=True)

        # Leader-specific work would go here or in callbacks
        # e.g., process sync job queue, coordinate cluster tasks, etc.

    async def _perform_follower_duties(self):
        """
        Perform follower-specific tasks.

        Override this method or use callbacks to implement follower-specific logic.
        """
        # Update host heartbeat
        try:
            logger.info(f"Updating heartbeat for host_id={self.host_id}")
            async with self.pool.acquire() as conn:
                # EXPLICITLY set session context before UPDATE
                # This ensures the correct host_id is used for RLS
                await conn.execute(f"SET app.current_host_id = '{self.host_id}'")
                await conn.execute(f"SET app.current_hostname = '{self.node_id}'")
                await conn.execute(f"SET app.current_cluster_name = '{self.cluster_name}'")

                result = await conn.execute(
                    """UPDATE sync_metadata.hosts
                       SET last_heartbeat = NOW(),
                           status = 'active'
                       WHERE host_id = $1::uuid""",
                    self.host_id
                )
                logger.info(f"Heartbeat update result: {result}")
        except Exception as e:
            logger.error(f"Error updating host heartbeat: {e}", exc_info=True)

        # Follower-specific work would go here or in callbacks
        # e.g., monitor leader health, update local metrics, etc.

    async def _release_leadership(self):
        """
        Release leadership voluntarily (e.g., on shutdown).

        Sets lease expiry to NOW so another node can immediately take over.
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """UPDATE sync_metadata.leader_election
                       SET expires_at = NOW()
                       WHERE cluster_name = $1
                         AND leader_id = $2""",
                    self.cluster_name,
                    self.node_id
                )

                logger.info(f"Leadership released by {self.node_id}")

                failover_events_total.labels(
                    from_node=self.node_id,
                    to_node='unknown',
                    reason='graceful_shutdown'
                ).inc()

        except Exception as e:
            logger.error(f"Error releasing leadership: {e}")

    async def get_current_leader(self) -> Optional[str]:
        """
        Get the current leader node ID.

        Returns:
            Leader node ID or None if no leader
        """
        await self._check_current_leader()
        return self.current_leader_id

    async def close(self):
        """
        Close database connection pool and clean up resources.
        """
        await self.stop()

        if self.pool:
            await self.pool.close()
            logger.info("Leader election database pool closed")

    def __repr__(self):
        return (
            f"LeaderElection(cluster={self.cluster_name}, node={self.node_id}, "
            f"is_leader={self.is_leader}, current_leader={self.current_leader_id})"
        )
