-- SQLite + Supabase Sync System - Schema Initialization
-- Phase 1: High Availability Sync with State Management
--
-- This script creates the sync_metadata schema and all required tables
-- for managing multi-tenant Open WebUI synchronization
--
-- Run this script with admin credentials (postgres user) on your Supabase project

-- ============================================================================
-- SCHEMA CREATION
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS sync_metadata;

-- ============================================================================
-- TABLE: hosts
-- Tracks physical servers running sync containers
-- ============================================================================

CREATE TABLE IF NOT EXISTS sync_metadata.hosts (
    host_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hostname VARCHAR(255) NOT NULL,
    ip_address INET,
    cluster_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'maintenance', 'offline')),
    last_heartbeat TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,

    CONSTRAINT unique_hostname_cluster UNIQUE (hostname, cluster_name)
);

CREATE INDEX idx_hosts_cluster ON sync_metadata.hosts(cluster_name);
CREATE INDEX idx_hosts_status ON sync_metadata.hosts(status) WHERE status = 'active';
CREATE INDEX idx_hosts_heartbeat ON sync_metadata.hosts(last_heartbeat);

COMMENT ON TABLE sync_metadata.hosts IS 'Physical servers running sync containers';
COMMENT ON COLUMN sync_metadata.hosts.metadata IS 'Additional host information (CPU, memory, disk, etc.)';

-- ============================================================================
-- TABLE: client_deployments
-- Tracks Open WebUI client container deployments
-- ============================================================================

CREATE TABLE IF NOT EXISTS sync_metadata.client_deployments (
    deployment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    host_id UUID REFERENCES sync_metadata.hosts(host_id) ON DELETE CASCADE,
    client_name VARCHAR(100) NOT NULL,
    container_name VARCHAR(255) NOT NULL,
    fqdn VARCHAR(255),
    port INTEGER,
    database_type VARCHAR(20) DEFAULT 'sqlite' CHECK (database_type IN ('sqlite', 'postgresql')),

    -- Sync configuration
    sync_enabled BOOLEAN DEFAULT false,
    sync_interval INTEGER DEFAULT 300, -- seconds (5 minutes default)
    last_sync_at TIMESTAMP,
    last_sync_status VARCHAR(20) CHECK (last_sync_status IN ('success', 'failed', 'running', 'pending')),
    next_sync_at TIMESTAMP,

    -- State tracking
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'paused', 'migrating', 'stopped')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Additional configuration
    config JSONB DEFAULT '{}'::jsonb,

    CONSTRAINT unique_client_name UNIQUE (client_name),
    CONSTRAINT unique_container_name UNIQUE (container_name)
);

CREATE INDEX idx_deployments_host ON sync_metadata.client_deployments(host_id);
CREATE INDEX idx_deployments_sync_enabled ON sync_metadata.client_deployments(sync_enabled) WHERE sync_enabled = true;
CREATE INDEX idx_deployments_next_sync ON sync_metadata.client_deployments(next_sync_at) WHERE sync_enabled = true;
CREATE INDEX idx_deployments_status ON sync_metadata.client_deployments(status);

COMMENT ON TABLE sync_metadata.client_deployments IS 'Open WebUI client container deployments';
COMMENT ON COLUMN sync_metadata.client_deployments.config IS 'Client-specific configuration (conflict resolution, custom sync rules, etc.)';

-- ============================================================================
-- TABLE: leader_election
-- Manages distributed leader election for HA sync containers
-- ============================================================================

CREATE TABLE IF NOT EXISTS sync_metadata.leader_election (
    cluster_name VARCHAR(100) PRIMARY KEY,
    leader_id VARCHAR(100) NOT NULL,
    leader_host_id UUID REFERENCES sync_metadata.hosts(host_id) ON DELETE CASCADE,
    acquired_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    heartbeat_count INTEGER DEFAULT 0,

    CONSTRAINT valid_lease_duration CHECK (expires_at > acquired_at)
);

CREATE INDEX idx_leader_expires ON sync_metadata.leader_election(expires_at);
CREATE INDEX idx_leader_host ON sync_metadata.leader_election(leader_host_id);

