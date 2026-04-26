<script lang="ts">
	import { getContext } from 'svelte';
	import { fade, fly } from 'svelte/transition';

	const i18n = getContext('i18n');

	export let open = false;

	const tiers = [
		{
			color: '#EA580C',
			name: 'Claude Haiku',
			tagline: () => $i18n.t('Fast & efficient'),
			useCases: () => [
				$i18n.t('Quick questions and answers'),
				$i18n.t('Translations and summaries'),
				$i18n.t('Simple drafts and edits'),
				$i18n.t('Repetitive tasks'),
			],
			note: () => $i18n.t('Default model — lowest cost per token'),
		},
		{
			color: '#F59E0B',
			name: 'Claude Sonnet',
			tagline: () => $i18n.t('Balanced — the workhorse'),
			useCases: () => [
				$i18n.t('Complex analysis and research'),
				$i18n.t('Writing and content creation'),
				$i18n.t('Coding and debugging'),
				$i18n.t('Multi-step reasoning'),
			],
			note: () => $i18n.t('Recommended for most professional tasks'),
		},
		{
			color: '#16A34A',
			name: 'Claude Opus',
			tagline: () => $i18n.t('Most powerful'),
			useCases: () => [
				$i18n.t('Deep strategic analysis'),
				$i18n.t('Complex legal or medical review'),
				$i18n.t('Advanced code architecture'),
				$i18n.t('When quality matters most'),
			],
			note: () => $i18n.t('Highest quality — uses more tokens'),
		},
		{
			color: '#7C3AED',
			name: 'Mistral',
			tagline: () => $i18n.t('EU-native alternative'),
			useCases: () => [
				$i18n.t('When EU-only inference is required'),
				$i18n.t('Fallback when Claude is unavailable'),
				$i18n.t('French-language documents'),
			],
			note: () => $i18n.t('Data stays in France — GDPR fallback'),
		},
	];
</script>

{#if open}
	<!-- Backdrop -->
	<button
		class="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm cursor-default"
		transition:fade={{ duration: 150 }}
		on:click={() => (open = false)}
		aria-label="Close"
	/>

	<!-- Panel -->
	<div
		class="fixed bottom-0 left-0 right-0 z-50 mx-auto max-w-2xl"
		transition:fly={{ y: 40, duration: 220 }}
	>
		<div class="rounded-t-2xl bg-white dark:bg-gray-900 border border-black/[.08] dark:border-white/[.08] shadow-2xl overflow-hidden">
			<!-- Header -->
			<div class="flex items-center justify-between px-6 py-4 border-b border-black/[.06] dark:border-white/[.06]">
				<div>
					<p class="text-sm font-semibold text-gray-900 dark:text-white">{$i18n.t('Know the models')}</p>
					<p class="text-[11px] text-gray-400 mt-0.5">{$i18n.t('Each colored dot in the selector represents a model tier')}</p>
				</div>
				<button
					class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition cursor-pointer p-1 rounded-lg hover:bg-black/[.05] dark:hover:bg-white/[.05]"
					on:click={() => (open = false)}
					aria-label="Close"
				>
					<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6 6 18M6 6l12 12"/></svg>
				</button>
			</div>

			<!-- Tiers grid -->
			<div class="grid grid-cols-2 gap-3 p-5 max-h-[60vh] overflow-y-auto scrollbar-none">
				{#each tiers as tier}
					<div class="rounded-xl border border-black/[.06] dark:border-white/[.06] p-4">
						<div class="flex items-center gap-2 mb-2">
							<span class="size-2.5 rounded-full shrink-0" style="background:{tier.color}" />
							<p class="text-xs font-bold text-gray-800 dark:text-white">{tier.name}</p>
						</div>
						<p class="text-[11px] font-semibold mb-2" style="color:{tier.color}">{tier.tagline()}</p>
						<ul class="space-y-1 mb-3">
							{#each tier.useCases() as uc}
								<li class="text-[11px] text-gray-500 dark:text-gray-400 flex gap-1.5 items-start">
									<span class="mt-[3px] shrink-0 size-1 rounded-full bg-gray-300 dark:bg-gray-600" />
									{uc}
								</li>
							{/each}
						</ul>
						<p class="text-[10px] text-gray-400 dark:text-gray-500 italic">{tier.note()}</p>
					</div>
				{/each}
			</div>

			<!-- Footer tip -->
			<div class="px-6 py-3 border-t border-black/[.06] dark:border-white/[.06] bg-gray-50 dark:bg-gray-800/50">
				<p class="text-[11px] text-gray-400 text-center">
					{$i18n.t('Tip: look for the colored dot next to each model name in the selector')}
				</p>
			</div>
		</div>
	</div>
{/if}
