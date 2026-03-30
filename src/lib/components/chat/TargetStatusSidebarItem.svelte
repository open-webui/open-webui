<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';

	import type { Target } from '$lib/components/workspace/Targets/types';
	import { getTargetStatusClass } from '$lib/components/workspace/Targets/status';

	const i18n = getContext<any>('i18n');
	const dispatch = createEventDispatcher<{ select: string; queue: string; toggle: string }>();

	export let target: Target;
	export let active = false;

	$: secondaryText = target.lastScan
		? `${$i18n.t('Last scan')}: ${target.lastScan}`
		: `${$i18n.t('Value')}: ${target.value}`;
</script>

<div
	role="button"
	tabindex="0"
	class="w-full text-left rounded-xl border px-2.5 py-2 transition {active
		? 'border-sky-500/80 bg-sky-100/70 dark:bg-sky-900/40 shadow-sm'
		: 'border-sky-100/80 dark:border-sky-900/50 bg-white/65 dark:bg-slate-950/45 hover:bg-sky-50/45 dark:hover:bg-sky-900/20'}"
	on:click={() => {
		dispatch('select', target.id);
	}}
	on:keydown={(event) => {
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			dispatch('select', target.id);
		}
	}}
>
	<div class="flex items-start justify-between gap-2">
		<div class="min-w-0">
			<div class="text-sm font-medium line-clamp-1">{target.name}</div>
			<div class="mt-0.5 text-[11px] text-gray-600 dark:text-gray-300 line-clamp-1">
				{target.type}
			</div>
		</div>

		<div
			class="text-[10px] px-1.5 py-0.5 rounded-full font-medium shrink-0 whitespace-nowrap leading-none {getTargetStatusClass(
				target.status
			)}"
		>
			{target.status}
		</div>
	</div>

	<div class="mt-1 text-[11px] text-gray-500 dark:text-gray-400 line-clamp-1">{secondaryText}</div>

	<div class="mt-2 flex items-center gap-1.5">
		{#if target.status === 'Active' || target.status === 'Paused'}
			<button
				class="text-[10px] px-2 py-1 rounded-lg bg-slate-100/90 hover:bg-slate-200/90 dark:bg-slate-800/80 dark:hover:bg-slate-700/80 transition"
				on:click|stopPropagation={() => {
					dispatch('toggle', target.id);
				}}
			>
				{target.status === 'Paused' ? $i18n.t('Resume') : $i18n.t('Pause')}
			</button>
		{/if}

		<button
			class="text-[10px] px-2 py-1 rounded-lg bg-sky-600 text-white hover:bg-sky-500 dark:bg-sky-500 dark:hover:bg-sky-400 transition"
			on:click|stopPropagation={() => {
				dispatch('queue', target.id);
			}}
		>
			{$i18n.t('Queue Scan')}
		</button>
	</div>
</div>