COMMENT ON TABLE sync_metadata.leader_election IS 'Distributed leader election for HA sync containers';
COMMENT ON COLUMN sync_metadata.leader_election.heartbeat_count IS 'Number of heartbeats since becoming leader (for monitoring)';

-- ============================================================================
-- TABLE: conflict_log
-- Logs all detected conflicts and their resolutions
-- ============================================================================

CREATE TABLE IF NOT EXISTS sync_metadata.conflict_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deployment_id UUID REFERENCES sync_metadata.client_deployments(deployment_id) ON DELETE CASCADE,
    client_name VARCHAR(100) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    record_id VARCHAR(255),

    -- Conflict details
    conflict_type VARCHAR(50) NOT NULL CHECK (conflict_type IN ('update_conflict', 'delete_conflict', 'constraint_violation', 'type_mismatch', 'custom')),
    source_data JSONB,
    target_data JSONB,

    -- Resolution details
    resolution_strategy VARCHAR(50) CHECK (resolution_strategy IN ('newest_wins', 'source_wins', 'target_wins', 'merge', 'manual')),
    resolved_data JSONB,
    detected_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(100), -- 'automatic' or username for manual resolution
    resolution_notes TEXT,

    -- Audit
    sync_job_id UUID
);

CREATE INDEX idx_conflicts_deployment ON sync_metadata.conflict_log(deployment_id);
CREATE INDEX idx_conflicts_client ON sync_metadata.conflict_log(client_name, detected_at DESC);
CREATE INDEX idx_conflicts_table ON sync_metadata.conflict_log(table_name);
CREATE INDEX idx_conflicts_unresolved ON sync_metadata.conflict_log(resolved_at) WHERE resolved_at IS NULL;
CREATE INDEX idx_conflicts_type ON sync_metadata.conflict_log(conflict_type);

COMMENT ON TABLE sync_metadata.conflict_log IS 'Audit log of all sync conflicts and resolutions';
COMMENT ON COLUMN sync_metadata.conflict_log.source_data IS 'Data from SQLite (before conflict)';
COMMENT ON COLUMN sync_metadata.conflict_log.target_data IS 'Data from Supabase (conflicting)';

-- ============================================================================
-- TABLE: cache_events
-- State cache invalidation events for cluster synchronization
-- ============================================================================

CREATE TABLE IF NOT EXISTS sync_metadata.cache_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    host_id UUID REFERENCES sync_metadata.hosts(host_id) ON DELETE CASCADE,
    cache_key VARCHAR(255) NOT NULL,
    action VARCHAR(20) NOT NULL CHECK (action IN ('invalidate', 'refresh', 'delete')),
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    processed_by VARCHAR(100), -- container ID that processed the event

    CONSTRAINT future_processed CHECK (processed_at IS NULL OR processed_at >= created_at)
);

CREATE INDEX idx_cache_events_host ON sync_metadata.cache_events(host_id);
CREATE INDEX idx_cache_events_unprocessed ON sync_metadata.cache_events(host_id, processed_at, created_at)
    WHERE processed_at IS NULL;
CREATE INDEX idx_cache_events_key ON sync_metadata.cache_events(cache_key);

COMMENT ON TABLE sync_metadata.cache_events IS 'Cache invalidation events for cluster state synchronization';
COMMENT ON COLUMN sync_metadata.cache_events.processed_by IS 'Container ID that acknowledged and processed this event';

-- ============================================================================
-- TABLE: sync_jobs
-- Tracks individual sync operations for monitoring and debugging
-- ============================================================================

