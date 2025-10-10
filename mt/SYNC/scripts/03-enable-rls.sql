-- SQLite + Supabase Sync System - Row Level Security
-- Phase 1: Multi-Tenant Isolation via RLS
--
-- This script enables Row Level Security (RLS) on sync_metadata tables
-- to ensure that sync containers can only access data from their own host
--
-- Run this script with admin credentials (postgres user) on your Supabase project
--
-- CRITICAL: This script enables RLS on sync_metadata schema ONLY
-- DO NOT enable RLS on Open WebUI public schema tables - it breaks authentication

-- ============================================================================
-- ENABLE ROW LEVEL SECURITY
-- ============================================================================

-- Enable RLS on all sync_metadata tables
ALTER TABLE sync_metadata.hosts ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_metadata.client_deployments ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_metadata.leader_election ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_metadata.conflict_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_metadata.cache_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_metadata.sync_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_metadata.sync_progress ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- RLS POLICIES: hosts table
-- ============================================================================

-- Policy: Sync service can only see/modify its own host
DROP POLICY IF EXISTS sync_host_isolation ON sync_metadata.hosts;
CREATE POLICY sync_host_isolation ON sync_metadata.hosts
    FOR ALL
    TO sync_service
    USING (
        host_id::TEXT = current_setting('app.current_host_id', TRUE)
        OR hostname = current_setting('app.current_hostname', TRUE)
    )
    WITH CHECK (
        host_id::TEXT = current_setting('app.current_host_id', TRUE)
        OR hostname = current_setting('app.current_hostname', TRUE)
    );

-- Policy: Admin (postgres) can see all hosts
DROP POLICY IF EXISTS admin_full_access_hosts ON sync_metadata.hosts;
CREATE POLICY admin_full_access_hosts ON sync_metadata.hosts
    FOR ALL
    TO postgres
    USING (TRUE)
    WITH CHECK (TRUE);

COMMENT ON POLICY sync_host_isolation ON sync_metadata.hosts IS
    'Isolates sync_service to only access its own host data';

-- ============================================================================
-- RLS POLICIES: client_deployments table
-- ============================================================================

-- Policy: Sync service can only see deployments on its own host
DROP POLICY IF EXISTS sync_deployment_isolation ON sync_metadata.client_deployments;
CREATE POLICY sync_deployment_isolation ON sync_metadata.client_deployments
    FOR ALL
    TO sync_service
    USING (
        host_id::TEXT = current_setting('app.current_host_id', TRUE)
        OR client_name = current_setting('app.current_client_name', TRUE)
    )
    WITH CHECK (
        host_id::TEXT = current_setting('app.current_host_id', TRUE)
        OR client_name = current_setting('app.current_client_name', TRUE)
    );

-- Policy: Admin (postgres) can see all deployments
DROP POLICY IF EXISTS admin_full_access_deployments ON sync_metadata.client_deployments;
CREATE POLICY admin_full_access_deployments ON sync_metadata.client_deployments
    FOR ALL
    TO postgres
    USING (TRUE)
    WITH CHECK (TRUE);

COMMENT ON POLICY sync_deployment_isolation ON sync_metadata.client_deployments IS
    'Isolates sync_service to only access deployments on its own host';

-- ============================================================================
-- RLS POLICIES: leader_election table
-- ============================================================================

-- Policy: Sync service can access leader election for its cluster only
DROP POLICY IF EXISTS sync_leader_cluster_isolation ON sync_metadata.leader_election;
CREATE POLICY sync_leader_cluster_isolation ON sync_metadata.leader_election
    FOR ALL
    TO sync_service
    USING (
        cluster_name = current_setting('app.current_cluster_name', TRUE)
    )
    WITH CHECK (
        cluster_name = current_setting('app.current_cluster_name', TRUE)
    );

-- Policy: Admin (postgres) can see all leader elections
DROP POLICY IF EXISTS admin_full_access_leader ON sync_metadata.leader_election;
CREATE POLICY admin_full_access_leader ON sync_metadata.leader_election
    FOR ALL
    TO postgres
    USING (TRUE)
    WITH CHECK (TRUE);

