# Mermaid Scalability Test Suite

Comprehensive test suite for the Mermaid scalability optimization implementation.

## Test Structure

### Unit Tests
- `src/lib/services/__tests__/mermaid.service.test.ts` - MermaidService tests
- `src/lib/stores/__tests__/mermaid.store.test.ts` - MermaidStore tests
- `src/lib/utils/__tests__/mermaid-errors.test.ts` - Error handling tests
- `src/lib/components/chat/Messages/__tests__/CodeBlock.mermaid.test.ts` - Component integration tests

### Integration Tests
- `test/mermaid/integration.test.ts` - Complete pipeline integration tests

### E2E Tests
- `test/mermaid/e2e.test.ts` - End-to-end user flow tests

## Running Tests

### Using Conda and Docker (Recommended)
```bash
./scripts/run-tests.sh
```

### Local Testing
```bash
# Unit tests only
npm run test:unit

# Integration tests
npm run test:integration

# E2E tests
npm run test:e2e

# All tests
npm run test:all

# With coverage
npm run test:coverage
```

### Using Docker Only
```bash
docker-compose -f docker-compose.test.yaml up
```

## Test Coverage

The test suite covers:
- ✅ Service initialization and singleton pattern
- ✅ Theme detection and switching
- ✅ Parse and render functionality
- ✅ Memory cache (LRU eviction)
- ✅ IndexedDB persistence
- ✅ BroadcastChannel cross-tab sync
- ✅ Error handling and retry logic
- ✅ Performance metrics tracking
- ✅ Lazy loading with IntersectionObserver
- ✅ Debouncing for streaming content
- ✅ Complete render pipeline
- ✅ Cache hit/miss scenarios
- ✅ Theme-aware caching
- ✅ Error recovery

## Mock Data

Tests use mock Mermaid diagrams:
- Simple diagrams: `graph TD\nA-->B`
- Complex diagrams: Multi-node flowcharts
- Sequence diagrams
- Invalid syntax for error testing

## Environment Requirements

- Node.js >= 18.13.0
- npm >= 6.0.0
- Docker (optional, for containerized testing)
- Conda (for rit4test environment)

## Continuous Integration

Tests are designed to run in CI/CD pipelines with:
- Headless browser support
- Docker containerization
- Coverage reporting
- Parallel test execution

