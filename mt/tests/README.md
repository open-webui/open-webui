# Multi-Tenant System Testing Suite

This directory contains all test suites for the Multi-Tenant (mt/) system, including tests for sync infrastructure, client management, and deployment validation.

## 📋 Testing Methodology

### Purpose

The testing suite validates that all mt/ features are production-ready before release. Tests cover:
- **Functional Requirements**: Feature behavior matches specifications
- **Security Requirements**: Access controls and permissions work correctly
- **Performance Requirements**: System meets latency and throughput targets
- **Reliability Requirements**: High availability and failover work as designed
- **Integration Requirements**: Components interact correctly

### Test Categories

1. **Unit Tests**: Individual component functionality
2. **Integration Tests**: Multi-component interactions
3. **Security Tests**: Permission validation and access control
4. **Performance Tests**: Load, stress, and latency testing
5. **HA/Failover Tests**: High availability and disaster recovery
6. **End-to-End Tests**: Full user workflow validation

## 🗂️ Test Structure

```
mt/tests/
├── README.md                          # This file
├── run-certification.sh               # Batch test runner (future)
├── sync-security-validation.py        # SYNC: Security validation
├── sync-ha-failover.sh               # SYNC: HA failover tests (future)
├── sync-conflict-resolution.sh       # SYNC: Conflict tests (future)
├── sync-state-authority.sh           # SYNC: State management tests (future)
└── client-manager-integration.sh     # Client manager tests (future)
```

## 🧪 Available Tests

### SYNC System Tests

#### 1. Security Validation (`sync-security-validation.py`)

**Status**: ✅ Completed (2025-10-12)
**Language**: Python 3.11+
**Dependencies**: asyncpg
**Archon Task**: 39304002-a278-4eb8-a12e-f77c63bed141

**Purpose**: Validates sync_service role permissions and RLS policies

**Test Coverage**:
- ✅ DELETE operations correctly denied
- ✅ DROP TABLE/SCHEMA operations correctly denied
- ✅ TRUNCATE operations correctly denied
- ✅ SELECT operations correctly allowed
- ✅ INSERT operations correctly allowed (with RLS context)
- ✅ UPDATE operations correctly allowed
- ✅ View access correctly allowed
- ✅ RLS enabled on all sync_metadata tables
- ✅ RLS isolation prevents cross-host data access
- ✅ Schema isolation prevents unauthorized access
- ✅ CREATE/ALTER operations correctly denied

**Usage**:
```bash
# From host with running Docker containers:
cd mt/tests
source ../SYNC/.credentials
docker exec -i \
  -e SYNC_URL="$SYNC_URL" \
  -e ADMIN_URL="$ADMIN_URL" \
  openwebui-sync-node-a python3 - < sync-security-validation.py
```

**Expected Result**: All 13 tests pass

**Last Run**: 2025-10-12 (157.245.220.28) - ✅ All tests passed

---

#### 2. HA Failover Tests (`sync-ha-failover.sh`)

**Status**: ⏳ Manual testing completed, script pending
**Language**: Bash
**Dependencies**: curl, jq, docker
**Archon Task**: 1dd7b8f1-bb15-4d32-aa5c-234b93405e6c

**Purpose**: Validates leader election and automatic failover

**Test Coverage**:
- ✅ Initial state verification (single leader elected)
- ✅ Leader failure → follower takeover (~35 seconds)
- ✅ Restarted node becomes follower (not leader)
- ✅ Simultaneous restart (only one leader)
- ✅ Database view accuracy (real-time status)
- ✅ Lease expiration and renewal

**Manual Testing Completed**: 2025-10-12 (157.245.220.28)

**Future Script Usage**:
```bash
cd mt/tests
./sync-ha-failover.sh
```

---

#### 3. Conflict Resolution Tests (`sync-conflict-resolution.sh`)

**Status**: 🔲 Pending
**Language**: Bash + Python
**Archon Task**: f5133b33-a8e9-4e62-b81e-e5f5a5e5c5c5

**Purpose**: Validates all 5 conflict resolution strategies

**Test Coverage** (planned):
- [ ] newest_wins strategy
- [ ] source_wins strategy
- [ ] target_wins strategy
- [ ] merge strategy
- [ ] manual strategy

---

#### 4. State Authority Tests (`sync-state-authority.sh`)

**Status**: 🔲 Pending
**Language**: Bash + Python
**Archon Task**: 8dc3f74f-a8e9-4e62-b81e-e5f5a5e5c5c5

**Purpose**: Validates Supabase as authoritative source of truth

**Test Coverage** (planned):
- [ ] Cache invalidation across cluster
- [ ] Supabase updates propagate to cache
- [ ] Cache-aside pattern works correctly
- [ ] TTL expiration and refresh

---

## 🎯 Certification Testing

### Pre-Release Certification

Before deploying to production, run the full certification suite:

```bash
cd mt/tests
./run-certification.sh
```

**Future Implementation**: This script will:
1. Detect available test components (SYNC, client-manager, etc.)
2. Run all applicable tests in sequence
3. Generate comprehensive test report
4. Set exit code (0 = all pass, 1 = any failures)
5. Save results to `mt/tests/reports/YYYY-MM-DD-HH-MM-SS.txt`

### Certification Criteria

A system passes certification if:
- ✅ All security tests pass (no exceptions)
- ✅ All HA/failover tests pass (no exceptions)
- ✅ All functional tests pass (≥95%)
- ✅ Performance targets met (≥90%)
- ⚠️ Integration tests pass (≥90%, document exceptions)

### Certification Levels

1. **Alpha**: Core functionality works, known issues exist
2. **Beta**: Security + HA pass, functional tests ≥90%
3. **Release Candidate**: All tests ≥95%, performance validated
4. **Production**: Full certification passed, deployed and monitored

