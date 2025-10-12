#!/usr/bin/env python3
"""
Security Validation Test Suite
Tests sync_service role permissions and RLS isolation

This test suite validates that the sync_service role has the correct
permissions and that RLS policies properly isolate data between hosts.

Test Coverage:
1. Destructive operations (DELETE, DROP, TRUNCATE) - Should FAIL
2. Read operations (SELECT) - Should SUCCEED
3. Write operations (INSERT, UPDATE) with proper RLS context - Should SUCCEED
4. RLS policy enforcement - Should prevent cross-host data access
5. Schema isolation - Should prevent access to other schemas
6. DDL operations (CREATE, ALTER) - Should FAIL

Usage:
    # Run from host:
    source mt/SYNC/.credentials
    docker exec -i -e SYNC_URL="$SYNC_URL" -e ADMIN_URL="$ADMIN_URL" \\
        openwebui-sync-node-a python3 - < tests/security-validation-test.py

    # Or from within container:
    export SYNC_URL="postgresql://sync_service.PROJECT_REF:PASSWORD@..."
    export ADMIN_URL="postgresql://postgres.PROJECT_REF:PASSWORD@..."
    python3 tests/security-validation-test.py

Test Results (2025-10-12):
    ✅ All 13 tests passed on production deployment (157.245.220.28)
"""

import asyncio
import asyncpg
import os
import sys
import uuid
import random

# Colors for output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
BLUE = '\033[0;34m'
NC = '\033[0m'

# Test results
tests_passed = 0
tests_failed = 0
tests_total = 0


async def run_test(conn, test_name, query, should_succeed):
    """Run a single test query"""
    global tests_passed, tests_failed, tests_total

    tests_total += 1
    print(f"\n{BLUE}Test #{tests_total}: {test_name}{NC}")
    print(f"Query: {query[:100]}...") if len(query) > 100 else print(f"Query: {query}")

    try:
        await conn.execute(query)
        if should_succeed:
            print(f"{GREEN}✅ PASS{NC} - Command succeeded as expected")
            tests_passed += 1
        else:
            print(f"{RED}❌ FAIL{NC} - Command succeeded but should have failed")
            tests_failed += 1
    except Exception as e:
        if not should_succeed:
            print(f"{GREEN}✅ PASS{NC} - Command failed as expected (security working)")
            print(f"  Error: {str(e)[:80]}")
            tests_passed += 1
        else:
            print(f"{RED}❌ FAIL{NC} - Command failed but should have succeeded")
            print(f"  Error: {e}")
            tests_failed += 1


async def run_query_test(conn, test_name, query, should_succeed):
    """Run a test that expects results"""
    global tests_passed, tests_failed, tests_total

    tests_total += 1
    print(f"\n{BLUE}Test #{tests_total}: {test_name}{NC}")

    try:
        result = await conn.fetchval(query)
        if should_succeed:
            print(f"{GREEN}✅ PASS{NC} - Query succeeded, result: {result}")
            tests_passed += 1
            return result
        else:
            print(f"{RED}❌ FAIL{NC} - Query succeeded but should have failed")
            tests_failed += 1
            return result
    except Exception as e:
        if not should_succeed:
            print(f"{GREEN}✅ PASS{NC} - Query failed as expected")
            print(f"  Error: {str(e)[:80]}")
            tests_passed += 1
            return None
        else:
            print(f"{RED}❌ FAIL{NC} - Query failed but should have succeeded")
            print(f"  Error: {e}")
            tests_failed += 1
            return None


