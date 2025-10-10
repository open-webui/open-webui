"""
SQLite + Supabase Sync System - Conflict Resolver
Phase 1: Automated Conflict Resolution

This module implements configurable conflict resolution strategies for
database synchronization. Supports multiple strategies with table-specific
configuration.

Strategies:
- newest_wins: Use row with most recent timestamp
- source_wins: Always prefer SQLite (source) version
- target_wins: Always prefer Supabase (target) version
- merge: Merge changes using field-level rules
- manual: Flag for human review
"""

import json
import asyncio
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime
from pathlib import Path
import logging

import asyncpg
from metrics import record_conflict

logger = logging.getLogger(__name__)


class ConflictResolver:
    """
    Resolves synchronization conflicts using configurable strategies.

    Conflicts occur when the same row has been modified in both SQLite
    and Supabase since the last sync. The resolver uses table-specific
    strategies to automatically resolve most conflicts, flagging only
    critical cases for manual review.
    """

    def __init__(self, config_path: str, db_url: str):
        """
        Initialize ConflictResolver.

        Args:
            config_path: Path to conflict resolution JSON configuration
            db_url: PostgreSQL connection URL for logging conflicts
        """
        self.config_path = config_path
        self.db_url = db_url

        # Load configuration
        with open(config_path, 'r') as f:
            self.config = json.load(f)['conflict_resolution']

        # Strategy implementations
        self.strategies: Dict[str, Callable] = {
            'newest_wins': self._resolve_newest_wins,
            'source_wins': self._resolve_source_wins,
            'target_wins': self._resolve_target_wins,
            'merge': self._resolve_merge,
            'manual': self._flag_manual_resolution
        }

        # Connection pool (lazy initialization)
        self.pool: Optional[asyncpg.Pool] = None

        logger.info(f"ConflictResolver initialized with config: {config_path}")

    async def initialize(self):
        """Initialize database connection pool."""
        self.pool = await asyncpg.create_pool(
            self.db_url,
            min_size=1,
            max_size=5
        )
        logger.info("ConflictResolver database pool created")

    async def resolve_conflict(
        self,
        table: str,
        source_row: Dict[str, Any],
        target_row: Dict[str, Any],
        client_id: str,
        deployment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Resolve conflict based on configured strategy.

        Args:
            table: Table name
            source_row: Row from SQLite (source)
            target_row: Row from Supabase (target)
            client_id: Client identifier
            deployment_id: Deployment UUID (optional)

        Returns:
            Resolved row data
        """
        import time
        start_time = time.time()

        # Get strategy for this table
        strategy = self._get_strategy(table)

        logger.info(
            f"Resolving conflict for {table} (client: {client_id}) "
            f"using strategy: {strategy}"
        )

        # Log conflict detection
        conflict_type = self._determine_conflict_type(source_row, target_row)
        record_id = source_row.get('id') or target_row.get('id')

        await self._log_conflict(
            deployment_id=deployment_id,
            client_name=client_id,
            table_name=table,
            record_id=str(record_id),
            conflict_type=conflict_type,
            source_data=source_row,
            target_data=target_row,
            resolution_strategy=strategy
        )

        # Apply resolution strategy
        try:
            resolved = self.strategies[strategy](source_row, target_row, table)
        except Exception as e:
            logger.error(f"Error applying strategy {strategy}: {e}")
            # Fallback to target_wins on error
            resolved = target_row

        # Log resolution
        await self._log_resolution(
            client_name=client_id,
            table_name=table,
            record_id=str(record_id),
            resolved_data=resolved,
            resolution_strategy=strategy
        )

        # Record metrics
        resolution_time = time.time() - start_time
        record_conflict(
            client=client_id,
            table=table,
            conflict_type=conflict_type,
            strategy=strategy,
            resolution_time=resolution_time
        )

        logger.debug(
            f"Conflict resolved in {resolution_time:.3f}s using {strategy}"
        )

        return resolved

    def _get_strategy(self, table: str) -> str:
        """
        Get resolution strategy for table.

        Args:
            table: Table name

        Returns:
            Strategy name
        """
        table_config = self.config['table_strategies']

        if table in table_config:
            return table_config[table]['strategy']

        return self.config['default_strategy']

    def _determine_conflict_type(
        self,
        source_row: Dict[str, Any],
        target_row: Dict[str, Any]
    ) -> str:
        """
        Determine the type of conflict.

        Args:
            source_row: Source row data
            target_row: Target row data

        Returns:
            Conflict type string
        """
        if not target_row:
            return 'insert_conflict'
        if not source_row:
            return 'delete_conflict'

        # Check if both rows were updated
        source_updated = source_row.get('updated_at')
        target_updated = target_row.get('updated_at')

        if source_updated and target_updated and source_updated != target_updated:
            return 'update_conflict'

        return 'custom'

    # ========================================================================
    # RESOLUTION STRATEGIES
    # ========================================================================

    def _resolve_newest_wins(
        self,
        source: Dict[str, Any],
        target: Dict[str, Any],
        table: str
    ) -> Dict[str, Any]:
        """
        Resolution: Use the row with most recent updated_at.

        Args:
            source: SQLite row
            target: Supabase row
            table: Table name

        Returns:
            Resolved row
        """
        table_config = self.config['table_strategies'].get(table, {})
        compare_field = table_config.get('compare_field', self.config['default_compare_field'])

        source_time = source.get(compare_field)
        target_time = target.get(compare_field)

        if not source_time:
            return target
        if not target_time:
            return source

        # Parse timestamps
        try:
            if isinstance(source_time, str):
                source_dt = datetime.fromisoformat(source_time.replace('Z', '+00:00'))
            else:
                source_dt = source_time

            if isinstance(target_time, str):
                target_dt = datetime.fromisoformat(target_time.replace('Z', '+00:00'))
            else:
                target_dt = target_time

            result = source if source_dt > target_dt else target
            logger.debug(
                f"newest_wins: source={source_dt.isoformat()}, "
                f"target={target_dt.isoformat()}, winner={'source' if result == source else 'target'}"
            )
            return result

        except Exception as e:
            logger.error(f"Error parsing timestamps for newest_wins: {e}")
            # Fallback to source
            return source

    def _resolve_source_wins(
        self,
        source: Dict[str, Any],
        target: Dict[str, Any],
        table: str
    ) -> Dict[str, Any]:
        """
        Resolution: Always use source (SQLite).

        Use this for tables where local state is authoritative,
        such as active sessions.

        Args:
            source: SQLite row
            target: Supabase row
            table: Table name

        Returns:
            Source row
        """
        logger.debug(f"source_wins: Using source row for {table}")
        return source

    def _resolve_target_wins(
        self,
        source: Dict[str, Any],
        target: Dict[str, Any],
        table: str
    ) -> Dict[str, Any]:
        """
        Resolution: Always use target (Supabase).

        Use this when Supabase should be authoritative.

        Args:
            source: SQLite row
            target: Supabase row
            table: Table name

        Returns:
            Target row
        """
        logger.debug(f"target_wins: Using target row for {table}")
        return target

    def _resolve_merge(
        self,
        source: Dict[str, Any],
        target: Dict[str, Any],
        table: str
    ) -> Dict[str, Any]:
        """
        Resolution: Merge based on configured rules.

        Applies field-level merge rules to combine source and target data.

        Args:
            source: SQLite row
            target: Supabase row
            table: Table name

        Returns:
            Merged row
        """
        table_config = self.config['table_strategies'].get(table, {})
        merge_rules = table_config.get('merge_rules', {})

        if not merge_rules:
            logger.warning(f"No merge rules for {table}, falling back to newest_wins")
            return self._resolve_newest_wins(source, target, table)

        # Start with target as base
        merged = target.copy()

        for field, rule in merge_rules.items():
            if rule == 'append':
                # Append lists/arrays (deduplicate)
                source_val = source.get(field, [])
                target_val = target.get(field, [])

                if isinstance(source_val, list) and isinstance(target_val, list):
                    merged[field] = target_val + [x for x in source_val if x not in target_val]
                else:
                    merged[field] = source_val  # Fallback

            elif rule == 'newest_wins':
                # Take newest value for this field
                source_time = source.get('updated_at')
                target_time = target.get('updated_at')

                if source_time and target_time:
                    try:
                        if isinstance(source_time, str):
                            source_dt = datetime.fromisoformat(source_time.replace('Z', '+00:00'))
                        else:
                            source_dt = source_time

                        if isinstance(target_time, str):
                            target_dt = datetime.fromisoformat(target_time.replace('Z', '+00:00'))
                        else:
                            target_dt = target_time

                        if source_dt > target_dt and field in source:
                            merged[field] = source[field]
                    except Exception as e:
                        logger.error(f"Error in merge newest_wins for field {field}: {e}")

            elif rule == 'union':
                # Union of sets
                source_val = source.get(field, [])
                target_val = target.get(field, [])

                if isinstance(source_val, list) and isinstance(target_val, list):
                    merged[field] = list(set(target_val) | set(source_val))
                else:
                    merged[field] = source_val  # Fallback

            elif rule == 'source_wins':
                # Take source value for this field
                if field in source:
                    merged[field] = source[field]

            elif rule == 'target_wins':
                # Keep target value (already in merged)
                pass

        logger.debug(f"merge: Merged {len(merge_rules)} fields for {table}")
        return merged

    def _flag_manual_resolution(
        self,
        source: Dict[str, Any],
        target: Dict[str, Any],
        table: str
    ) -> Dict[str, Any]:
        """
        Resolution: Flag for manual review, keep target.

        Use this for critical tables where automated resolution
        is risky (e.g., configuration, functions).

        Args:
            source: SQLite row
            target: Supabase row
            table: Table name

        Returns:
            Target row (unchanged)
        """
        logger.warning(
            f"manual: Conflict flagged for manual resolution on {table}. "
            f"Keeping target unchanged."
        )

        # The conflict will be logged with resolution_strategy='manual'
        # and resolved_by=NULL, which flags it for manual review

        return target

    # ========================================================================
    # CONFLICT LOGGING
    # ========================================================================

    async def _log_conflict(
        self,
        deployment_id: Optional[str],
        client_name: str,
        table_name: str,
        record_id: str,
        conflict_type: str,
        source_data: Dict[str, Any],
        target_data: Dict[str, Any],
        resolution_strategy: str
    ):
        """
        Log conflict to sync_metadata.conflict_log.

        Args:
            deployment_id: Deployment UUID
            client_name: Client identifier
            table_name: Table name
            record_id: Record ID
            conflict_type: Type of conflict
            source_data: Source row data
            target_data: Target row data
            resolution_strategy: Resolution strategy used
        """
        if not self.pool:
            await self.initialize()

        try:
            async with self.pool.acquire() as conn:
                # Convert data to JSON, excluding binary fields if any
                source_json = json.dumps(source_data, default=str)
                target_json = json.dumps(target_data, default=str)

                await conn.execute(
                    """INSERT INTO sync_metadata.conflict_log
                       (deployment_id, client_name, table_name, record_id,
                        conflict_type, source_data, target_data, resolution_strategy,
                        detected_at)
                       VALUES ($1::uuid, $2, $3, $4, $5, $6::jsonb, $7::jsonb, $8, NOW())""",
                    deployment_id if deployment_id else None,
                    client_name,
                    table_name,
                    record_id,
                    conflict_type,
                    source_json,
                    target_json,
                    resolution_strategy
                )

        except Exception as e:
            logger.error(f"Error logging conflict: {e}")
            # Don't fail the sync operation if logging fails

    async def _log_resolution(
        self,
        client_name: str,
        table_name: str,
        record_id: str,
        resolved_data: Dict[str, Any],
        resolution_strategy: str
    ):
        """
        Update conflict log with resolution.

        Args:
            client_name: Client identifier
            table_name: Table name
            record_id: Record ID
            resolved_data: Resolved row data
            resolution_strategy: Resolution strategy used
        """
        if not self.pool:
            await self.initialize()

        try:
            async with self.pool.acquire() as conn:
                resolved_json = json.dumps(resolved_data, default=str)

                # Determine resolved_by
                resolved_by = 'automatic' if resolution_strategy != 'manual' else None

                await conn.execute(
                    """UPDATE sync_metadata.conflict_log
                       SET resolved_data = $1::jsonb,
                           resolved_at = NOW(),
                           resolved_by = $2
                       WHERE client_name = $3
                         AND table_name = $4
                         AND record_id = $5
                         AND resolved_at IS NULL
                       ORDER BY detected_at DESC
                       LIMIT 1""",
                    resolved_json,
                    resolved_by,
                    client_name,
                    table_name,
                    record_id
                )

        except Exception as e:
            logger.error(f"Error logging resolution: {e}")

    async def get_unresolved_conflicts(
        self,
        client_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get unresolved conflicts (manual review required).

        Args:
            client_name: Filter by client name (optional)
            limit: Maximum number of conflicts to return

        Returns:
            List of conflict records
        """
        if not self.pool:
            await self.initialize()

        try:
            async with self.pool.acquire() as conn:
                if client_name:
                    rows = await conn.fetch(
                        """SELECT log_id, client_name, table_name, record_id,
                                  conflict_type, detected_at, resolution_strategy
                           FROM sync_metadata.conflict_log
                           WHERE client_name = $1
                             AND resolved_at IS NULL
                           ORDER BY detected_at DESC
                           LIMIT $2""",
                        client_name,
                        limit
                    )
                else:
                    rows = await conn.fetch(
                        """SELECT log_id, client_name, table_name, record_id,
                                  conflict_type, detected_at, resolution_strategy
                           FROM sync_metadata.conflict_log
                           WHERE resolved_at IS NULL
                           ORDER BY detected_at DESC
                           LIMIT $1""",
                        limit
                    )

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error fetching unresolved conflicts: {e}")
            return []

    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("ConflictResolver database pool closed")

    def __repr__(self):
        return f"ConflictResolver(config={self.config_path})"
