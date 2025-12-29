<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { getUserTopChats, formatTokenCount, type TopChat } from '$lib/apis/analytics';

	const i18n = getContext('i18n');

	export let year: number | undefined = undefined;
	export let limit: number = 10;

	let loading = true;
	let error: string | null = null;
	let topChats: TopChat[] = [];

	onMount(async () => {
		await loadTopChats();
	});

	async function loadTopChats() {
		loading = true;
		error = null;

		try {
			const token = localStorage.getItem('token');
			if (!token) {
				error = 'Not authenticated';
				loading = false;
				return;
			}

			topChats = await getUserTopChats(token, year, limit);
		} catch (e) {
			error = 'Error loading top chats';
			console.error(e);
		}

		loading = false;
	}

	function navigateToChat(chatId: string) {
		goto(`/c/${chatId}`);
	}

	function getBarWidth(tokens: number, maxTokens: number): number {
		if (maxTokens === 0) return 0;
		return (tokens / maxTokens) * 100;
	}

	$: maxTokens = topChats.length > 0 ? topChats[0].total_tokens : 0;
</script>

<div class="w-full">
	<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
		{$i18n.t('Top Conversations')}
	</h3>

	{#if loading}
		<div class="flex items-center justify-center py-8">
			<div class="animate-spin rounded-full h-6 w-6 border-b-2 border-emerald-500"></div>
		</div>
	{:else if error}
		<div class="text-center py-6 text-gray-500 dark:text-gray-400">
			{error}
		</div>
	{:else if topChats.length === 0}
		<div class="text-center py-6 text-gray-500 dark:text-gray-400">
			{$i18n.t('No conversations yet')}
		</div>
	{:else}
		<div class="space-y-3">
			{#each topChats as chat, index}
				<button
					class="w-full text-left p-3 rounded-lg bg-gray-50 dark:bg-gray-850 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
					on:click={() => navigateToChat(chat.chat_id)}
				>
					<div class="flex items-start justify-between gap-3">
						<div class="flex-1 min-w-0">
							<div class="flex items-center gap-2 mb-1">
								<span class="text-sm font-medium text-gray-400 dark:text-gray-500">
									#{index + 1}
								</span>
								<span class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
									{chat.title || $i18n.t('Untitled Chat')}
								</span>
							</div>
							
							<!-- Token bar -->
							<div class="relative h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden mb-2">
								<div 
									class="absolute top-0 left-0 h-full bg-gradient-to-r from-emerald-400 to-emerald-500 rounded-full transition-all duration-500"
									style="width: {getBarWidth(chat.total_tokens, maxTokens)}%"
								></div>
							</div>

							<div class="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
								<span class="flex items-center gap-1">
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-3 text-blue-500">
										<path fill-rule="evenodd" d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z" clip-rule="evenodd" />
									</svg>
									{formatTokenCount(chat.total_input_tokens)}
								</span>
								<span class="flex items-center gap-1">
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-3 text-green-500">
										<path fill-rule="evenodd" d="M8 2a.75.75 0 0 1 .75.75v8.69l3.22-3.22a.75.75 0 1 1 1.06 1.06l-4.5 4.5a.75.75 0 0 1-1.06 0l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.22 3.22V2.75A.75.75 0 0 1 8 2Z" clip-rule="evenodd" />
									</svg>
									{formatTokenCount(chat.total_output_tokens)}
								</span>
								<span>•</span>
								<span>{chat.message_count} {$i18n.t('messages')}</span>
								{#if chat.model_id}
									<span>•</span>
									<span class="text-gray-400 dark:text-gray-500 truncate max-w-[150px]">
										{chat.model_id}
									</span>
								{/if}
							</div>
						</div>

						<div class="flex-shrink-0 text-right">
							<span class="text-lg font-bold text-emerald-600 dark:text-emerald-400">
								{formatTokenCount(chat.total_tokens)}
							</span>
							<div class="text-xs text-gray-500 dark:text-gray-400">
								{$i18n.t('tokens')}
							</div>
						</div>
					</div>
				</button>
			{/each}
		</div>
	{/if}
</div>