CREATE TABLE IF NOT EXISTS sync_metadata.sync_jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deployment_id UUID REFERENCES sync_metadata.client_deployments(deployment_id) ON DELETE CASCADE,
    client_name VARCHAR(100) NOT NULL,

    -- Job details
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'running' CHECK (status IN ('running', 'success', 'failed', 'cancelled')),

    -- Progress tracking
    tables_synced INTEGER DEFAULT 0,
    tables_total INTEGER,
    rows_synced INTEGER DEFAULT 0,
    rows_failed INTEGER DEFAULT 0,

    -- Performance metrics
    duration_seconds NUMERIC(10, 2),
    bytes_transferred BIGINT,

    -- Error handling
    error_message TEXT,
    error_details JSONB,

    -- Conflict tracking
    conflicts_detected INTEGER DEFAULT 0,
    conflicts_resolved INTEGER DEFAULT 0,

    -- Metadata
    triggered_by VARCHAR(100), -- 'scheduler', 'manual', 'api', username
    sync_type VARCHAR(20) DEFAULT 'incremental' CHECK (sync_type IN ('full', 'incremental', 'manual')),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_sync_jobs_deployment ON sync_metadata.sync_jobs(deployment_id);
CREATE INDEX idx_sync_jobs_client ON sync_metadata.sync_jobs(client_name, started_at DESC);
CREATE INDEX idx_sync_jobs_status ON sync_metadata.sync_jobs(status, started_at DESC);
CREATE INDEX idx_sync_jobs_running ON sync_metadata.sync_jobs(started_at) WHERE status = 'running';

COMMENT ON TABLE sync_metadata.sync_jobs IS 'Individual sync operation tracking for monitoring and debugging';
COMMENT ON COLUMN sync_metadata.sync_jobs.metadata IS 'Additional job information (source version, schema hash, etc.)';

-- ============================================================================
-- TABLE: sync_progress
-- Real-time progress tracking for long-running sync operations
-- ============================================================================

CREATE TABLE IF NOT EXISTS sync_metadata.sync_progress (
    progress_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES sync_metadata.sync_jobs(job_id) ON DELETE CASCADE,
    table_name VARCHAR(100) NOT NULL,

    -- Progress details
    rows_total INTEGER,
    rows_processed INTEGER DEFAULT 0,
    rows_failed INTEGER DEFAULT 0,

    -- Timing
    started_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,

    -- Status
    status VARCHAR(20) DEFAULT 'running' CHECK (status IN ('running', 'success', 'failed')),
    error_message TEXT,

    CONSTRAINT unique_job_table UNIQUE (job_id, table_name)
);

CREATE INDEX idx_sync_progress_job ON sync_metadata.sync_progress(job_id);
CREATE INDEX idx_sync_progress_running ON sync_metadata.sync_progress(job_id, status) WHERE status = 'running';

COMMENT ON TABLE sync_metadata.sync_progress IS 'Real-time progress tracking for individual table syncs';

-- ============================================================================
-- TRIGGERS: Automatic timestamp updates
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION sync_metadata.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to relevant tables
CREATE TRIGGER update_hosts_updated_at
    BEFORE UPDATE ON sync_metadata.hosts
    FOR EACH ROW
    EXECUTE FUNCTION sync_metadata.update_updated_at_column();

CREATE TRIGGER update_deployments_updated_at
    BEFORE UPDATE ON sync_metadata.client_deployments
    FOR EACH ROW
    EXECUTE FUNCTION sync_metadata.update_updated_at_column();

CREATE TRIGGER update_sync_progress_updated_at
    BEFORE UPDATE ON sync_metadata.sync_progress
    FOR EACH ROW
    EXECUTE FUNCTION sync_metadata.update_updated_at_column();

-- ============================================================================
-- TRIGGERS: Automatic job completion tracking
-- ============================================================================

CREATE OR REPLACE FUNCTION sync_metadata.update_job_completion()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status IN ('success', 'failed', 'cancelled') AND OLD.status = 'running' THEN
        NEW.completed_at = NOW();
        NEW.duration_seconds = EXTRACT(EPOCH FROM (NOW() - NEW.started_at));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_sync_job_completion
    BEFORE UPDATE ON sync_metadata.sync_jobs
    FOR EACH ROW
    EXECUTE FUNCTION sync_metadata.update_job_completion();

-- ============================================================================
-- VIEWS: Convenient monitoring queries
-- ============================================================================

