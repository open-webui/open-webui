/**
 * Debug interface for PII performance monitoring and troubleshooting
 * Provides console commands and utilities for developers
 */

import { PiiPerformanceTracker } from './PiiPerformanceOptimizer';
import { getPiiConfig } from './PiiExtensionConfig';
import { PiiSessionManager } from '$lib/utils/pii';

// Debug commands interface
export interface PiiDebugCommands {
	/** Show current performance metrics */
	metrics(): void;
	/** Reset performance metrics */
	reset(): void;
	/** Enable/disable performance tracking */
	setTracking(enabled: boolean): void;
	/** Run performance benchmark */
	benchmark(): Promise<void>;
	/** Get current configuration */
	config(): void;
	/** Show session manager debug info */
	session(conversationId?: string): void;
	/** Show sync state info */
	sync(conversationId?: string): void;
	/** Show data sources breakdown */
	sources(conversationId?: string): void;
	/** Show help */
	help(): void;
}

/**
 * Initialize debug interface on window object
 * Available as window.piiDebug in browser console
 */
export function initializePiiDebugInterface(): void {
	if (typeof window === 'undefined') return;

	const tracker = PiiPerformanceTracker.getInstance();
	const config = getPiiConfig();

	// Set initial tracking state from config
	tracker.setEnabled(config.performance.enabled);

	const debugCommands: PiiDebugCommands = {
		metrics() {
			console.group('🚀 PII Performance Metrics');
			const metrics = tracker.getMetrics();

			console.table({
				'State Updates': metrics.stateUpdates,
				'Position Remaps': metrics.positionRemaps,
				'Decoration Updates': metrics.decorationUpdates,
				'API Calls': metrics.apiCalls,
				'Sync Operations': metrics.syncOperations,
				'Updates/sec': metrics.stateUpdatesPerSecond.toFixed(2),
				'Cache Hit Rate': `${(metrics.cacheHitRate * 100).toFixed(1)}%`,
				'Avg Persist Time': `${metrics.avgPersistTime.toFixed(2)}ms`,
				Runtime: `${(metrics.elapsedMs / 1000).toFixed(1)}s`
			});

			console.log('🔧 Performance Status:', tracker.isEnabled() ? '✅ Enabled' : '❌ Disabled');
			console.log('📊 Config Thresholds:', config.performance.thresholds);
			console.groupEnd();
		},

		session(conversationId?: string) {
			const sessionManager = PiiSessionManager.getInstance();
			console.group('📊 PII Session Manager Stats');
			console.log('General Stats:', sessionManager.getDebugStats());
			if (conversationId) {
				console.log(
					`Conversation ${conversationId}:`,
					sessionManager.getDebugSources(conversationId)
				);
			}
			console.groupEnd();
		},

		sync(conversationId?: string) {
			const sessionManager = PiiSessionManager.getInstance();
			console.group('🔄 PII Sync State');
			console.log('Sync Info:', sessionManager.getDebugSyncState(conversationId));
			console.groupEnd();
		},

		sources(conversationId?: string) {
			const sessionManager = PiiSessionManager.getInstance();
			console.group('📂 PII Data Sources');
			const sources = sessionManager.getDebugSources(conversationId);
			console.table(sources);
			console.groupEnd();
		},

		reset() {
			tracker.reset();
			console.log('🔄 Performance metrics reset');
		},

		setTracking(enabled: boolean) {
			tracker.setEnabled(enabled);
			console.log(`📊 Performance tracking ${enabled ? 'enabled' : 'disabled'}`);
		},

		async benchmark() {
			console.log('🏃‍♂️ Running PII performance benchmark...');

			const start = performance.now();
			tracker.reset();

			// Simulate typical operations
			for (let i = 0; i < 100; i++) {
				tracker.recordStateUpdate();
				tracker.recordPositionRemap();
				if (i % 10 === 0) tracker.recordDecorationUpdate();
				if (i % 20 === 0) tracker.recordApiCall();
				await new Promise((resolve) => setTimeout(resolve, 1));
			}

			const elapsed = performance.now() - start;
			const metrics = tracker.getMetrics();

			console.log(`⏱️ Benchmark completed in ${elapsed.toFixed(0)}ms`);
			console.log(`📈 Operations/sec: ${(100 / (elapsed / 1000)).toFixed(0)}`);
			this.metrics();
		},

		config() {
			console.group('⚙️ PII Configuration');
			console.log('Performance Settings:', config.performance);
			console.log('Timing Settings:', config.timing);
			console.log('Text Processing:', config.textProcessing);
			console.groupEnd();
		},

		help() {
			console.group('🛠️ PII Debug Commands');
			console.log('Available commands:');
			console.log('• piiDebug.metrics()         - Show performance metrics');
			console.log('• piiDebug.reset()           - Reset metrics');
			console.log('• piiDebug.setTracking(bool) - Enable/disable tracking');
			console.log('• piiDebug.benchmark()       - Run performance test');
			console.log('• piiDebug.config()          - Show configuration');
			console.log('• piiDebug.session(id?)      - Show session manager stats');
			console.log('• piiDebug.sync(id?)         - Show sync state');
			console.log('• piiDebug.sources(id?)      - Show data sources');
			console.log('• piiDebug.help()            - Show this help');
			console.log('');
			console.log('Chat slash commands (admin only):');
			console.log('• /pii-perf metrics     - Show metrics in chat');
			console.log('• /pii-perf reset       - Reset metrics');
			console.log('• /pii-perf on/off      - Enable/disable tracking');
			console.log('• /pii-debug on/off     - Toggle debug overlay');
			console.groupEnd();
		}
	};

	// Make available globally
	(window as any).piiDebug = debugCommands;

	// Also make available on globalThis for broader compatibility
	if (typeof globalThis !== 'undefined') {
		(globalThis as any).piiDebug = debugCommands;
	}

	console.log('🔧 PII Debug interface loaded. Type piiDebug.help() for commands.');
	console.log('📊 Performance tracking:', tracker.isEnabled() ? 'ENABLED' : 'DISABLED');
}