COMMENT ON POLICY sync_leader_cluster_isolation ON sync_metadata.leader_election IS
    'Isolates sync_service to only access leader election for its cluster';

-- ============================================================================
-- RLS POLICIES: conflict_log table
-- ============================================================================

-- Policy: Sync service can only see conflicts for deployments on its host
DROP POLICY IF EXISTS sync_conflict_isolation ON sync_metadata.conflict_log;
CREATE POLICY sync_conflict_isolation ON sync_metadata.conflict_log
    FOR ALL
    TO sync_service
    USING (
        EXISTS (
            SELECT 1 FROM sync_metadata.client_deployments cd
            WHERE cd.deployment_id = conflict_log.deployment_id
              AND (cd.host_id::TEXT = current_setting('app.current_host_id', TRUE)
                   OR cd.client_name = current_setting('app.current_client_name', TRUE))
        )
        OR client_name = current_setting('app.current_client_name', TRUE)
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM sync_metadata.client_deployments cd
            WHERE cd.deployment_id = conflict_log.deployment_id
              AND (cd.host_id::TEXT = current_setting('app.current_host_id', TRUE)
                   OR cd.client_name = current_setting('app.current_client_name', TRUE))
        )
        OR client_name = current_setting('app.current_client_name', TRUE)
    );

-- Policy: Admin (postgres) can see all conflicts
DROP POLICY IF EXISTS admin_full_access_conflicts ON sync_metadata.conflict_log;
CREATE POLICY admin_full_access_conflicts ON sync_metadata.conflict_log
    FOR ALL
    TO postgres
    USING (TRUE)
    WITH CHECK (TRUE);

COMMENT ON POLICY sync_conflict_isolation ON sync_metadata.conflict_log IS
    'Isolates sync_service to only see conflicts for deployments on its host';

-- ============================================================================
-- RLS POLICIES: cache_events table
-- ============================================================================

-- Policy: Sync service can only see cache events for its host
DROP POLICY IF EXISTS sync_cache_events_isolation ON sync_metadata.cache_events;
CREATE POLICY sync_cache_events_isolation ON sync_metadata.cache_events
    FOR ALL
    TO sync_service
    USING (
        host_id::TEXT = current_setting('app.current_host_id', TRUE)
    )
    WITH CHECK (
        host_id::TEXT = current_setting('app.current_host_id', TRUE)
    );

-- Policy: Admin (postgres) can see all cache events
DROP POLICY IF EXISTS admin_full_access_cache_events ON sync_metadata.cache_events;
CREATE POLICY admin_full_access_cache_events ON sync_metadata.cache_events
    FOR ALL
    TO postgres
    USING (TRUE)
    WITH CHECK (TRUE);

COMMENT ON POLICY sync_cache_events_isolation ON sync_metadata.cache_events IS
    'Isolates sync_service to only see cache events for its host';

-- ============================================================================
-- RLS POLICIES: sync_jobs table
-- ============================================================================

-- Policy: Sync service can only see sync jobs for deployments on its host
DROP POLICY IF EXISTS sync_jobs_isolation ON sync_metadata.sync_jobs;
CREATE POLICY sync_jobs_isolation ON sync_metadata.sync_jobs
    FOR ALL
    TO sync_service
    USING (
        EXISTS (
            SELECT 1 FROM sync_metadata.client_deployments cd
            WHERE cd.deployment_id = sync_jobs.deployment_id
              AND (cd.host_id::TEXT = current_setting('app.current_host_id', TRUE)
                   OR cd.client_name = current_setting('app.current_client_name', TRUE))
        )
        OR client_name = current_setting('app.current_client_name', TRUE)
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM sync_metadata.client_deployments cd
            WHERE cd.deployment_id = sync_jobs.deployment_id
              AND (cd.host_id::TEXT = current_setting('app.current_host_id', TRUE)
                   OR cd.client_name = current_setting('app.current_client_name', TRUE))
        )
        OR client_name = current_setting('app.current_client_name', TRUE)
    );

