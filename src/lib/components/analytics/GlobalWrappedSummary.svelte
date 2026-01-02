<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { getGlobalWrapped, getGlobalModelUsage, formatTokenCount, type GlobalWrappedSummary, type ModelUsage } from '$lib/apis/analytics';

	const i18n = getContext('i18n');

	export let year: number | undefined = undefined;

	let loading = true;
	let error: string | null = null;
	let wrapped: GlobalWrappedSummary | null = null;
	let modelUsage: ModelUsage[] = [];

	// Colors for model leaderboard
	const MEDAL_COLORS = ['#FFD700', '#C0C0C0', '#CD7F32'];

	onMount(async () => {
		await loadGlobalData();
	});

	async function loadGlobalData() {
		loading = true;
		error = null;

		try {
			const token = localStorage.getItem('token');
			if (!token) {
				error = 'Not authenticated';
				loading = false;
				return;
			}

			const [wrappedData, modelData] = await Promise.all([
				getGlobalWrapped(token, year),
				getGlobalModelUsage(token, 10)
			]);

			wrapped = wrappedData;
			modelUsage = modelData;
		} catch (e) {
			error = 'Error loading global data';
			console.error(e);
		}

		loading = false;
	}

	function getModelDisplayName(modelId: string): string {
		const parts = modelId.split('/');
		return parts[parts.length - 1] || modelId;
	}

	$: if (year !== undefined) {
		loadGlobalData();
	}
</script>