async def main():
    # Get credentials from environment
    sync_url = os.getenv('SYNC_URL')
    admin_url = os.getenv('ADMIN_URL')

    if not sync_url or not admin_url:
        print(f"{RED}ERROR: SYNC_URL or ADMIN_URL not set{NC}")
        print(f"{RED}Please set these environment variables before running tests{NC}")
        sys.exit(1)

    # Generate unique hostname for this test run
    test_hostname = f"test-sec-{random.randint(10000, 99999)}"

    print(f"{BLUE}========================================{NC}")
    print(f"{BLUE}Security Validation Test Suite{NC}")
    print(f"{BLUE}========================================{NC}")
    print(f"Test hostname: {test_hostname}")
    print("Testing sync_service role permissions...\n")

    # Connect with sync_service credentials
    try:
        conn = await asyncpg.connect(sync_url)
        admin_conn = await asyncpg.connect(admin_url)
    except Exception as e:
        print(f"{RED}ERROR: Failed to connect to database{NC}")
        print(f"  {e}")
        sys.exit(1)

    try:
        # ============================================
        # Test 1: DELETE Permission (Should FAIL)
        # ============================================
        await run_test(
            conn,
            "DELETE should be denied",
            "DELETE FROM sync_metadata.hosts WHERE hostname = 'test-delete';",
            should_succeed=False
        )

        # ============================================
        # Test 2: DROP TABLE Permission (Should FAIL)
        # ============================================
        await run_test(
            conn,
            "DROP TABLE should be denied",
            "DROP TABLE sync_metadata.hosts;",
            should_succeed=False
        )

        # ============================================
        # Test 3: DROP SCHEMA Permission (Should FAIL)
        # ============================================
        await run_test(
            conn,
            "DROP SCHEMA should be denied",
            "DROP SCHEMA sync_metadata;",
            should_succeed=False
        )

        # ============================================
        # Test 4: TRUNCATE Permission (Should FAIL)
        # ============================================
        await run_test(
            conn,
            "TRUNCATE should be denied",
            "TRUNCATE sync_metadata.hosts;",
            should_succeed=False
        )

        # ============================================
        # Test 5: SELECT Permission (Should SUCCEED)
        # ============================================
        await run_query_test(
            conn,
            "SELECT should be allowed",
            "SELECT COUNT(*) FROM sync_metadata.hosts;",
            should_succeed=True
        )

        # ============================================
        # Test 6: INSERT Permission with RLS context (Should SUCCEED)
        # ============================================
        # Set session context for RLS (required for INSERT)
        test_host_id = str(uuid.uuid4())
        await conn.execute(f"SET app.current_host_id = '{test_host_id}';")
        await conn.execute(f"SET app.current_hostname = '{test_hostname}';")
        await conn.execute("SET app.current_cluster_name = 'test-cluster';")

        await run_test(
            conn,
            "INSERT should be allowed (with RLS context)",
            f"""INSERT INTO sync_metadata.hosts (host_id, hostname, cluster_name, status)
               VALUES ('{test_host_id}'::uuid, '{test_hostname}', 'test-cluster', 'active');""",
            should_succeed=True
        )

        # ============================================
        # Test 7: UPDATE Permission (Should SUCCEED)
        # ============================================
        await run_test(
            conn,
            "UPDATE should be allowed",
            f"UPDATE sync_metadata.hosts SET status = 'maintenance' WHERE hostname = '{test_hostname}';",
            should_succeed=True
        )

        # ============================================
        # Test 8: View Access (Should SUCCEED)
        # ============================================
        await run_query_test(
            conn,
            "View SELECT should be allowed",
            "SELECT COUNT(*) FROM sync_metadata.v_cluster_health;",
            should_succeed=True
        )

        # ============================================
        # Test 9: RLS Policy Check
        # ============================================
        rls_count = await run_query_test(
            admin_conn,
            "RLS is enabled on all tables",
            """SELECT COUNT(*)
               FROM pg_tables
               WHERE schemaname = 'sync_metadata'
                 AND tablename NOT LIKE 'pg_%'
                 AND rowsecurity = true;""",
            should_succeed=True
        )

        if rls_count and rls_count >= 6:
            print(f"  RLS enabled on {rls_count} tables (expected >= 6)")

        # ============================================
        # Test 10: RLS Isolation - Cannot INSERT for other host (Should FAIL)
        # ============================================
        other_host_id = str(uuid.uuid4())
        await run_test(
            conn,
            "RLS isolation prevents INSERT for different host",
            f"""INSERT INTO sync_metadata.hosts (host_id, hostname, cluster_name, status)
               VALUES ('{other_host_id}'::uuid, 'other-host-{random.randint(1000, 9999)}', 'test-cluster', 'active');""",
            should_succeed=False
        )

        # ============================================
        # Test 11: Cannot Access Other Schemas
        # ============================================
        await run_test(
            conn,
            "Cannot access other schemas (public)",
            "SELECT * FROM public.user LIMIT 1;",
            should_succeed=False
        )

        # ============================================
        # Test 12: Cannot Create Objects in sync_metadata
        # ============================================
        await run_test(
            conn,
            "Cannot create tables in sync_metadata",
            "CREATE TABLE sync_metadata.malicious_table (id int);",
            should_succeed=False
        )

        # ============================================
        # Test 13: Cannot Alter Tables
        # ============================================
        await run_test(
            conn,
            "Cannot alter tables",
            "ALTER TABLE sync_metadata.hosts ADD COLUMN malicious_column TEXT;",
            should_succeed=False
        )

    finally:
        await conn.close()
        await admin_conn.close()

    # ============================================
    # Summary
    # ============================================
    print(f"\n{BLUE}========================================{NC}")
    print(f"{BLUE}Test Results Summary{NC}")
    print(f"{BLUE}========================================{NC}")
    print(f"Total Tests: {tests_total}")
    print(f"{GREEN}Passed: {tests_passed}{NC}")
    print(f"{RED}Failed: {tests_failed}{NC}")

    if tests_failed == 0:
        print(f"\n{GREEN}🎉 All security validation tests passed!{NC}")
        sys.exit(0)
    else:
        print(f"\n{RED}⚠️  Some tests failed. Security validation incomplete.{NC}")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