**Current Status**:
- SYNC System: **Beta** (Security ✅, HA ✅, Integration pending)

---

## 📝 Writing New Tests

### Test Naming Convention

```
<component>-<category>-<description>.{py|sh}
```

Examples:
- `sync-security-validation.py` - SYNC security tests
- `sync-ha-failover.sh` - SYNC high availability tests
- `client-manager-deployment.sh` - Client manager deployment tests

### Test Template (Python)

```python
#!/usr/bin/env python3
"""
<Component> <Category> Test Suite
Purpose: <One line description>

Test Coverage:
- Test 1 description
- Test 2 description

Usage:
    python3 <test-name>.py

Expected Result: All tests pass
"""

import sys

# Test counter
tests_passed = 0
tests_failed = 0
tests_total = 0

def run_test(test_name, test_func):
    """Run a single test"""
    global tests_passed, tests_failed, tests_total

    tests_total += 1
    print(f"\nTest #{tests_total}: {test_name}")

    try:
        test_func()
        print("✅ PASS")
        tests_passed += 1
    except Exception as e:
        print(f"❌ FAIL - {e}")
        tests_failed += 1

def main():
    print("=" * 50)
    print("<Test Suite Name>")
    print("=" * 50)

    # Run tests
    run_test("Test 1 description", test_1)
    run_test("Test 2 description", test_2)

    # Summary
    print("\n" + "=" * 50)
    print("Test Results Summary")
    print("=" * 50)
    print(f"Total Tests: {tests_total}")
    print(f"Passed: {tests_passed}")
    print(f"Failed: {tests_failed}")

    sys.exit(0 if tests_failed == 0 else 1)

if __name__ == '__main__':
    main()
```

### Test Template (Bash)

```bash
#!/bin/bash
# <Component> <Category> Test Suite
# Purpose: <One line description>
#
# Test Coverage:
# - Test 1 description
# - Test 2 description
#
# Usage: ./<test-name>.sh

set -e

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

run_test() {
    local test_name="$1"
    local test_command="$2"

    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    echo -e "\n${BLUE}Test #${TESTS_TOTAL}: ${test_name}${NC}"

    if eval "$test_command"; then
        echo -e "${GREEN}✅ PASS${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

echo "=================================================="
echo "<Test Suite Name>"
echo "=================================================="

# Run tests
run_test "Test 1 description" "test_1_function"
run_test "Test 2 description" "test_2_function"

# Summary
echo ""
echo "=================================================="
echo "Test Results Summary"
echo "=================================================="
echo "Total Tests: $TESTS_TOTAL"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}🎉 All tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}⚠️  Some tests failed.${NC}"
    exit 1
fi
```

### Test Requirements

All tests must:
1. **Be self-contained**: No manual setup required (beyond env vars)
2. **Be idempotent**: Can run multiple times without side effects
3. **Clean up**: Remove test data after completion
4. **Report clearly**: Use colored output and clear pass/fail indicators
5. **Exit correctly**: Exit 0 on success, 1 on any failure
6. **Document usage**: Include usage instructions in header comments
7. **Handle errors**: Graceful error handling with informative messages

---

## 🔍 Test Execution Environments

### Local Development
- Run tests against local containers
- Use `localhost` for connections
- Credentials in `mt/SYNC/.credentials`

### Staging Server
- Run tests against staging deployment
- Use staging server IP/hostname
- Credentials in server's `mt/SYNC/.credentials`

### Production Server
- **Caution**: Only run read-only/non-destructive tests
- Some tests (HA failover) require maintenance window
- Always backup before running

---

## 📊 Test Reports

### Manual Test Report Format

```
Test Report: <Test Suite Name>
Date: YYYY-MM-DD HH:MM:SS UTC
Server: <hostname/IP>
Environment: <dev/staging/production>

Test Results:
- Total Tests: X
- Passed: Y
- Failed: Z

Detailed Results:
1. [PASS/FAIL] Test 1 name
   Notes: <any relevant notes>

2. [PASS/FAIL] Test 2 name
   Notes: <any relevant notes>

Summary:
<overall assessment>

Issues Found:
- Issue 1 description
- Issue 2 description

Recommendations:
- Recommendation 1
- Recommendation 2
```

---

## 🚀 Future Enhancements

### Planned Features

1. **Automated Test Runner** (`run-certification.sh`)
   - Sequential test execution
   - Dependency checking
   - Report generation
   - Email notifications

2. **Continuous Testing**
   - GitHub Actions integration
   - Scheduled test runs
   - Automated regression testing

3. **Performance Benchmarking**
   - Baseline performance metrics
   - Regression detection
   - Load testing automation

4. **Test Coverage Tracking**
   - Code coverage reports
   - Feature coverage matrix
   - Gap analysis

---

## 📚 Related Documentation

- **SYNC System**: `mt/SYNC/README.md`
- **Implementation Status**: `mt/SYNC/IMPLEMENTATION_STATUS.md`
- **Technical Reference**: `mt/SYNC/TECHNICAL_REFERENCE.md`
- **Multi-Tenant Overview**: `mt/README.md`

---

## 🤝 Contributing

When adding new tests:

1. Follow naming conventions
2. Use test templates as starting point
3. Document test coverage in this README
4. Update `run-certification.sh` to include new test
5. Test on development environment first
6. Get peer review before merging

---

## 📞 Support

For questions about testing:
- Review test documentation in this README
- Check test script comments for usage instructions
- Review related documentation in mt/SYNC/
- Create GitHub issue for test failures or bugs

---

**Last Updated**: 2025-10-12
**Maintained By**: Development Team
**Status**: Active Development
