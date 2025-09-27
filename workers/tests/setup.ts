// Test setup for Vitest
import { vi, afterEach } from 'vitest';

// Mock global console methods in tests to reduce noise
console.log = vi.fn(console.log);
console.warn = vi.fn(console.warn);
console.error = vi.fn(console.error);

// Setup global test timeout
vi.setConfig({ testTimeout: 10000 });

// Clean up after each test
afterEach(() => {
  vi.clearAllMocks();
});