-- Policy: Admin (postgres) can see all sync jobs
DROP POLICY IF EXISTS admin_full_access_sync_jobs ON sync_metadata.sync_jobs;
CREATE POLICY admin_full_access_sync_jobs ON sync_metadata.sync_jobs
    FOR ALL
    TO postgres
    USING (TRUE)
    WITH CHECK (TRUE);

COMMENT ON POLICY sync_jobs_isolation ON sync_metadata.sync_jobs IS
    'Isolates sync_service to only see sync jobs for deployments on its host';

-- ============================================================================
-- RLS POLICIES: sync_progress table
-- ============================================================================

-- Policy: Sync service can only see progress for jobs on its host
DROP POLICY IF EXISTS sync_progress_isolation ON sync_metadata.sync_progress;
CREATE POLICY sync_progress_isolation ON sync_metadata.sync_progress
    FOR ALL
    TO sync_service
    USING (
        EXISTS (
            SELECT 1 FROM sync_metadata.sync_jobs sj
            JOIN sync_metadata.client_deployments cd ON sj.deployment_id = cd.deployment_id
            WHERE sj.job_id = sync_progress.job_id
              AND (cd.host_id::TEXT = current_setting('app.current_host_id', TRUE)
                   OR cd.client_name = current_setting('app.current_client_name', TRUE))
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM sync_metadata.sync_jobs sj
            JOIN sync_metadata.client_deployments cd ON sj.deployment_id = cd.deployment_id
            WHERE sj.job_id = sync_progress.job_id
              AND (cd.host_id::TEXT = current_setting('app.current_host_id', TRUE)
                   OR cd.client_name = current_setting('app.current_client_name', TRUE))
        )
    );

-- Policy: Admin (postgres) can see all progress
DROP POLICY IF EXISTS admin_full_access_sync_progress ON sync_metadata.sync_progress;
CREATE POLICY admin_full_access_sync_progress ON sync_metadata.sync_progress
    FOR ALL
    TO postgres
    USING (TRUE)
    WITH CHECK (TRUE);

COMMENT ON POLICY sync_progress_isolation ON sync_metadata.sync_progress IS
    'Isolates sync_service to only see sync progress for jobs on its host';

-- ============================================================================
-- HELPER FUNCTION: Set Session Context
-- ============================================================================

CREATE OR REPLACE FUNCTION sync_metadata.set_sync_context(
    p_host_id UUID,
    p_hostname TEXT DEFAULT NULL,
    p_cluster_name TEXT DEFAULT NULL,
    p_client_name TEXT DEFAULT NULL
)
RETURNS TEXT AS $$
BEGIN
    -- Set session variables for RLS policies
    PERFORM set_config('app.current_host_id', p_host_id::TEXT, FALSE);

    IF p_hostname IS NOT NULL THEN
        PERFORM set_config('app.current_hostname', p_hostname, FALSE);
    END IF;

    IF p_cluster_name IS NOT NULL THEN
        PERFORM set_config('app.current_cluster_name', p_cluster_name, FALSE);
    END IF;

    IF p_client_name IS NOT NULL THEN
        PERFORM set_config('app.current_client_name', p_client_name, FALSE);
    END IF;

    RETURN format('✅ Sync context set: host_id=%s, hostname=%s, cluster=%s, client=%s',
                  p_host_id, COALESCE(p_hostname, 'NULL'),
                  COALESCE(p_cluster_name, 'NULL'), COALESCE(p_client_name, 'NULL'));
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION sync_metadata.set_sync_context IS
    'Set session context variables for RLS policies - call this before sync operations';

-- ============================================================================
-- VALIDATION FUNCTION
-- ============================================================================

