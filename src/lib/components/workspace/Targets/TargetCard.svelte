<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import type { Target } from './types';
	import { getTargetStatusClass } from './status';

	const i18n = getContext<any>('i18n');
	const dispatch = createEventDispatcher<{ run: string; toggle: string; delete: string }>();

	export let target: Target;
</script>

<div
	class="rounded-2xl border border-sky-100/80 dark:border-sky-900/45 bg-white/78 dark:bg-slate-950/58 p-3.5 transition hover:bg-sky-50/35 dark:hover:bg-sky-900/22"
>
	<div class="flex items-start justify-between gap-2">
		<div class="min-w-0">
			<div class="font-medium line-clamp-1">{target.name}</div>
			<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-1">
				{target.description || $i18n.t('No description')}
			</div>
		</div>
		<div
			class="text-[11px] px-2 py-1 rounded-full font-medium {getTargetStatusClass(target.status)}"
		>
			{target.status}
		</div>
	</div>

	<div class="mt-3 grid grid-cols-2 gap-y-2 text-sm">
		<div class="text-gray-500 dark:text-gray-400 text-xs">{$i18n.t('Type')}</div>
		<div class="text-right font-medium">{target.type}</div>

		<div class="text-gray-500 dark:text-gray-400 text-xs">{$i18n.t('Value')}</div>
		<div class="text-right line-clamp-1" title={target.value}>{target.value}</div>

		<div class="text-gray-500 dark:text-gray-400 text-xs">{$i18n.t('Last Scan')}</div>
		<div class="text-right text-xs">{target.lastScan ?? $i18n.t('Never')}</div>
	</div>

	<div class="mt-3 flex items-center justify-end gap-1.5">
		<button
			class="text-xs px-2.5 py-1.5 rounded-xl bg-slate-100/85 hover:bg-slate-200/85 dark:bg-slate-800/70 dark:hover:bg-slate-700/80 transition"
			on:click={() => {
				dispatch('toggle', target.id);
			}}
		>
			{target.status === 'Paused' ? $i18n.t('Resume') : $i18n.t('Pause')}
		</button>
		<button
			class="text-xs px-2.5 py-1.5 rounded-xl bg-sky-600 text-white hover:bg-sky-500 dark:bg-sky-500 dark:hover:bg-sky-400 transition"
			on:click={() => {
				dispatch('run', target.id);
			}}
		>
			{$i18n.t('Queue Scan')}
		</button>
		<button
			class="text-xs px-2.5 py-1.5 rounded-xl bg-rose-50/90 text-rose-700 hover:bg-rose-100/90 dark:bg-rose-900/35 dark:text-rose-300 dark:hover:bg-rose-900/50 transition"
			on:click={() => {
				dispatch('delete', target.id);
			}}
		>
			{$i18n.t('Delete')}
		</button>
	</div>
</div>
