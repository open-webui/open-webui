"""
SQLite + Supabase Sync System - FastAPI Application
Phase 1: High Availability Sync Container

This is the main FastAPI application that runs in each sync container.
It integrates state management, leader election, conflict resolution,
and provides a REST API for monitoring and control.

Architecture:
- Primary and Secondary containers run this same application
- Leader election determines which container actively processes sync jobs
- Both containers participate in leader election via heartbeats
- State is cached locally with Supabase as authoritative source
"""

import asyncio
import os
import sys
import uuid
from contextlib import asynccontextmanager
from typing import Optional
import logging
from datetime import datetime

from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Import our modules
from state_manager import StateManager
from leader_election import LeaderElection
from conflict_resolver import ConflictResolver
from metrics import (
    setup_metrics,
    container_uptime_seconds,
    sync_queue_size,
    sync_jobs_active
)

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s' if os.getenv('LOG_FORMAT') != 'json' else None
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Environment variables (with defaults)
ROLE = os.getenv('ROLE', 'primary')  # primary or secondary
CLUSTER_NAME = os.getenv('CLUSTER_NAME', os.getenv('HOST_NAME', 'default-cluster'))
NODE_ID = f"{CLUSTER_NAME}-{ROLE}"
HOST_ID = os.getenv('HOST_ID', str(uuid.uuid4()))  # Generate if not provided
DATABASE_URL = os.getenv('DATABASE_URL')
API_PORT = int(os.getenv('API_PORT', '9443' if ROLE == 'primary' else '9444'))
CONFLICT_RESOLUTION_CONFIG = os.getenv('CONFLICT_RESOLUTION_CONFIG', '/app/config/conflict-resolution-default.json')
CACHE_TTL = int(os.getenv('CACHE_TTL', '300'))
HEARTBEAT_INTERVAL = int(os.getenv('HEARTBEAT_INTERVAL', '30'))
LEASE_DURATION = int(os.getenv('LEASE_DURATION', '60'))

# Validate required configuration
if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable is required")
    sys.exit(1)

logger.info(f"Starting sync container: role={ROLE}, cluster={CLUSTER_NAME}, node={NODE_ID}")

# ============================================================================
# GLOBAL INSTANCES
# ============================================================================

state_manager: Optional[StateManager] = None
leader_election: Optional[LeaderElection] = None
conflict_resolver: Optional[ConflictResolver] = None

# Background tasks
cache_cleanup_task: Optional[asyncio.Task] = None
cache_events_task: Optional[asyncio.Task] = None
periodic_sync_task: Optional[asyncio.Task] = None

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class StateUpdate(BaseModel):
    """Request model for state updates."""
    key: str = Field(..., description="State key")
    value: dict = Field(..., description="State value")

class SyncTrigger(BaseModel):
    """Request model for triggering manual sync."""
    client_name: str = Field(..., description="Client name to sync")
    full_sync: bool = Field(False, description="Perform full sync instead of incremental")

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    node_id: str
    role: str
    is_leader: bool
    cluster_name: str
    uptime_seconds: float
    leader_id: Optional[str] = None

class StateResponse(BaseModel):
    """State query response."""
    key: str
    value: Optional[dict]
    cached: bool
    updated_at: Optional[datetime]