CREATE OR REPLACE FUNCTION sync_metadata.test_rls_isolation()
RETURNS TABLE (
    test_name TEXT,
    test_result TEXT,
    details TEXT
) AS $$
DECLARE
    test_host_id_1 UUID;
    test_host_id_2 UUID;
    visible_count INTEGER;
BEGIN
    -- Create two test hosts
    INSERT INTO sync_metadata.hosts (hostname, cluster_name)
    VALUES ('rls-test-host-1', 'test-cluster')
    RETURNING host_id INTO test_host_id_1;

    INSERT INTO sync_metadata.hosts (hostname, cluster_name)
    VALUES ('rls-test-host-2', 'test-cluster')
    RETURNING host_id INTO test_host_id_2;

    -- Test 1: Set context to host 1, should only see host 1
    PERFORM sync_metadata.set_sync_context(test_host_id_1, 'rls-test-host-1', 'test-cluster');

    SELECT COUNT(*) INTO visible_count
    FROM sync_metadata.hosts
    WHERE cluster_name = 'test-cluster';

    IF visible_count = 1 THEN
        RETURN QUERY SELECT 'RLS Isolation Test'::TEXT, 'PASS'::TEXT,
            format('sync_service can only see its own host (%s rows visible)', visible_count)::TEXT;
    ELSE
        RETURN QUERY SELECT 'RLS Isolation Test'::TEXT, 'FAIL'::TEXT,
            format('Expected 1 row, but got %s rows - RLS not working!', visible_count)::TEXT;
    END IF;

    -- Cleanup
    DELETE FROM sync_metadata.hosts WHERE host_id IN (test_host_id_1, test_host_id_2);

    RETURN;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION sync_metadata.test_rls_isolation() IS
    'Test RLS policies to ensure proper isolation - run as postgres admin';

-- ============================================================================
-- SECURITY VALIDATION
-- ============================================================================

DO $$
DECLARE
    rls_enabled_count INTEGER;
BEGIN
    -- Count tables with RLS enabled in sync_metadata
    SELECT COUNT(*) INTO rls_enabled_count
    FROM pg_tables t
    JOIN pg_class c ON t.tablename = c.relname
    WHERE t.schemaname = 'sync_metadata'
      AND c.relrowsecurity = TRUE;

    IF rls_enabled_count = 7 THEN
        RAISE NOTICE '✅ RLS enabled on all 7 sync_metadata tables';
    ELSE
        RAISE WARNING '⚠️  RLS enabled on %/7 tables - check configuration', rls_enabled_count;
    END IF;

    -- Verify policies exist
    IF EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'sync_metadata'
          AND policyname LIKE 'sync_%_isolation'
    ) THEN
        RAISE NOTICE '✅ RLS isolation policies created';
    ELSE
        RAISE WARNING '⚠️  RLS policies not found - check policy creation';
    END IF;
END $$;

-- ============================================================================
-- COMPLETION MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Row Level Security Enabled';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'RLS enabled on 7 tables:';
    RAISE NOTICE '  - hosts';
    RAISE NOTICE '  - client_deployments';
    RAISE NOTICE '  - leader_election';
    RAISE NOTICE '  - conflict_log';
    RAISE NOTICE '  - cache_events';
    RAISE NOTICE '  - sync_jobs';
    RAISE NOTICE '  - sync_progress';
    RAISE NOTICE '';
    RAISE NOTICE 'Isolation policies created for sync_service role';
    RAISE NOTICE 'Admin (postgres) role has full access to all rows';
    RAISE NOTICE '';
    RAISE NOTICE 'Usage in Python (asyncpg):';
    RAISE NOTICE '  await conn.execute(';
    RAISE NOTICE '    "SELECT sync_metadata.set_sync_context($1, $2, $3)",';
    RAISE NOTICE '    host_id, hostname, cluster_name';
    RAISE NOTICE '  )';
    RAISE NOTICE '';
    RAISE NOTICE 'Test RLS isolation:';
    RAISE NOTICE '  SELECT * FROM sync_metadata.test_rls_isolation();';
    RAISE NOTICE '';
END $$;