<div class="w-full">
	{#if loading}
		<div class="flex items-center justify-center py-24">
			<div class="flex flex-col items-center gap-4">
				<div class="w-16 h-16 border-4 border-[#ff003c] border-t-transparent rounded-full animate-spin"></div>
				<div class="text-[#ff003c] font-mono animate-pulse">ACCESSING_GLOBAL_MAINFRAME...</div>
			</div>
		</div>
	{:else if error}
		<div class="text-center py-24 border border-red-500/50 bg-red-500/10">
			<div class="text-red-500 font-bold text-xl mb-2">SYSTEM_FAILURE</div>
			<div class="text-red-400 font-mono">{error}</div>
		</div>
	{:else if wrapped}
		<!-- Hero Stats -->
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
			<!-- Total Tokens -->
			<div class="group relative bg-black border border-white/20 p-6 hover:border-[#ff003c] transition-colors overflow-hidden">
				<div class="absolute top-0 right-0 p-2 opacity-20 group-hover:opacity-100 transition-opacity">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-12 h-12 text-[#ff003c]">
						<path fill-rule="evenodd" d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12Zm11.378-3.917c-.89-.777-2.366-.777-3.255 0a.75.75 0 0 1-.988-1.129c1.454-1.272 3.776-1.272 5.23 0 1.513 1.324 1.513 3.518 0 4.842a3.75 3.75 0 0 1-.837.552c-.676.328-1.028.774-1.028 1.152v.75a.75.75 0 0 1-1.5 0v-.75c0-1.279 1.06-2.107 1.875-2.502.182-.088.351-.199.503-.331.83-.727.83-1.857 0-2.584ZM12 18a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Z" clip-rule="evenodd" />
					</svg>
				</div>
				<div class="text-xs text-gray-500 uppercase tracking-widest mb-2">Global_Token_Volume</div>
				<div class="text-4xl md:text-5xl font-bold text-white group-hover:text-[#ff003c] transition-colors font-['Koulen']">
					{formatTokenCount(wrapped.total_tokens)}
				</div>
				<div class="mt-4 h-1 w-full bg-white/10">
					<div class="h-full bg-[#ff003c] w-full origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-500"></div>
				</div>
			</div>

			<!-- Active Users -->
			<div class="group relative bg-black border border-white/20 p-6 hover:border-[#ff003c] transition-colors overflow-hidden">
				<div class="absolute top-0 right-0 p-2 opacity-20 group-hover:opacity-100 transition-opacity">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-12 h-12 text-[#ff003c]">
						<path fill-rule="evenodd" d="M7.5 6a4.5 4.5 0 1 1 9 0 4.5 4.5 0 0 1-9 0ZM3.751 20.105a8.25 8.25 0 0 1 16.498 0 .75.75 0 0 1-.437.695A18.683 18.683 0 0 1 12 22.5c-2.786 0-5.433-.608-7.812-1.7a.75.75 0 0 1-.437-.695Z" clip-rule="evenodd" />
					</svg>
				</div>
				<div class="text-xs text-gray-500 uppercase tracking-widest mb-2">Active_Personnel</div>
				<div class="text-4xl md:text-5xl font-bold text-white group-hover:text-[#ff003c] transition-colors font-['Koulen']">
					{wrapped.total_users_active.toLocaleString()}
				</div>
				<div class="mt-4 h-1 w-full bg-white/10">
					<div class="h-full bg-[#ff003c] w-full origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-500 delay-75"></div>
				</div>
			</div>

			<!-- Conversations -->
			<div class="group relative bg-black border border-white/20 p-6 hover:border-[#ff003c] transition-colors overflow-hidden">
				<div class="absolute top-0 right-0 p-2 opacity-20 group-hover:opacity-100 transition-opacity">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-12 h-12 text-[#ff003c]">
						<path fill-rule="evenodd" d="M4.804 21.644A6.707 6.707 0 0 0 6 21.75a6.721 6.721 0 0 0 3.583-1.029c.774.182 1.584.279 2.417.279 5.322 0 9.75-3.97 9.75-9 0-5.03-4.428-9-9.75-9s-9.75 3.97-9.75 9c0 2.409 1.025 4.587 2.674 6.192.232.226.277.428.254.543a3.73 3.73 0 0 1-.814 1.686.75.75 0 0 0 .44 1.223ZM8.25 10.875a1.125 1.125 0 1 0 0 2.25 1.125 1.125 0 0 0 0-2.25ZM10.875 12a1.125 1.125 0 1 1 2.25 0 1.125 1.125 0 0 1-2.25 0Zm4.875-1.125a1.125 1.125 0 1 0 0 2.25 1.125 1.125 0 0 0 0-2.25Z" clip-rule="evenodd" />
					</svg>
				</div>
				<div class="text-xs text-gray-500 uppercase tracking-widest mb-2">Total_Conversations</div>
				<div class="text-4xl md:text-5xl font-bold text-white group-hover:text-[#ff003c] transition-colors font-['Koulen']">
					{wrapped.total_conversations.toLocaleString()}
				</div>
				<div class="mt-4 h-1 w-full bg-white/10">
					<div class="h-full bg-[#ff003c] w-full origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-500 delay-150"></div>
				</div>
			</div>

			<!-- Messages -->
			<div class="group relative bg-black border border-white/20 p-6 hover:border-[#ff003c] transition-colors overflow-hidden">
				<div class="absolute top-0 right-0 p-2 opacity-20 group-hover:opacity-100 transition-opacity">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-12 h-12 text-[#ff003c]">
						<path fill-rule="evenodd" d="M4.848 2.771A49.144 49.144 0 0 1 12 2.25c2.43 0 4.817.178 7.152.52 1.978.292 3.348 2.024 3.348 3.97v6.02c0 1.946-1.37 3.678-3.348 3.97a48.901 48.901 0 0 1-3.476.383.39.39 0 0 0-.297.17l-2.755 4.133a.75.75 0 0 1-1.248 0l-2.755-4.133a.39.39 0 0 0-.297-.17 48.9 48.9 0 0 1-3.476-.384c-1.978-.29-3.348-2.024-3.348-3.97V6.741c0-1.946 1.37-3.68 3.348-3.97ZM6.75 8.25a.75.75 0 0 1 .75-.75h9a.75.75 0 0 1 0 1.5h-9a.75.75 0 0 1-.75-.75Zm.75 2.25a.75.75 0 0 0 0 1.5H12a.75.75 0 0 0 0-1.5H7.5Z" clip-rule="evenodd" />
					</svg>
				</div>
				<div class="text-xs text-gray-500 uppercase tracking-widest mb-2">Total_Messages</div>
				<div class="text-4xl md:text-5xl font-bold text-white group-hover:text-[#ff003c] transition-colors font-['Koulen']">
					{wrapped.total_messages.toLocaleString()}
				</div>
				<div class="mt-4 h-1 w-full bg-white/10">
					<div class="h-full bg-[#ff003c] w-full origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-500 delay-200"></div>
				</div>
			</div>
		</div>

		<!-- Busiest Day -->
		{#if wrapped.busiest_day}
			<div class="mb-12">
				<div class="relative group">
					<div class="absolute -inset-0.5 bg-gradient-to-r from-[#ff003c] to-orange-600 opacity-20 group-hover:opacity-100 transition duration-500 blur"></div>
					<div class="relative bg-black border border-white/10 p-8">
						<div class="flex items-center justify-between mb-6">
							<div>
								<h4 class="text-sm text-gray-500 uppercase tracking-widest mb-1">
									{$i18n.t('System_Peak_Load')}
								</h4>
								<div class="text-3xl font-bold text-white font-['Koulen']">
									{wrapped.busiest_day.day_of_week}
								</div>
							</div>
							<div class="p-3 bg-[#ff003c]/10 border border-[#ff003c]/20 text-[#ff003c]">
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="size-6">
									<path fill-rule="evenodd" d="M12.963 2.286a.75.75 0 0 0-1.071-.136 9.742 9.742 0 0 0-3.539 6.176 7.547 7.547 0 0 1-1.705-1.715.75.75 0 0 0-1.152-.082A9 9 0 1 0 15.68 4.534a7.46 7.46 0 0 1-2.717-2.248ZM15.75 14.25a3.75 3.75 0 1 1-7.313-1.172c.628.465 1.35.81 2.133 1a5.99 5.99 0 0 1 1.925-3.546 3.75 3.75 0 0 1 3.255 3.718Z" clip-rule="evenodd" />
								</svg>
							</div>
						</div>
						
						<div class="grid grid-cols-1 md:grid-cols-2 gap-8">
							<div class="flex justify-between items-end border-b border-white/10 pb-2">
								<span class="text-xs text-gray-500 uppercase">Date</span>
								<span class="font-mono text-[#ff003c]">
									{new Date(wrapped.busiest_day.date).toLocaleDateString(undefined, { 
										year: 'numeric',
										month: 'long', 
										day: 'numeric' 
									})}
								</span>
							</div>
							<div class="flex justify-between items-end border-b border-white/10 pb-2">
								<span class="text-xs text-gray-500 uppercase">Token_Throughput</span>
								<span class="font-mono text-[#ff003c]">
									{formatTokenCount(wrapped.busiest_day.tokens)}
								</span>
							</div>
						</div>
					</div>
				</div>
			</div>
		{/if}

		<!-- Model Leaderboard -->
		{#if modelUsage.length > 0}
			<div>
				<div class="flex items-center gap-4 mb-8">
					<div class="w-3 h-3 bg-[#ff003c]"></div>
					<h3 class="text-2xl font-bold uppercase tracking-widest text-white">
						{$i18n.t('Model_Performance_Ranking')}
					</h3>
					<div class="h-px flex-1 bg-white/10"></div>
				</div>

				<div class="space-y-4">
					{#each modelUsage as model, index}
						<div class="group relative bg-black border border-white/10 p-4 hover:border-[#ff003c] transition-colors">
							<div class="flex items-center gap-6">
								<div class="text-4xl font-['Koulen'] w-12 text-center {index < 3 ? 'text-[#ff003c]' : 'text-gray-700'}">
									#{index + 1}
								</div>
								
								<div class="flex-1 min-w-0">
									<div class="flex items-center justify-between mb-2">
										<div class="font-bold text-white truncate text-lg">
											{getModelDisplayName(model.model_id)}
										</div>
										<div class="font-mono text-[#ff003c]">
											{model.percentage.toFixed(1)}%
										</div>
									</div>
									
									<div class="h-2 bg-white/5 w-full overflow-hidden">
										<div 
											class="h-full bg-[#ff003c] transition-all duration-1000 ease-out"
											style="width: {model.percentage}%"
										></div>
									</div>
									
									<div class="flex justify-between mt-2 text-xs text-gray-500 uppercase tracking-wider">
										<span>{model.conversation_count.toLocaleString()} Conversations</span>
										<span>{formatTokenCount(model.total_tokens)} Tokens</span>
									</div>
								</div>
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Top Models from wrapped -->
		{#if wrapped.top_models && wrapped.top_models.length > 0}
			<!-- Already showing model leaderboard above -->
		{/if}
	{:else}
		<div class="text-center py-24 border border-white/10 bg-white/5">
			<div class="text-gray-500 font-mono">NO_GLOBAL_DATA_AVAILABLE</div>
		</div>
	{/if}
</div>
