"""
SQLite + Supabase Sync System - Python Package
Phase 1: High Availability Sync Container

This package provides the core synchronization infrastructure for
multi-tenant Open WebUI deployments.

Components:
- state_manager: Cache-aside state management with Supabase as authoritative source
- leader_election: PostgreSQL-based distributed leader election
- conflict_resolver: Automated conflict resolution with configurable strategies
- metrics: Prometheus metrics for monitoring
- main: FastAPI application entry point
"""

__version__ = "1.0.0"
__phase__ = "1"