# ============================================================================
# FASTAPI LIFESPAN
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle: startup and shutdown.

    Startup:
    - Initialize state manager
    - Initialize leader election
    - Initialize conflict resolver
    - Start background tasks

    Shutdown:
    - Stop background tasks
    - Release leadership
    - Close connections
    """
    global state_manager, leader_election, conflict_resolver
    global cache_cleanup_task, cache_events_task

    logger.info("=== Application Startup ===")

    try:
        # Initialize state manager
        logger.info("Initializing state manager...")
        state_manager = StateManager(DATABASE_URL, HOST_ID, ttl=CACHE_TTL)
        await state_manager.initialize()
        logger.info("✅ State manager initialized")

        # Initialize leader election
        logger.info("Initializing leader election...")
        leader_election = LeaderElection(
            cluster_name=CLUSTER_NAME,
            node_id=NODE_ID,
            host_id=HOST_ID,
            db_url=DATABASE_URL,
            lease_duration=LEASE_DURATION,
            heartbeat_interval=HEARTBEAT_INTERVAL,
            on_become_leader=on_become_leader,
            on_lose_leadership=on_lose_leadership
        )
        await leader_election.initialize()
        await leader_election.start()
        logger.info("✅ Leader election started")

        # Initialize conflict resolver
        logger.info("Initializing conflict resolver...")
        conflict_resolver = ConflictResolver(CONFLICT_RESOLUTION_CONFIG, DATABASE_URL)
        await conflict_resolver.initialize()
        logger.info("✅ Conflict resolver initialized")

        # Start background tasks
        logger.info("Starting background tasks...")
        cache_cleanup_task = asyncio.create_task(periodic_cache_cleanup())
        cache_events_task = asyncio.create_task(periodic_cache_events_processing())
        periodic_sync_task = asyncio.create_task(periodic_sync_scheduler())
        logger.info("✅ Background tasks started")

        logger.info("=== Application Ready ===")
        logger.info(f"API listening on port {API_PORT}")
        logger.info(f"Prometheus metrics available at /metrics")

    except Exception as e:
        logger.error(f"Failed to initialize application: {e}", exc_info=True)
        raise

    # Application runs here
    yield

    # Shutdown
    logger.info("=== Application Shutdown ===")

    # Cancel background tasks
    if cache_cleanup_task:
        cache_cleanup_task.cancel()
        try:
            await cache_cleanup_task
        except asyncio.CancelledError:
            pass

    if cache_events_task:
        cache_events_task.cancel()
        try:
            await cache_events_task
        except asyncio.CancelledError:
            pass

    if periodic_sync_task:
        periodic_sync_task.cancel()
        try:
            await periodic_sync_task
        except asyncio.CancelledError:
            pass

    # Stop leader election
    if leader_election:
        await leader_election.stop()
        await leader_election.close()

    # Close state manager
    if state_manager:
        await state_manager.close()

    # Close conflict resolver
    if conflict_resolver:
        await conflict_resolver.close()

    logger.info("✅ Application shutdown complete")

# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="Open WebUI Sync Service",
    description="High availability database synchronization service",
    version="1.0.0",
    lifespan=lifespan
)

# Setup Prometheus metrics
setup_metrics(app)

# ============================================================================
# LEADER ELECTION CALLBACKS
# ============================================================================

async def on_become_leader():
    """Called when this node becomes the leader."""
    logger.info(f"🎉 {NODE_ID} is now the LEADER")
    # Leader-specific initialization could go here
    # e.g., start processing sync job queue

async def on_lose_leadership():
    """Called when this node loses leadership."""
    logger.warning(f"⚠️  {NODE_ID} is no longer the leader")
    # Leader-specific cleanup could go here
    # e.g., stop processing sync job queue

# ============================================================================
# BACKGROUND TASKS
# ============================================================================

async def periodic_cache_cleanup():
    """Periodically clean up expired cache entries."""
    while True:
        try:
            await asyncio.sleep(60)  # Run every minute
            if state_manager:
                await state_manager.cleanup_expired_cache()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in cache cleanup task: {e}")

async def periodic_cache_events_processing():
    """Periodically process cache invalidation events from cluster."""
    while True:
        try:
            await asyncio.sleep(5)  # Run every 5 seconds
            if state_manager:
                await state_manager.process_cache_events()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in cache events processing task: {e}")

async def periodic_sync_scheduler():
    """
    Periodically check for clients needing sync and trigger sync jobs.

    Only runs on the leader node. Checks every 60 seconds for clients with:
    - sync_enabled = true
    - status = 'active'
    - (now - last_sync_at) >= sync_interval OR last_sync_at IS NULL
    """
    import asyncpg
    from datetime import datetime, timezone

    logger.info("Periodic sync scheduler started")

    # Wait a bit before starting to ensure leader election stabilizes
    await asyncio.sleep(30)

    while True:
        try:
            await asyncio.sleep(60)  # Check every minute

            # Only leader processes syncs
            if not leader_election or not leader_election.is_leader:
                continue

            # Query clients needing sync
            if not state_manager or not state_manager.pool:
                continue

            async with state_manager.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT
                        client_name,
                        sync_interval,
                        last_sync_at,
                        EXTRACT(EPOCH FROM (NOW() - last_sync_at))::int AS seconds_since_sync
                    FROM sync_metadata.client_deployments
                    WHERE sync_enabled = true
                      AND status = 'active'
                      AND (
                          last_sync_at IS NULL
                          OR EXTRACT(EPOCH FROM (NOW() - last_sync_at)) >= sync_interval
                      )
                    ORDER BY last_sync_at NULLS FIRST, client_name
                """)

                if rows:
                    logger.info(f"Found {len(rows)} client(s) needing sync")

                    for row in rows:
                        client_name = row['client_name']
                        sync_interval = row['sync_interval']
                        last_sync = row['last_sync_at']
                        seconds_since = row['seconds_since_sync']

                        if last_sync is None:
                            logger.info(f"Triggering initial sync for {client_name}")
                        else:
                            logger.info(
                                f"Triggering sync for {client_name} "
                                f"(interval: {sync_interval}s, last: {seconds_since}s ago)"
                            )

                        # Trigger sync as background task (incremental, not full)
                        asyncio.create_task(execute_sync_job(client_name, full_sync=False))
                        sync_queue_size.inc()

        except asyncio.CancelledError:
            logger.info("Periodic sync scheduler stopped")
            break
        except Exception as e:
            logger.error(f"Error in periodic sync scheduler: {e}", exc_info=True)

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirect."""
    return {
        "service": "Open WebUI Sync Service",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "docs": "/docs"
        }
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns current node status, leader election state, and uptime.
    Used by Docker health checks and monitoring systems.
    """
    import time

    if not leader_election:
        raise HTTPException(status_code=503, detail="Leader election not initialized")

    current_leader = await leader_election.get_current_leader()
    uptime = time.time() - leader_election.start_time if leader_election else 0

    return HealthResponse(
        status="healthy",
        node_id=NODE_ID,
        role=ROLE,
        is_leader=leader_election.is_leader if leader_election else False,
        cluster_name=CLUSTER_NAME,
        uptime_seconds=uptime,
        leader_id=current_leader
    )

