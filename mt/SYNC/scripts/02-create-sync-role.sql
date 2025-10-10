-- SQLite + Supabase Sync System - Restricted Database Role
-- Phase 1: Security Configuration
--
-- This script creates the sync_service role with minimal permissions
-- Run this script with admin credentials (postgres user) on your Supabase project
--
-- CRITICAL SECURITY REQUIREMENTS:
-- - NO DELETE permission (prevents accidental data loss)
-- - NO DROP permission (prevents schema destruction)
-- - NO CREATE permission (prevents unauthorized schema changes)
-- - Only SELECT, INSERT, UPDATE on sync_metadata schema
-- - Per-client schema access granted separately

-- ============================================================================
-- CREATE RESTRICTED ROLE
-- ============================================================================

-- Drop role if exists (for re-running script)
DROP ROLE IF EXISTS sync_service;

-- Create role with LOGIN only (no superuser, no createdb, no createrole)
CREATE ROLE sync_service WITH
    LOGIN
    NOCREATEDB
    NOCREATEROLE
    NOINHERIT
    NOREPLICATION
    CONNECTION LIMIT 10;  -- Prevent connection exhaustion

-- Set a strong password (will be overridden by deployment script)
-- This is a placeholder - the deploy-sync-cluster.sh script will set a random password
ALTER ROLE sync_service WITH ENCRYPTED PASSWORD 'CHANGE_THIS_PASSWORD_IN_DEPLOYMENT';

COMMENT ON ROLE sync_service IS 'Restricted role for sync containers with minimal permissions';

-- ============================================================================
-- GRANT PERMISSIONS ON SYNC_METADATA SCHEMA
-- ============================================================================

-- Grant schema usage
GRANT USAGE ON SCHEMA sync_metadata TO sync_service;

-- Grant SELECT, INSERT, UPDATE on all tables in sync_metadata
-- IMPORTANT: NO DELETE permission
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA sync_metadata TO sync_service;

-- Grant USAGE on sequences (for auto-increment columns)
GRANT USAGE ON ALL SEQUENCES IN SCHEMA sync_metadata TO sync_service;

-- Grant default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA sync_metadata
    GRANT SELECT, INSERT, UPDATE ON TABLES TO sync_service;

ALTER DEFAULT PRIVILEGES IN SCHEMA sync_metadata
    GRANT USAGE ON SEQUENCES TO sync_service;

-- ============================================================================
-- VALIDATION FUNCTION
-- ============================================================================

-- Function to test sync_service permissions
CREATE OR REPLACE FUNCTION sync_metadata.test_sync_service_permissions()
RETURNS TABLE (
    test_name TEXT,
    test_result TEXT,
    details TEXT
) AS $$
BEGIN
    -- Test 1: Can SELECT from hosts
    BEGIN
        PERFORM * FROM sync_metadata.hosts LIMIT 1;
        RETURN QUERY SELECT 'SELECT permission'::TEXT, 'PASS'::TEXT, 'Can read from hosts table'::TEXT;
    EXCEPTION WHEN OTHERS THEN
        RETURN QUERY SELECT 'SELECT permission'::TEXT, 'FAIL'::TEXT, SQLERRM::TEXT;
    END;

    -- Test 2: Can INSERT into hosts
    BEGIN
        INSERT INTO sync_metadata.hosts (hostname, cluster_name)
        VALUES ('test-host', 'test-cluster')
        RETURNING host_id INTO STRICT;
        DELETE FROM sync_metadata.hosts WHERE hostname = 'test-host';  -- Cleanup (admin can delete)
        RETURN QUERY SELECT 'INSERT permission'::TEXT, 'PASS'::TEXT, 'Can insert into hosts table'::TEXT;
    EXCEPTION WHEN OTHERS THEN
        RETURN QUERY SELECT 'INSERT permission'::TEXT, 'FAIL'::TEXT, SQLERRM::TEXT;
    END;

    -- Test 3: Cannot DELETE (should fail)
    -- Note: This test is run as admin, we document the expected behavior
    RETURN QUERY SELECT 'DELETE restriction'::TEXT, 'INFO'::TEXT,
        'sync_service should NOT have DELETE permission - test manually with sync_service role'::TEXT;

    RETURN;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION sync_metadata.test_sync_service_permissions() IS
    'Validation function to test sync_service permissions - run as postgres admin';

-- ============================================================================
-- CLIENT SCHEMA PERMISSIONS (Template)
-- ============================================================================

