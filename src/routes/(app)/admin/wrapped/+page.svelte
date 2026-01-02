<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';

	import GlobalWrappedSummary from '$lib/components/analytics/GlobalWrappedSummary.svelte';
	import GlobalActivityHeatmap from '$lib/components/analytics/GlobalActivityHeatmap.svelte';

	const i18n = getContext('i18n');

	// Get current year by default
	let selectedYear: number = new Date().getFullYear();
	
	// Generate available years
	const currentYear = new Date().getFullYear();
	const availableYears = Array.from({ length: 5 }, (_, i) => currentYear - i);

	onMount(() => {
		// Redirect if not admin
		if (!$user || $user.role !== 'admin') {
			goto('/');
		}
	});
</script>

<svelte:head>
	<title>Global {selectedYear} Wrapped | Admin | Open WebUI</title>
	<link rel="preconnect" href="https://fonts.googleapis.com">
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous">
	<link href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@300;400;500;600;700&family=Koulen&display=swap" rel="stylesheet">
</svelte:head>

<div class="min-h-screen bg-[#050505] text-gray-100 font-['Chakra_Petch'] selection:bg-[#ff003c] selection:text-white overflow-x-hidden">
	<!-- CRT Overlay Effect -->
	<div class="fixed inset-0 pointer-events-none z-50 opacity-[0.03] bg-[url('https://grainy-gradients.vercel.app/noise.svg')]"></div>
	<div class="fixed inset-0 pointer-events-none z-50 bg-gradient-to-b from-transparent via-transparent to-black/20 bg-[length:100%_4px]"></div>

	<!-- Grid Background -->
	<div class="fixed inset-0 pointer-events-none z-0 opacity-10" 
		style="background-image: linear-gradient(#333 1px, transparent 1px), linear-gradient(90deg, #333 1px, transparent 1px); background-size: 40px 40px;">
	</div>

	<!-- Header -->
	<div class="relative z-10 pt-12 pb-8 px-4 border-b border-white/10 bg-[#050505]/80 backdrop-blur-sm">
		<div class="max-w-6xl mx-auto">
			<div class="flex flex-col md:flex-row items-center justify-between gap-6 mb-12">
				<button
					class="group flex items-center gap-3 text-gray-400 hover:text-[#ff003c] transition-colors uppercase tracking-widest text-xs font-bold"
					on:click={() => goto('/admin')}
				>
					<div class="w-8 h-8 border border-current flex items-center justify-center group-hover:bg-[#ff003c] group-hover:text-white transition-all">
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-4">
							<path fill-rule="evenodd" d="M17 10a.75.75 0 0 1-.75.75H5.612l4.158 3.96a.75.75 0 1 1-1.04 1.08l-5.5-5.25a.75.75 0 0 1 0-1.08l5.5-5.25a.75.75 0 1 1 1.04 1.08L5.612 9.25H16.25A.75.75 0 0 1 17 10Z" clip-rule="evenodd" />
						</svg>
					</div>
					{$i18n.t('Admin_Console')}
				</button>

				<!-- Year Selector -->
				<div class="flex items-center gap-4">
					<div class="relative group">
						<select
							id="year-select"
							bind:value={selectedYear}
							class="appearance-none bg-black border border-white/20 text-[#ff003c] rounded-none px-6 py-2 pr-10 text-lg font-bold focus:outline-none focus:border-[#ff003c] cursor-pointer uppercase tracking-widest hover:bg-[#ff003c]/10 transition-colors"
						>
							{#each availableYears as year}
								<option value={year} class="bg-black text-gray-300">{year}</option>
							{/each}
						</select>
						<div class="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-[#ff003c]">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-4">
								<path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd" />
							</svg>
						</div>
					</div>
				</div>
			</div>

			<div class="flex items-center justify-center gap-2 mb-4">
				<span class="px-3 py-1 border border-[#ff003c] text-[#ff003c] text-xs font-bold uppercase tracking-widest bg-[#ff003c]/10">
					{$i18n.t('Restricted_Access_Level_5')}
				</span>
			</div>

			<div class="text-center relative">
				<div class="inline-block">
					<h1 class="text-6xl md:text-9xl font-['Koulen'] text-white leading-none tracking-tighter uppercase mix-blend-difference relative z-10">
						Global <span class="text-transparent bg-clip-text bg-gradient-to-r from-[#ff003c] to-[#ff003c]">Wrapped</span>
					</h1>
					<div class="h-1 w-full bg-[#ff003c] mt-2"></div>
					<p class="text-[#ff003c] font-mono text-sm md:text-base mt-4 tracking-[0.2em] uppercase">
						// {$i18n.t('System_Wide_Analytics_Core')} //
					</p>
				</div>
			</div>
		</div>
	</div>

	<!-- Main content -->
	<div class="max-w-6xl mx-auto px-4 py-12 relative z-10">
		{#key selectedYear}
			<!-- Global Wrapped Summary -->
			<GlobalWrappedSummary year={selectedYear} />

			<!-- Global Activity Heatmap -->
			<div class="mt-24 border-t border-white/10 pt-12">
				<div class="flex items-center gap-4 mb-8">
					<div class="w-3 h-3 bg-[#ff003c]"></div>
					<h2 class="text-2xl font-bold uppercase tracking-widest text-white">
						{$i18n.t('Global_Activity_Matrix')}
					</h2>
					<div class="h-px flex-1 bg-white/10"></div>
				</div>
				<div class="bg-black/50 border border-white/10 p-6 backdrop-blur-sm">
					<GlobalActivityHeatmap year={selectedYear} />
				</div>
			</div>
		{/key}

		<!-- Footer -->
		<div class="text-center py-24 border-t border-white/10 mt-24">
			<p class="text-xs font-mono text-gray-600 uppercase tracking-widest">
				{$i18n.t('System_Generated')} // Open WebUI Analytics Core
			</p>
			<button
				class="mt-6 text-sm font-bold text-white hover:text-[#ff003c] border border-white/20 hover:border-[#ff003c] px-6 py-2 transition-all uppercase tracking-widest"
				on:click={() => goto('/wrapped')}
			>
				<< {$i18n.t('Return_To_User_Interface')}
			</button>
		</div>
	</div>
</div>

<style>
	/* Custom Scrollbar */
	:global(::-webkit-scrollbar) {
		width: 8px;
		height: 8px;
	}
	:global(::-webkit-scrollbar-track) {
		background: #050505;
	}
	:global(::-webkit-scrollbar-thumb) {
		background: #333;
		border: 1px solid #050505;
	}
	:global(::-webkit-scrollbar-thumb:hover) {
		background: #ff003c;
	}
</style>
