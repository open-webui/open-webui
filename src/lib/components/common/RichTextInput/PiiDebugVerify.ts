/**
 * Simple verification script to check if PII debug features are working
 * Run this in browser console: import('/src/lib/components/common/RichTextInput/PiiDebugVerify.ts').then(m => m.verifyPiiDebug())
 */

export function verifyPiiDebug(): void {
	console.group('🔍 PII Debug Verification');

	// Check window object
	const hasWindowDebug = typeof window !== 'undefined' && !!(window as any).piiDebug;
	console.log('1. Window piiDebug object:', hasWindowDebug ? '✅ Available' : '❌ Missing');

	if (hasWindowDebug) {
		const debugObj = (window as any).piiDebug;
		const methods = [
			'metrics',
			'reset',
			'setTracking',
			'benchmark',
			'config',
			'session',
			'sync',
			'sources',
			'help'
		];
		const availableMethods = methods.filter((method) => typeof debugObj[method] === 'function');
		console.log(
			'2. Available methods:',
			availableMethods.length === methods.length
				? '✅ All present'
				: `⚠️ Missing: ${methods.filter((m) => !availableMethods.includes(m)).join(', ')}`
		);

		// Test a simple method
		try {
			debugObj.config();
			console.log('3. Method execution test:', '✅ Working');
		} catch (e) {
			console.log('3. Method execution test:', '❌ Error:', e);
		}
	}

	// Check performance tracker
	try {
		const { PiiPerformanceTracker } = await import('./PiiPerformanceOptimizer');
		const tracker = PiiPerformanceTracker.getInstance();
		console.log('4. Performance tracker:', tracker ? '✅ Available' : '❌ Missing');
		console.log('5. Tracking enabled:', tracker.isEnabled() ? '✅ Yes' : '⚠️ No');
	} catch (e) {
		console.log('4. Performance tracker:', '❌ Import error:', e);
	}

	// Check session manager
	try {
		const { PiiSessionManager } = await import('../../../utils/pii');
		const sessionManager = PiiSessionManager.getInstance();
		console.log('6. Session manager:', sessionManager ? '✅ Available' : '❌ Missing');

		// Check debug methods
		const hasDebugMethods = typeof sessionManager.getDebugStats === 'function';
		console.log('7. Session debug methods:', hasDebugMethods ? '✅ Available' : '❌ Missing');
	} catch (e) {
		console.log('6. Session manager:', '❌ Import error:', e);
	}

	console.groupEnd();

	if (hasWindowDebug) {
		console.log('🎉 PII Debug is working! Try: piiDebug.help()');
	} else {
		console.log('🔧 To fix: Reload the page or run initialization manually');
	}
}

// Quick test function for console
(window as any).verifyPiiDebug = verifyPiiDebug;
