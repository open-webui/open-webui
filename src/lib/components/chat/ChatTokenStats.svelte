<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import { chatId, chatTokenStats, chatTokenStatsRefreshTrigger } from '$lib/stores';
	import { getChatTokenStats, formatTokenCount } from '$lib/apis/analytics';
	import Tooltip from '../common/Tooltip.svelte';

	const i18n = getContext('i18n');

	// Track the last trigger value to detect changes
	let lastTrigger = 0;

	// Reactive fetch when chatId changes
	$: if ($chatId && $chatId !== '' && !$chatId.startsWith('local:')) {
		fetchTokenStats($chatId);
	} else {
		chatTokenStats.set(null);
	}

	// Reactive fetch when refresh trigger changes (debounced)
	$: if ($chatTokenStatsRefreshTrigger > lastTrigger && $chatId && !$chatId.startsWith('local:')) {
		lastTrigger = $chatTokenStatsRefreshTrigger;
		// Debounce the refresh slightly to allow backend to process
		setTimeout(() => {
			fetchTokenStats($chatId);
		}, 500);
	}

	async function fetchTokenStats(id: string) {
		if (!id || id.startsWith('local:')) {
			chatTokenStats.set(null);
			return;
		}

		// Set loading state
		chatTokenStats.update((current) => ({
			chat_id: id,
			total_input_tokens: current?.total_input_tokens ?? 0,
			total_output_tokens: current?.total_output_tokens ?? 0,
			total_tokens: current?.total_tokens ?? 0,
			last_input_tokens: current?.last_input_tokens ?? 0,
			last_output_tokens: current?.last_output_tokens ?? 0,
			message_count: current?.message_count ?? 0,
			loading: true
		}));

		try {
				const token = localStorage.getItem('token');
				if (!token) {
					console.log('[ChatTokenStats] No token found, setting null');
					chatTokenStats.set(null);
					return;
				}
	
				console.log('[ChatTokenStats] Fetching stats for chat:', id);
				const stats = await getChatTokenStats(token, id);
				console.log('[ChatTokenStats] API Response:', stats);
				
				if (stats) {
					chatTokenStats.set({
						chat_id: stats.chat_id,
						total_input_tokens: stats.total_input_tokens,
						total_output_tokens: stats.total_output_tokens,
						total_tokens: stats.total_tokens,
						last_input_tokens: stats.last_input_tokens,
						last_output_tokens: stats.last_output_tokens,
						message_count: stats.message_count,
						loading: false
					});
					console.log('[ChatTokenStats] Stats set, total_tokens:', stats.total_tokens);
				} else {
					console.log('[ChatTokenStats] No stats returned, setting null');
					chatTokenStats.set(null);
				}
			} catch (error) {
				console.error('[ChatTokenStats] Error fetching token stats:', error);
				chatTokenStats.set(null);
			}
	}

	// Function to refresh stats (can be called from parent)
	export function refresh() {
		if ($chatId && $chatId !== '' && !$chatId.startsWith('local:')) {
			fetchTokenStats($chatId);
		}
	}

	onDestroy(() => {
		chatTokenStats.set(null);
	});
</script>

{#if $chatTokenStats && !$chatTokenStats.loading}
	<Tooltip
		content={`
			<div class="text-xs space-y-1">
				<div class="font-semibold mb-1">${$i18n.t('Token Usage')}</div>
				<div class="flex justify-between gap-4">
					<span>${$i18n.t('Input')}:</span>
					<span class="font-mono">${$chatTokenStats.total_input_tokens.toLocaleString()}</span>
				</div>
				<div class="flex justify-between gap-4">
					<span>${$i18n.t('Output')}:</span>
					<span class="font-mono">${$chatTokenStats.total_output_tokens.toLocaleString()}</span>
				</div>
				<div class="flex justify-between gap-4 border-t border-gray-600 pt-1 mt-1">
					<span>${$i18n.t('Total')}:</span>
					<span class="font-mono font-semibold">${$chatTokenStats.total_tokens.toLocaleString()}</span>
				</div>
				<div class="text-gray-400 text-[10px] mt-2">
					${$chatTokenStats.message_count} ${$i18n.t('messages')}
				</div>
			</div>
		`}
		placement="bottom"
	>
		<div
			class="flex items-center gap-1.5 px-2 py-1 rounded-lg text-[11px] font-mono text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-850 border border-gray-100 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors cursor-default select-none"
		>
			<!-- Input tokens -->
			<span class="flex items-center gap-0.5" title={$i18n.t('Input tokens')}>
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-3 text-blue-500 dark:text-blue-400">
					<path fill-rule="evenodd" d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z" clip-rule="evenodd" />
				</svg>
				<span>{formatTokenCount($chatTokenStats.total_input_tokens)}</span>
			</span>

			<span class="text-gray-300 dark:text-gray-600">·</span>

			<!-- Output tokens -->
			<span class="flex items-center gap-0.5" title={$i18n.t('Output tokens')}>
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-3 text-green-500 dark:text-green-400">
					<path fill-rule="evenodd" d="M8 2a.75.75 0 0 1 .75.75v8.69l3.22-3.22a.75.75 0 1 1 1.06 1.06l-4.5 4.5a.75.75 0 0 1-1.06 0l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.22 3.22V2.75A.75.75 0 0 1 8 2Z" clip-rule="evenodd" />
				</svg>
				<span>{formatTokenCount($chatTokenStats.total_output_tokens)}</span>
			</span>

			<span class="text-gray-300 dark:text-gray-600">·</span>

			<!-- Total tokens -->
			<span class="flex items-center gap-0.5 font-medium text-gray-600 dark:text-gray-300" title={$i18n.t('Total tokens')}>
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-3">
					<path d="M13.488 2.513a1.75 1.75 0 0 0-2.475 0L6.75 6.774a2.75 2.75 0 0 0-.596.892l-.848 2.047a.75.75 0 0 0 .98.98l2.047-.848a2.75 2.75 0 0 0 .892-.596l4.261-4.262a1.75 1.75 0 0 0 0-2.474Z" />
					<path d="M4.75 3.5c-.69 0-1.25.56-1.25 1.25v6.5c0 .69.56 1.25 1.25 1.25h6.5c.69 0 1.25-.56 1.25-1.25V9A.75.75 0 0 1 14 9v2.25A2.75 2.75 0 0 1 11.25 14h-6.5A2.75 2.75 0 0 1 2 11.25v-6.5A2.75 2.75 0 0 1 4.75 2H7a.75.75 0 0 1 0 1.5H4.75Z" />
				</svg>
				<span>{formatTokenCount($chatTokenStats.total_tokens)}</span>
			</span>
		</div>
	</Tooltip>
{:else if $chatTokenStats?.loading}
	<div
		class="flex items-center gap-1.5 px-2 py-1 rounded-lg text-[11px] font-mono text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-850 border border-gray-100 dark:border-gray-800 animate-pulse"
	>
		<span>···</span>
	</div>
{/if}