/**
 * Slash command handler for chat interface
 * Usage: /pii-perf [metrics|reset|on|off]
 */
export function handlePiiPerformanceSlashCommand(args: string[]): boolean {
	const command = args[0]?.toLowerCase();
	const tracker = PiiPerformanceTracker.getInstance();

	switch (command) {
		case 'metrics':
		case 'm':
			tracker.logMetrics();
			console.log('✅ PII performance metrics displayed in console');
			return true;

		case 'reset':
		case 'r':
			tracker.reset();
			console.log('🔄 PII performance metrics reset');
			return true;

		case 'on':
		case 'enable':
			tracker.setEnabled(true);
			console.log('✅ PII performance tracking ENABLED');
			return true;

		case 'off':
		case 'disable':
			tracker.setEnabled(false);
			console.log('❌ PII performance tracking DISABLED');
			return true;

		case 'debug':
		case 'd':
			// Show available debug commands
			if (typeof window !== 'undefined' && (window as any).piiDebug) {
				(window as any).piiDebug.help();
			} else {
				console.log('⚠️ PII debug interface not available. Trying to initialize...');
				ensurePiiDebugInterface();
			}
			return true;

		default:
			console.group('📊 PII Performance Commands');
			console.log('Available commands:');
			console.log('• /pii-perf metrics  - Show performance metrics');
			console.log('• /pii-perf reset    - Reset all metrics');
			console.log('• /pii-perf on       - Enable tracking');
			console.log('• /pii-perf off      - Disable tracking');
			console.log('• /pii-perf debug    - Show debug interface help');
			console.log('');
			console.log('💻 Browser console: Type piiDebug.help() for more commands');
			console.groupEnd();
			return true;
	}
}

// Check if already initialized to prevent double initialization
let debugInterfaceInitialized = false;

// Enhanced initialization function
export function ensurePiiDebugInterface(): void {
	if (debugInterfaceInitialized) return;
	if (typeof window === 'undefined') return;

	debugInterfaceInitialized = true;
	initializePiiDebugInterface();
}

// Auto-initialize when module loads (with safeguards)
if (typeof window !== 'undefined') {
	// Check if already exists
	if (!(window as any).piiDebug) {
		// Delay initialization to ensure other modules are loaded
		setTimeout(() => {
			if (!(window as any).piiDebug) {
				ensurePiiDebugInterface();
			}
		}, 100);
	}
}
