<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { PiiSessionManager } from '$lib/utils/pii';
	import type { ExtendedPiiEntity, ConversationPiiState } from '$lib/utils/pii';
	import type { PiiModifier } from '$lib/components/common/RichTextInput/PiiModifierExtension';
	// Use unicode icons instead of lucide-svelte to avoid dependency issues

	export let conversationId: string | undefined = undefined;

	// Debug data state
	let entities: ExtendedPiiEntity[] = [];
	let modifiers: PiiModifier[] = [];
	let syncState: {
		lastUpdated: number | null;
		sessionId: string | null;
		apiKey: boolean;
		isLoading: boolean;
		hasPendingSave: boolean;
	} = {
		lastUpdated: null,
		sessionId: null,
		apiKey: false,
		isLoading: false,
		hasPendingSave: false
	};
	let sources: {
		temporary: { entities: number; modifiers: number; active: boolean };
		conversation: { entities: number; modifiers: number; exists: boolean };
		working: { entities: number };
		files: { mappings: number };
	} = {
		temporary: { entities: 0, modifiers: 0, active: false },
		conversation: { entities: 0, modifiers: 0, exists: false },
		working: { entities: 0 },
		files: { mappings: 0 }
	};
	let systemStats: {
		totalConversations: number;
		loadingConversations: number;
		pendingSaves: number;
		errorBackups: number;
		hasApiClient: boolean;
		temporaryStateActive: boolean;
	} = {
		totalConversations: 0,
		loadingConversations: 0,
		pendingSaves: 0,
		errorBackups: 0,
		hasApiClient: false,
		temporaryStateActive: false
	};

	// UI State
	let activeTab: 'entities' | 'modifiers' | 'sync' | 'sources' | 'system' = 'entities';
	let refreshInterval: ReturnType<typeof setInterval>;

	const refreshDebugData = () => {
		const manager = PiiSessionManager.getInstance();

		try {
			// Get current entities and modifiers
			entities = manager.getEntitiesForDisplay(conversationId) || [];
			modifiers = manager.getModifiersForDisplay(conversationId) || [];

			// Get debug data using proper debug methods
			const debugData = getManagerDebugData(manager);
			syncState = debugData.syncState;
			sources = debugData.sources;
			systemStats = manager.getDebugStats();
		} catch (e) {
			console.warn('PII Debug: Failed to refresh data:', e);
		}
	};

	// Helper function to extract debug data from PiiSessionManager using proper debug methods
	const getManagerDebugData = (manager: PiiSessionManager) => {
		try {
			return {
				syncState: manager.getDebugSyncState(conversationId),
				sources: manager.getDebugSources(conversationId)
			};
		} catch (e) {
			console.warn('PII Debug: Failed to extract manager data:', e);
			return {
				syncState: {
					lastUpdated: null,
					sessionId: null,
					apiKey: false,
					isLoading: false,
					hasPendingSave: false
				},
				sources: {
					temporary: { entities: 0, modifiers: 0, active: false },
					conversation: { entities: 0, modifiers: 0, exists: false },
					working: { entities: 0 },
					files: { mappings: 0 }
				}
			};
		}
	};

	const formatTimestamp = (timestamp: number | null): string => {
		if (!timestamp) return 'Never';
		const now = Date.now();
		const diff = now - timestamp;
		if (diff < 1000) return 'Just now';
		if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`;
		if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
		if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
		return new Date(timestamp).toLocaleString();
	};

	const getModifierActionIcon = (action: string) => {
		switch (action) {
			case 'ignore':
				return '🚫';
			case 'string-mask':
				return '🎭';
			case 'word-mask':
				return '📝';
			default:
				return '❓';
		}
	};

	const getSourceIcon = (source: string) => {
		switch (source) {
			case 'temporary':
				return '💬';
			case 'conversation':
				return '🗄️';
			case 'working':
				return '⏰';
			case 'files':
				return '📄';
			default:
				return '🤖';
		}
	};

	onMount(() => {
		refreshDebugData();
		refreshInterval = setInterval(refreshDebugData, 500);
	});

	onDestroy(() => {
		if (refreshInterval) {
			clearInterval(refreshInterval);
		}
	});

	// Reactive refresh when conversation changes
	$: if (conversationId !== undefined) {
		refreshDebugData();
	}
</script>

<!-- Enhanced PII Debug Overlay -->
<div
	class="fixed bottom-2 right-2 z-50 bg-gray-900/95 text-white rounded-lg shadow-xl border border-gray-700 w-[480px] max-h-[70vh] flex flex-col backdrop-blur-sm"
>
	<!-- Header with tabs -->
	<div class="flex items-center justify-between p-3 border-b border-gray-700">
		<div class="flex items-center gap-2">
			<span class="text-blue-400">🛡️</span>
			<span class="font-semibold text-sm">PII Debug</span>
			{#if conversationId}
				<span class="text-xs text-gray-400 font-mono">({conversationId.slice(0, 8)}...)</span>
			{/if}
			<!-- Status indicators -->
			<div class="flex items-center gap-1 ml-2">
				{#if syncState.apiKey}
					<div class="size-1.5 bg-green-500 rounded-full" title="API Connected"></div>
				{:else}
					<div class="size-1.5 bg-red-500 rounded-full" title="API Disconnected"></div>
				{/if}
				{#if syncState.isLoading || syncState.hasPendingSave}
					<div class="size-1.5 bg-yellow-500 rounded-full animate-pulse" title="Syncing"></div>
				{:else}
					<div class="size-1.5 bg-gray-500 rounded-full" title="Idle"></div>
				{/if}
			</div>
		</div>

		<!-- Tab navigation -->
		<div class="flex rounded-md bg-gray-800 p-0.5">
			<button
				class="px-2 py-1 text-xs rounded {activeTab === 'entities'
					? 'bg-blue-600 text-white'
					: 'text-gray-300 hover:text-white'}"
				on:click={() => (activeTab = 'entities')}
			>
				Entities ({entities.length})
			</button>
			<button
				class="px-2 py-1 text-xs rounded {activeTab === 'modifiers'
					? 'bg-blue-600 text-white'
					: 'text-gray-300 hover:text-white'}"
				on:click={() => (activeTab = 'modifiers')}
			>
				Modifiers ({modifiers.length})
			</button>
			<button
				class="px-2 py-1 text-xs rounded {activeTab === 'sync'
					? 'bg-blue-600 text-white'
					: 'text-gray-300 hover:text-white'}"
				on:click={() => (activeTab = 'sync')}
			>
				Sync
			</button>
			<button
				class="px-2 py-1 text-xs rounded {activeTab === 'sources'
					? 'bg-blue-600 text-white'
					: 'text-gray-300 hover:text-white'}"
				on:click={() => (activeTab = 'sources')}
			>
				Sources
			</button>
			<button
				class="px-2 py-1 text-xs rounded {activeTab === 'system'
					? 'bg-blue-600 text-white'
					: 'text-gray-300 hover:text-white'}"
				on:click={() => (activeTab = 'system')}
			>
				System
			</button>
		</div>
	</div>

	<!-- Content area -->
	<div class="flex-1 overflow-auto p-3">
		{#if activeTab === 'entities'}
			<!-- Entities Tab -->
			<div class="space-y-2">
				<div class="text-xs text-gray-400 mb-2">Known Entities ({entities.length})</div>
				{#if entities.length === 0}
					<div class="text-gray-500 text-xs italic">No entities detected</div>
				{:else}
					{#each entities as entity}
						<div class="bg-gray-800 rounded p-2 text-xs">
							<div class="flex items-center justify-between mb-1">
								<span class="font-mono text-blue-300">{entity.label}</span>
								<span
									class="px-1.5 py-0.5 rounded text-[10px] {entity.shouldMask
										? 'bg-green-600/70'
										: 'bg-red-600/70'}"
								>
									{entity.shouldMask ? 'masked' : 'unmasked'}
								</span>
							</div>
							<div class="text-gray-300">"{entity.text}"</div>
							<div class="flex items-center justify-between mt-1 text-[10px] text-gray-400">
								<span>{entity.type}</span>
								<span>{entity.occurrences?.length || 0} occurrence(s)</span>
							</div>
						</div>
					{/each}
				{/if}
			</div>
		{:else if activeTab === 'modifiers'}
			<!-- Modifiers Tab -->
			<div class="space-y-2">
				<div class="text-xs text-gray-400 mb-2">Active Modifiers ({modifiers.length})</div>
				{#if modifiers.length === 0}
					<div class="text-gray-500 text-xs italic">No modifiers defined</div>
				{:else}
					{#each modifiers as modifier}
						<div class="bg-gray-800 rounded p-2 text-xs">
							<div class="flex items-center justify-between mb-1">
								<span class="flex items-center gap-1">
									<span>{getModifierActionIcon(modifier.action)}</span>
									<span class="font-mono text-purple-300">{modifier.entity}</span>
								</span>
								<span class="px-1.5 py-0.5 rounded text-[10px] bg-purple-600/70">
									{modifier.action}
								</span>
							</div>
							{#if modifier.type}
								<div class="text-gray-400">Type: {modifier.type}</div>
							{/if}
							{#if modifier.from !== undefined && modifier.to !== undefined}
								<div class="text-gray-400">Position: {modifier.from}-{modifier.to}</div>
							{/if}
							<div class="text-[10px] text-gray-500 mt-1">ID: {modifier.id}</div>
						</div>
					{/each}
				{/if}
			</div>
		{:else if activeTab === 'sync'}
			<!-- Sync State Tab -->
			<div class="space-y-3">
				<div class="text-xs text-gray-400 mb-2">Synchronization State</div>

				<!-- API Connection -->
				<div class="bg-gray-800 rounded p-2">
					<div class="flex items-center justify-between mb-1">
						<span class="text-xs font-medium">API Connection</span>
						<span class="size-2 rounded-full {syncState.apiKey ? 'bg-green-500' : 'bg-red-500'}"
						></span>
					</div>
					<div class="text-[10px] text-gray-400">
						Status: {syncState.apiKey ? 'Connected' : 'Disconnected'}
					</div>
					{#if syncState.sessionId}
						<div class="text-[10px] text-gray-400 font-mono">
							Session: {syncState.sessionId.slice(0, 16)}...
						</div>
					{/if}
				</div>

				<!-- Sync Status -->
				<div class="bg-gray-800 rounded p-2">
					<div class="flex items-center justify-between mb-1">
						<span class="text-xs font-medium">Data Sync</span>
						<div class="flex items-center gap-1">
							{#if syncState.isLoading}
								<div class="size-2 bg-yellow-500 rounded-full animate-pulse"></div>
								<span class="text-[10px] text-yellow-400">Loading</span>
							{:else if syncState.hasPendingSave}
								<div class="size-2 bg-blue-500 rounded-full animate-pulse"></div>
								<span class="text-[10px] text-blue-400">Saving</span>
							{:else}
								<div class="size-2 bg-green-500 rounded-full"></div>
								<span class="text-[10px] text-green-400">Synced</span>
							{/if}
						</div>
					</div>
					<div class="text-[10px] text-gray-400">
						Last Updated: {formatTimestamp(syncState.lastUpdated)}
					</div>
				</div>
			</div>
		{:else if activeTab === 'sources'}
			<!-- Sources Tab -->
			<div class="space-y-2">
				<div class="text-xs text-gray-400 mb-2">Data Sources</div>

				<!-- Temporary State -->
				<div class="bg-gray-800 rounded p-2">
					<div class="flex items-center justify-between mb-1">
						<div class="flex items-center gap-1">
							<span>💬</span>
							<span class="text-xs font-medium">Temporary</span>
						</div>
						<span
							class="size-2 rounded-full {sources.temporary.active
								? 'bg-green-500'
								: 'bg-gray-500'}"
						></span>
					</div>
					<div class="text-[10px] text-gray-400">
						Entities: {sources.temporary.entities} | Modifiers: {sources.temporary.modifiers}
					</div>
					<div class="text-[10px] text-gray-500">
						{sources.temporary.active ? 'Active (new chat)' : 'Inactive'}
					</div>
				</div>

				<!-- Conversation State -->
				<div class="bg-gray-800 rounded p-2">
					<div class="flex items-center justify-between mb-1">
						<div class="flex items-center gap-1">
							<span>🗄️</span>
							<span class="text-xs font-medium">Conversation</span>
						</div>
						<span
							class="size-2 rounded-full {sources.conversation.exists
								? 'bg-green-500'
								: 'bg-gray-500'}"
						></span>
					</div>
					<div class="text-[10px] text-gray-400">
						Entities: {sources.conversation.entities} | Modifiers: {sources.conversation.modifiers}
					</div>
					<div class="text-[10px] text-gray-500">
						{sources.conversation.exists ? 'Persisted state' : 'No saved state'}
					</div>
				</div>

				<!-- Working Entities -->
				<div class="bg-gray-800 rounded p-2">
					<div class="flex items-center gap-1 mb-1">
						<span>⏰</span>
						<span class="text-xs font-medium">Working Entities</span>
					</div>
					<div class="text-[10px] text-gray-400">
						Uncommitted: {sources.working.entities}
					</div>
					<div class="text-[10px] text-gray-500">Entities before message send</div>
				</div>

				<!-- File Mappings -->
				<div class="bg-gray-800 rounded p-2">
					<div class="flex items-center gap-1 mb-1">
						<span>📄</span>
						<span class="text-xs font-medium">File Sources</span>
					</div>
					<div class="text-[10px] text-gray-400">
						File mappings: {sources.files.mappings}
					</div>
					<div class="text-[10px] text-gray-500">PII detected from uploads</div>
				</div>
			</div>
		{:else if activeTab === 'system'}
			<!-- System Tab -->
			<div class="space-y-2">
				<div class="text-xs text-gray-400 mb-2">System Overview</div>

				<!-- Overall Stats -->
				<div class="bg-gray-800 rounded p-2">
					<div class="flex items-center gap-1 mb-1">
						<span>🗄️</span>
						<span class="text-xs font-medium">Session Manager</span>
					</div>
					<div class="grid grid-cols-2 gap-2 text-[10px] text-gray-400">
						<div>
							<span class="text-gray-300">Conversations:</span>
							{systemStats.totalConversations}
						</div>
						<div>
							<span class="text-gray-300">Loading:</span>
							{systemStats.loadingConversations}
						</div>
						<div>
							<span class="text-gray-300">Pending saves:</span>
							{systemStats.pendingSaves}
						</div>
						<div>
							<span class="text-gray-300">Error backups:</span>
							{systemStats.errorBackups}
						</div>
					</div>
				</div>

				<!-- API Client Status -->
				<div class="bg-gray-800 rounded p-2">
					<div class="flex items-center justify-between mb-1">
						<span class="text-xs font-medium">API Client</span>
						<span
							class="size-2 rounded-full {systemStats.hasApiClient ? 'bg-green-500' : 'bg-red-500'}"
						></span>
					</div>
					<div class="text-[10px] text-gray-400">
						Status: {systemStats.hasApiClient ? 'Initialized' : 'Not initialized'}
					</div>
				</div>

				<!-- Temporary State -->
				<div class="bg-gray-800 rounded p-2">
					<div class="flex items-center justify-between mb-1">
						<span class="text-xs font-medium">Temporary State</span>
						<span
							class="size-2 rounded-full {systemStats.temporaryStateActive
								? 'bg-green-500'
								: 'bg-gray-500'}"
						></span>
					</div>
					<div class="text-[10px] text-gray-400">
						Mode: {systemStats.temporaryStateActive ? 'Active (new chat)' : 'Inactive'}
					</div>
				</div>

				<!-- Summary Stats -->
				<div class="bg-gray-800 rounded p-2">
					<div class="text-xs font-medium mb-1">Current Session</div>
					<div class="grid grid-cols-2 gap-2 text-[10px] text-gray-400">
						<div>
							<span class="text-blue-300">Total Entities:</span>
							{entities.length}
						</div>
						<div>
							<span class="text-purple-300">Total Modifiers:</span>
							{modifiers.length}
						</div>
						<div>
							<span class="text-green-300">Masked:</span>
							{entities.filter((e) => e.shouldMask).length}
						</div>
						<div>
							<span class="text-red-300">Unmasked:</span>
							{entities.filter((e) => !e.shouldMask).length}
						</div>
					</div>
				</div>
			</div>
		{/if}
	</div>

	<!-- Footer with refresh indicator -->
	<div class="border-t border-gray-700 p-2 flex items-center justify-between">
		<div class="text-[10px] text-gray-500">Auto-refresh: 500ms</div>
		<div class="size-1 bg-blue-500 rounded-full animate-pulse"></div>
	</div>
</div>
