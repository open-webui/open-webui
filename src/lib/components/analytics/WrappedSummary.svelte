<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { getUserWrapped, formatTokenCount, type WrappedSummary } from '$lib/apis/analytics';

	const i18n = getContext('i18n');

	export let year: number | undefined = undefined;

	let loading = true;
	let error: string | null = null;
	let wrapped: WrappedSummary | null = null;

	onMount(async () => {
		await loadWrappedData();
	});

	async function loadWrappedData() {
		loading = true;
		error = null;

		try {
			const token = localStorage.getItem('token');
			if (!token) {
				error = 'Not authenticated';
				loading = false;
				return;
			}

			wrapped = await getUserWrapped(token, year);
		} catch (e) {
			error = 'Error loading wrapped data';
			console.error(e);
		}

		loading = false;
	}

	function getTimeOfDay(date: string): string {
		// Just return the day of week for now since we track by day
		return '';
	}
</script>

<div class="w-full">
	{#if loading}
		<div class="flex items-center justify-center py-24">
			<div class="flex flex-col items-center gap-4">
				<div class="w-16 h-16 border-4 border-[#00ff41] border-t-transparent rounded-full animate-spin"></div>
				<div class="text-[#00ff41] font-mono animate-pulse">LOADING_DATA_STREAM...</div>
			</div>
		</div>
	{:else if error}
		<div class="text-center py-24 border border-red-500/50 bg-red-500/10">
			<div class="text-red-500 font-bold text-xl mb-2">SYSTEM_ERROR</div>
			<div class="text-red-400 font-mono">{error}</div>
		</div>
	{:else if wrapped}
		<!-- Hero Stats -->
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
			<!-- Total Tokens -->
			<div class="group relative bg-black border border-white/20 p-6 hover:border-[#00ff41] transition-colors overflow-hidden">
				<div class="absolute top-0 right-0 p-2 opacity-20 group-hover:opacity-100 transition-opacity">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-12 h-12 text-[#00ff41]">
						<path fill-rule="evenodd" d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12Zm11.378-3.917c-.89-.777-2.366-.777-3.255 0a.75.75 0 0 1-.988-1.129c1.454-1.272 3.776-1.272 5.23 0 1.513 1.324 1.513 3.518 0 4.842a3.75 3.75 0 0 1-.837.552c-.676.328-1.028.774-1.028 1.152v.75a.75.75 0 0 1-1.5 0v-.75c0-1.279 1.06-2.107 1.875-2.502.182-.088.351-.199.503-.331.83-.727.83-1.857 0-2.584ZM12 18a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Z" clip-rule="evenodd" />
					</svg>
				</div>
				<div class="text-xs text-gray-500 uppercase tracking-widest mb-2">Total_Tokens</div>
				<div class="text-4xl md:text-5xl font-bold text-white group-hover:text-[#00ff41] transition-colors font-['Koulen']">
					{formatTokenCount(wrapped.total_tokens)}
				</div>
				<div class="mt-4 h-1 w-full bg-white/10">
					<div class="h-full bg-[#00ff41] w-full origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-500"></div>
				</div>
			</div>

			<!-- Conversations -->
			<div class="group relative bg-black border border-white/20 p-6 hover:border-[#00ff41] transition-colors overflow-hidden">
				<div class="absolute top-0 right-0 p-2 opacity-20 group-hover:opacity-100 transition-opacity">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-12 h-12 text-[#00ff41]">
						<path fill-rule="evenodd" d="M4.804 21.644A6.707 6.707 0 0 0 6 21.75a6.721 6.721 0 0 0 3.583-1.029c.774.182 1.584.279 2.417.279 5.322 0 9.75-3.97 9.75-9 0-5.03-4.428-9-9.75-9s-9.75 3.97-9.75 9c0 2.409 1.025 4.587 2.674 6.192.232.226.277.428.254.543a3.73 3.73 0 0 1-.814 1.686.75.75 0 0 0 .44 1.223ZM8.25 10.875a1.125 1.125 0 1 0 0 2.25 1.125 1.125 0 0 0 0-2.25ZM10.875 12a1.125 1.125 0 1 1 2.25 0 1.125 1.125 0 0 1-2.25 0Zm4.875-1.125a1.125 1.125 0 1 0 0 2.25 1.125 1.125 0 0 0 0-2.25Z" clip-rule="evenodd" />
					</svg>
				</div>
				<div class="text-xs text-gray-500 uppercase tracking-widest mb-2">Conversations</div>
				<div class="text-4xl md:text-5xl font-bold text-white group-hover:text-[#00ff41] transition-colors font-['Koulen']">
					{wrapped.total_conversations.toLocaleString()}
				</div>
				<div class="mt-4 h-1 w-full bg-white/10">
					<div class="h-full bg-[#00ff41] w-full origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-500 delay-75"></div>
				</div>
			</div>

			<!-- Messages -->
			<div class="group relative bg-black border border-white/20 p-6 hover:border-[#00ff41] transition-colors overflow-hidden">
				<div class="absolute top-0 right-0 p-2 opacity-20 group-hover:opacity-100 transition-opacity">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-12 h-12 text-[#00ff41]">
						<path fill-rule="evenodd" d="M4.848 2.771A49.144 49.144 0 0 1 12 2.25c2.43 0 4.817.178 7.152.52 1.978.292 3.348 2.024 3.348 3.97v6.02c0 1.946-1.37 3.678-3.348 3.97a48.901 48.901 0 0 1-3.476.383.39.39 0 0 0-.297.17l-2.755 4.133a.75.75 0 0 1-1.248 0l-2.755-4.133a.39.39 0 0 0-.297-.17 48.9 48.9 0 0 1-3.476-.384c-1.978-.29-3.348-2.024-3.348-3.97V6.741c0-1.946 1.37-3.68 3.348-3.97ZM6.75 8.25a.75.75 0 0 1 .75-.75h9a.75.75 0 0 1 0 1.5h-9a.75.75 0 0 1-.75-.75Zm.75 2.25a.75.75 0 0 0 0 1.5H12a.75.75 0 0 0 0-1.5H7.5Z" clip-rule="evenodd" />
					</svg>
				</div>
				<div class="text-xs text-gray-500 uppercase tracking-widest mb-2">Messages</div>
				<div class="text-4xl md:text-5xl font-bold text-white group-hover:text-[#00ff41] transition-colors font-['Koulen']">
					{wrapped.total_messages.toLocaleString()}
				</div>
				<div class="mt-4 h-1 w-full bg-white/10">
					<div class="h-full bg-[#00ff41] w-full origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-500 delay-150"></div>
				</div>
			</div>

			<!-- Days Active -->
			<div class="group relative bg-black border border-white/20 p-6 hover:border-[#00ff41] transition-colors overflow-hidden">
				<div class="absolute top-0 right-0 p-2 opacity-20 group-hover:opacity-100 transition-opacity">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-12 h-12 text-[#00ff41]">
						<path d="M12.75 12.75a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM7.5 15.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5ZM8.25 17.25a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM9.75 15.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5ZM10.5 17.25a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM12 15.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5ZM12.75 17.25a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM14.25 15.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5ZM15 17.25a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM16.5 15.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5ZM15 12.75a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM16.5 13.5a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Z" />
						<path fill-rule="evenodd" d="M6.75 2.25A.75.75 0 0 1 7.5 3v1.5h9V3A.75.75 0 0 1 18 3v1.5h.75a3 3 0 0 1 3 3v11.25a3 3 0 0 1-3 3H5.25a3 3 0 0 1-3-3V7.5a3 3 0 0 1 3-3H6V3a.75.75 0 0 1 .75-.75Zm13.5 9a1.5 1.5 0 0 0-1.5-1.5H5.25a1.5 1.5 0 0 0-1.5 1.5v7.5a1.5 1.5 0 0 0 1.5 1.5h13.5a1.5 1.5 0 0 0 1.5-1.5v-7.5Z" clip-rule="evenodd" />
					</svg>
				</div>
				<div class="text-xs text-gray-500 uppercase tracking-widest mb-2">Days_Active</div>
				<div class="text-4xl md:text-5xl font-bold text-white group-hover:text-[#00ff41] transition-colors font-['Koulen']">
					{wrapped.days_active}
				</div>
				<div class="mt-4 h-1 w-full bg-white/10">
					<div class="h-full bg-[#00ff41] w-full origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-500 delay-200"></div>
				</div>
			</div>
		</div>

		<!-- Input/Output breakdown -->
		<div class="mb-12">
			<div class="flex items-center gap-4 mb-6">
				<div class="w-3 h-3 bg-[#00ff41]"></div>
				<h3 class="text-xl font-bold uppercase tracking-widest text-white">
					{$i18n.t('Token_Distribution')}
				</h3>
				<div class="h-px flex-1 bg-white/10"></div>
			</div>
			
			<div class="bg-black/50 border border-white/10 p-8 backdrop-blur-sm">
				<div class="flex flex-col gap-8">
					<!-- Input bar -->
					<div class="group">
						<div class="flex items-end justify-between mb-2">
							<span class="text-sm text-gray-400 uppercase tracking-widest flex items-center gap-2">
								<span class="w-2 h-2 bg-blue-500"></span>
								{$i18n.t('Input')}
							</span>
							<span class="text-2xl font-bold text-white font-['Koulen']">
								{formatTokenCount(wrapped.total_input_tokens)}
							</span>
						</div>
						<div class="h-4 bg-white/5 w-full overflow-hidden relative">
							<!-- Grid lines -->
							<div class="absolute inset-0 z-10" style="background-image: linear-gradient(90deg, transparent 98%, rgba(0,0,0,0.5) 98%); background-size: 2% 100%;"></div>
							<div 
								class="h-full bg-blue-500 transition-all duration-1000 ease-out relative"
								style="width: {wrapped.total_tokens > 0 ? (wrapped.total_input_tokens / wrapped.total_tokens * 100) : 0}%"
							>
								<div class="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20"></div>
							</div>
						</div>
					</div>
					
					<!-- Output bar -->
					<div class="group">
						<div class="flex items-end justify-between mb-2">
							<span class="text-sm text-gray-400 uppercase tracking-widest flex items-center gap-2">
								<span class="w-2 h-2 bg-[#00ff41]"></span>
								{$i18n.t('Output')}
							</span>
							<span class="text-2xl font-bold text-white font-['Koulen']">
								{formatTokenCount(wrapped.total_output_tokens)}
							</span>
						</div>
						<div class="h-4 bg-white/5 w-full overflow-hidden relative">
							<!-- Grid lines -->
							<div class="absolute inset-0 z-10" style="background-image: linear-gradient(90deg, transparent 98%, rgba(0,0,0,0.5) 98%); background-size: 2% 100%;"></div>
							<div 
								class="h-full bg-[#00ff41] transition-all duration-1000 ease-out relative"
								style="width: {wrapped.total_tokens > 0 ? (wrapped.total_output_tokens / wrapped.total_tokens * 100) : 0}%"
							>
								<div class="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20"></div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Highlights -->
		<div class="grid grid-cols-1 md:grid-cols-2 gap-8">
			<!-- Most Active Day -->
			{#if wrapped.most_active_day}
				<div class="relative group">
					<div class="absolute -inset-0.5 bg-gradient-to-r from-orange-600 to-red-600 opacity-20 group-hover:opacity-100 transition duration-500 blur"></div>
					<div class="relative bg-black border border-white/10 p-8 h-full">
						<div class="flex items-start justify-between mb-6">
							<div>
								<h4 class="text-sm text-gray-500 uppercase tracking-widest mb-1">
									{$i18n.t('Peak_Activity_Vector')}
								</h4>
								<div class="text-3xl font-bold text-white font-['Koulen']">
									{wrapped.most_active_day.day_of_week}
								</div>
							</div>
							<div class="p-3 bg-orange-500/10 border border-orange-500/20 text-orange-500">
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="size-6">
									<path fill-rule="evenodd" d="M12.963 2.286a.75.75 0 0 0-1.071-.136 9.742 9.742 0 0 0-3.539 6.176 7.547 7.547 0 0 1-1.705-1.715.75.75 0 0 0-1.152-.082A9 9 0 1 0 15.68 4.534a7.46 7.46 0 0 1-2.717-2.248ZM15.75 14.25a3.75 3.75 0 1 1-7.313-1.172c.628.465 1.35.81 2.133 1a5.99 5.99 0 0 1 1.925-3.546 3.75 3.75 0 0 1 3.255 3.718Z" clip-rule="evenodd" />
								</svg>
							</div>
						</div>
						
						<div class="space-y-4">
							<div class="flex justify-between items-end border-b border-white/10 pb-2">
								<span class="text-xs text-gray-500 uppercase">Date</span>
								<span class="font-mono text-orange-500">
									{new Date(wrapped.most_active_day.date).toLocaleDateString(undefined, { 
										year: 'numeric',
										month: '2-digit', 
										day: '2-digit' 
									})}
								</span>
							</div>
							<div class="flex justify-between items-end border-b border-white/10 pb-2">
								<span class="text-xs text-gray-500 uppercase">Volume</span>
								<span class="font-mono text-orange-500">
									{formatTokenCount(wrapped.most_active_day.tokens)}
								</span>
							</div>
						</div>
					</div>
				</div>
			{/if}

			<!-- Favorite Model -->
			{#if wrapped.favorite_model}
				<div class="relative group">
					<div class="absolute -inset-0.5 bg-gradient-to-r from-purple-600 to-pink-600 opacity-20 group-hover:opacity-100 transition duration-500 blur"></div>
					<div class="relative bg-black border border-white/10 p-8 h-full">
						<div class="flex items-start justify-between mb-6">
							<div>
								<h4 class="text-sm text-gray-500 uppercase tracking-widest mb-1">
									{$i18n.t('Primary_Neural_Link')}
								</h4>
								<div class="text-3xl font-bold text-white font-['Koulen'] truncate max-w-[200px]">
									{wrapped.favorite_model.model_id.split('/').pop() || wrapped.favorite_model.model_id}
								</div>
							</div>
							<div class="p-3 bg-purple-500/10 border border-purple-500/20 text-purple-500">
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="size-6">
									<path fill-rule="evenodd" d="M10.788 3.21c.448-1.077 1.976-1.077 2.424 0l2.082 5.006 5.404.434c1.164.093 1.636 1.545.749 2.305l-4.117 3.527 1.257 5.273c.271 1.136-.964 2.033-1.96 1.425L12 18.354 7.373 21.18c-.996.608-2.231-.29-1.96-1.425l1.257-5.273-4.117-3.527c-.887-.76-.415-2.212.749-2.305l5.404-.434 2.082-5.005Z" clip-rule="evenodd" />
								</svg>
							</div>
						</div>
						
						<div class="space-y-4">
							<div class="flex justify-between items-end border-b border-white/10 pb-2">
								<span class="text-xs text-gray-500 uppercase">Usage_Share</span>
								<span class="font-mono text-purple-500">
									{wrapped.favorite_model.percentage.toFixed(1)}%
								</span>
							</div>
							<div class="flex justify-between items-end border-b border-white/10 pb-2">
								<span class="text-xs text-gray-500 uppercase">Total_Tokens</span>
								<span class="font-mono text-purple-500">
									{formatTokenCount(wrapped.favorite_model.total_tokens)}
								</span>
							</div>
						</div>
					</div>
				</div>
			{/if}
		</div>
	{:else}
		<div class="text-center py-24 border border-white/10 bg-white/5">
			<div class="text-gray-500 font-mono">NO_DATA_FOUND_FOR_SELECTED_PERIOD</div>
		</div>
	{/if}
</div>