@app.get("/api/v1/state/{key}", response_model=StateResponse)
async def get_state(key: str):
    """
    Get state with cache-aside pattern.

    Checks local cache first, fetches from Supabase on cache miss.
    """
    if not state_manager:
        raise HTTPException(status_code=503, detail="State manager not initialized")

    state = await state_manager.get_state(key)

    return StateResponse(
        key=key,
        value=state,
        cached=key in state_manager.cache,
        updated_at=datetime.now()
    )

@app.put("/api/v1/state/{key}")
async def update_state(key: str, update: StateUpdate):
    """
    Update state (writes to Supabase first, then invalidates cache).

    This ensures Supabase remains the authoritative source.
    """
    if not state_manager:
        raise HTTPException(status_code=503, detail="State manager not initialized")

    success = await state_manager.update_state(key, update.value)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update state")

    return {
        "success": True,
        "key": key,
        "updated_at": datetime.now().isoformat()
    }

@app.post("/api/v1/sync/trigger")
async def trigger_manual_sync(
    sync_request: SyncTrigger,
    background_tasks: BackgroundTasks
):
    """
    Trigger manual sync for a client (leader only).

    Only the leader container can trigger sync operations.
    The sync runs as a background task to avoid blocking the API.
    """
    if not leader_election or not leader_election.is_leader:
        current_leader = await leader_election.get_current_leader() if leader_election else "unknown"
        raise HTTPException(
            status_code=403,
            detail=f"Only leader can trigger sync. Current leader: {current_leader}"
        )

    # Add sync job to background tasks
    background_tasks.add_task(
        execute_sync_job,
        sync_request.client_name,
        sync_request.full_sync
    )

    # Increment queue size metric
    sync_queue_size.inc()

    return {
        "status": "queued",
        "client": sync_request.client_name,
        "full_sync": sync_request.full_sync,
        "queued_at": datetime.now().isoformat()
    }

@app.get("/api/v1/cluster/status")
async def get_cluster_status():
    """
    Get cluster status including all nodes.

    Queries Supabase for all hosts and their heartbeat status.
    """
    if not state_manager or not state_manager.pool:
        raise HTTPException(status_code=503, detail="State manager not initialized")

    async with state_manager.pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM sync_metadata.v_cluster_health
            ORDER BY cluster_name, hostname
        """)

        return {
            "cluster_name": CLUSTER_NAME,
            "nodes": [dict(row) for row in rows]
        }

@app.get("/api/v1/conflicts")
async def get_conflicts(
    client_name: Optional[str] = None,
    limit: int = 100
):
    """
    Get unresolved conflicts requiring manual review.
    """
    if not conflict_resolver:
        raise HTTPException(status_code=503, detail="Conflict resolver not initialized")

    conflicts = await conflict_resolver.get_unresolved_conflicts(
        client_name=client_name,
        limit=limit
    )

    return {
        "conflicts": conflicts,
        "count": len(conflicts)
    }

# ============================================================================
# SYNC JOB EXECUTION
# ============================================================================

async def execute_sync_job(client_name: str, full_sync: bool = False):
    """
    Execute sync job as background task.

    This calls the shell script that performs the actual sync operation.
    """
    import subprocess
    import time

    logger.info(f"Starting sync job for client: {client_name} (full={full_sync})")

    sync_jobs_active.inc()
    start_time = time.time()

    try:
        # Call sync script
        script_path = "/app/scripts/sync-client-to-supabase.sh"
        args = [script_path, client_name]

        if full_sync:
            args.append("--full")

        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        duration = time.time() - start_time

        if result.returncode == 0:
            logger.info(f"✅ Sync completed for {client_name} in {duration:.2f}s")
        else:
            logger.error(
                f"❌ Sync failed for {client_name}: {result.stderr}"
            )

    except subprocess.TimeoutExpired:
        logger.error(f"⏱️  Sync timeout for {client_name} after 10 minutes")
    except Exception as e:
        logger.error(f"Error executing sync job for {client_name}: {e}", exc_info=True)
    finally:
        sync_jobs_active.dec()
        sync_queue_size.dec()

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if os.getenv('DEBUG_MODE') == 'true' else "An error occurred"
        }
    )

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Run the FastAPI application."""
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=API_PORT,
        log_level=os.getenv('LOG_LEVEL', 'info').lower(),
        access_log=True
    )

if __name__ == "__main__":
    main()
