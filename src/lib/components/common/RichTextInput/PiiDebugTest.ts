/**
 * Test script to verify PII debug interface is working
 * This can be imported and run to force debug interface initialization
 */

import { ensurePiiDebugInterface } from './PiiDebugInterface';
import { PiiPerformanceTracker } from './PiiPerformanceOptimizer';

// Force immediate initialization
export function testPiiDebugInterface(): void {
	console.log('🧪 Testing PII Debug Interface...');

	// Ensure tracker is available
	const tracker = PiiPerformanceTracker.getInstance();
	console.log('✅ Performance tracker:', tracker.isEnabled() ? 'ENABLED' : 'DISABLED');

	// Force debug interface initialization
	ensurePiiDebugInterface();

	// Check if available on window
	const hasWindowDebug = typeof window !== 'undefined' && !!(window as any).piiDebug;
	console.log('✅ Window debug interface:', hasWindowDebug ? 'AVAILABLE' : 'NOT AVAILABLE');

	if (hasWindowDebug) {
		console.log('🎉 PII Debug interface is working! Try:');
		console.log('  • piiDebug.help()');
		console.log('  • piiDebug.metrics()');
		console.log('  • Chat command: /pii-perf metrics');
	} else {
		console.error('❌ PII Debug interface failed to initialize');
		console.log('🔧 Attempting manual initialization...');

		// Try direct initialization
		setTimeout(() => {
			ensurePiiDebugInterface();
			const retryCheck = typeof window !== 'undefined' && !!(window as any).piiDebug;
			console.log('🔄 Retry result:', retryCheck ? 'SUCCESS' : 'FAILED');
		}, 100);
	}
}

// Auto-run test if in development
if (typeof window !== 'undefined') {
	// Run test after a short delay
	setTimeout(testPiiDebugInterface, 200);
}