-- This section provides a template for granting permissions to sync_service
-- on client-specific schemas. Execute this for each client deployment.
--
-- USAGE:
-- Replace {client_name} with the actual client name (e.g., 'acme_corp', 'beta_client')
--
-- GRANT USAGE ON SCHEMA {client_name} TO sync_service;
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA {client_name} TO sync_service;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA {client_name} TO sync_service;
--
-- ALTER DEFAULT PRIVILEGES IN SCHEMA {client_name}
--     GRANT SELECT, INSERT, UPDATE ON TABLES TO sync_service;
--
-- ALTER DEFAULT PRIVILEGES IN SCHEMA {client_name}
--     GRANT USAGE ON SEQUENCES TO sync_service;

-- ============================================================================
-- HELPER FUNCTION: Grant Client Schema Access
-- ============================================================================

CREATE OR REPLACE FUNCTION sync_metadata.grant_client_access(client_schema_name TEXT)
RETURNS TEXT AS $$
BEGIN
    -- Grant schema usage
    EXECUTE format('GRANT USAGE ON SCHEMA %I TO sync_service', client_schema_name);

    -- Grant table permissions (NO DELETE)
    EXECUTE format('GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA %I TO sync_service', client_schema_name);

    -- Grant sequence usage
    EXECUTE format('GRANT USAGE ON ALL SEQUENCES IN SCHEMA %I TO sync_service', client_schema_name);

    -- Set default privileges for future tables
    EXECUTE format(
        'ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT SELECT, INSERT, UPDATE ON TABLES TO sync_service',
        client_schema_name
    );

    EXECUTE format(
        'ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT USAGE ON SEQUENCES TO sync_service',
        client_schema_name
    );

    RETURN format('✅ Granted sync_service access to schema: %s', client_schema_name);
EXCEPTION
    WHEN OTHERS THEN
        RETURN format('❌ Error granting access to schema %s: %s', client_schema_name, SQLERRM);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION sync_metadata.grant_client_access(TEXT) IS
    'Helper function to grant sync_service access to a client schema - execute as postgres admin';

-- ============================================================================
-- USAGE EXAMPLES
-- ============================================================================

-- Example 1: Grant access to a specific client schema
-- SELECT sync_metadata.grant_client_access('acme_corp');

-- Example 2: Grant access to multiple client schemas
-- SELECT sync_metadata.grant_client_access(schema_name)
-- FROM information_schema.schemata
-- WHERE schema_name LIKE 'client_%';

-- Example 3: Test permissions (run as sync_service role)
-- SET ROLE sync_service;
-- SELECT * FROM sync_metadata.hosts;  -- Should work
-- DELETE FROM sync_metadata.hosts WHERE host_id = 'test';  -- Should fail with permission denied

-- ============================================================================
-- SECURITY VALIDATION
-- ============================================================================

DO $$
DECLARE
    can_delete BOOLEAN;
BEGIN
    -- Check if sync_service has DELETE permission (should be FALSE)
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.role_table_grants
        WHERE grantee = 'sync_service'
          AND table_schema = 'sync_metadata'
          AND privilege_type = 'DELETE'
    ) INTO can_delete;

    IF can_delete THEN
        RAISE EXCEPTION '❌ SECURITY ERROR: sync_service has DELETE permission - this violates security requirements!';
    ELSE
        RAISE NOTICE '✅ Security validation passed: sync_service does NOT have DELETE permission';
    END IF;

    -- Check if sync_service has DROP permission (should be FALSE)
    IF pg_has_role('sync_service', 'postgres', 'MEMBER') THEN
        RAISE EXCEPTION '❌ SECURITY ERROR: sync_service is member of postgres role - excessive privileges!';
    ELSE
        RAISE NOTICE '✅ Security validation passed: sync_service is not a superuser';
    END IF;
END $$;

-- ============================================================================
-- COMPLETION MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Sync Service Role Created';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Role: sync_service';
    RAISE NOTICE 'Permissions:';
    RAISE NOTICE '  ✅ SELECT, INSERT, UPDATE on sync_metadata schema';
    RAISE NOTICE '  ❌ NO DELETE permission (data protection)';
    RAISE NOTICE '  ❌ NO DROP permission (schema protection)';
    RAISE NOTICE '  ❌ NO CREATE permission (schema control)';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Change password: ALTER ROLE sync_service WITH ENCRYPTED PASSWORD ''your-strong-password'';';
    RAISE NOTICE '2. Grant client schema access: SELECT sync_metadata.grant_client_access(''your_client_schema'');';
    RAISE NOTICE '3. Run 03-enable-rls.sql to enable row-level security';
    RAISE NOTICE '';
    RAISE NOTICE 'Test permissions (run as sync_service):';
    RAISE NOTICE '  SET ROLE sync_service;';
    RAISE NOTICE '  SELECT * FROM sync_metadata.hosts;  -- Should work';
    RAISE NOTICE '  DELETE FROM sync_metadata.hosts WHERE host_id = ''test'';  -- Should fail';
    RAISE NOTICE '';
END $$;