-- Active sync jobs with progress
CREATE OR REPLACE VIEW sync_metadata.v_active_sync_jobs AS
SELECT
    j.job_id,
    j.client_name,
    j.started_at,
    j.tables_synced,
    j.tables_total,
    ROUND((j.tables_synced::NUMERIC / NULLIF(j.tables_total, 0)) * 100, 2) AS percent_complete,
    j.rows_synced,
    j.rows_failed,
    j.conflicts_detected,
    j.conflicts_resolved,
    EXTRACT(EPOCH FROM (NOW() - j.started_at))::INTEGER AS runtime_seconds
FROM
    sync_metadata.sync_jobs j
WHERE
    j.status = 'running'
ORDER BY
    j.started_at DESC;

COMMENT ON VIEW sync_metadata.v_active_sync_jobs IS 'Currently running sync jobs with progress metrics';

-- Recent conflicts by client
CREATE OR REPLACE VIEW sync_metadata.v_recent_conflicts AS
SELECT
    c.client_name,
    c.table_name,
    c.conflict_type,
    c.resolution_strategy,
    c.detected_at,
    c.resolved_at,
    EXTRACT(EPOCH FROM (COALESCE(c.resolved_at, NOW()) - c.detected_at))::INTEGER AS resolution_time_seconds,
    CASE
        WHEN c.resolved_at IS NULL THEN 'unresolved'
        WHEN c.resolved_by = 'automatic' THEN 'auto-resolved'
        ELSE 'manually-resolved'
    END AS resolution_type
FROM
    sync_metadata.conflict_log c
WHERE
    c.detected_at > NOW() - INTERVAL '24 hours'
ORDER BY
    c.detected_at DESC;

COMMENT ON VIEW sync_metadata.v_recent_conflicts IS 'Conflicts detected in the last 24 hours';

-- Cluster health status
CREATE OR REPLACE VIEW sync_metadata.v_cluster_health AS
SELECT
    h.cluster_name,
    h.hostname,
    h.status AS host_status,
    h.last_heartbeat,
    EXTRACT(EPOCH FROM (NOW() - h.last_heartbeat))::INTEGER AS seconds_since_heartbeat,
    le.leader_id,
    CASE
        WHEN le.leader_id IS NOT NULL AND le.expires_at > NOW() THEN 'leader'
        ELSE 'follower'
    END AS leader_status,
    le.expires_at AS leader_lease_expires,
    COUNT(DISTINCT cd.deployment_id) AS deployments_count,
    COUNT(DISTINCT cd.deployment_id) FILTER (WHERE cd.sync_enabled = true) AS sync_enabled_count
FROM
    sync_metadata.hosts h
LEFT JOIN
    sync_metadata.leader_election le ON h.cluster_name = le.cluster_name
LEFT JOIN
    sync_metadata.client_deployments cd ON h.host_id = cd.host_id
GROUP BY
    h.cluster_name, h.hostname, h.status, h.last_heartbeat, le.leader_id, le.expires_at
ORDER BY
    h.cluster_name, h.hostname;

COMMENT ON VIEW sync_metadata.v_cluster_health IS 'Cluster health overview with leader status and deployment counts';

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

-- Grant schema usage to public (will be restricted via RLS)
GRANT USAGE ON SCHEMA sync_metadata TO PUBLIC;

-- Grant permissions on all tables to postgres (admin)
GRANT ALL ON ALL TABLES IN SCHEMA sync_metadata TO postgres;
GRANT ALL ON ALL SEQUENCES IN SCHEMA sync_metadata TO postgres;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA sync_metadata TO postgres;

-- Grant read access to views
GRANT SELECT ON ALL TABLES IN SCHEMA sync_metadata TO PUBLIC;

-- ============================================================================
-- COMPLETION MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Sync Metadata Schema Initialized';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Tables created: hosts, client_deployments, leader_election, conflict_log, cache_events, sync_jobs, sync_progress';
    RAISE NOTICE 'Views created: v_active_sync_jobs, v_recent_conflicts, v_cluster_health';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Run 02-create-sync-role.sql to create restricted sync_service role';
    RAISE NOTICE '2. Run 03-enable-rls.sql to enable row-level security';
    RAISE NOTICE '';
END $$;
