<script lang="ts">
	import { getContext } from 'svelte';
	import type { Readable } from 'svelte/store';
	import type { i18n as I18n } from 'i18next';
	import Tooltip from '../../common/Tooltip.svelte';
	import Icon from './Icon.svelte';

	const i18n = getContext<Readable<I18n>>('i18n');

	export let count: number = 0;
	export let canDelete = true;
	export let canCompare = false;
	export let onCompare: () => void = () => {};

	export let onDelete: () => void = () => {};
	export let onDownload: () => void = () => {};
	export let onSelectAll: () => void = () => {};
	export let onClear: () => void = () => {};
</script>

<div
	class="flex h-8 items-center gap-2 px-2 bg-gray-50 dark:bg-white/[0.03] shrink-0 border-t border-gray-50 dark:border-gray-850/30"
>
	<span class="text-[0.6875rem] font-normal text-gray-600 dark:text-gray-400 flex-1 truncate">
		{$i18n.t('{{count}} selected', { count })}
	</span>

	<Tooltip content={$i18n.t('Compare')}>
		<button
			class="flex h-5 w-5 items-center justify-center rounded transition-colors duration-100 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-30"
			disabled={!canCompare}
			on:click={onCompare}
			aria-label={$i18n.t('Compare')}
		>
			<Icon name="split-horizontal" size={12} strokeWidth={1.4} />
		</button>
	</Tooltip>

	<Tooltip content={$i18n.t('Select All')}>
		<button
			class="flex h-5 w-5 items-center justify-center rounded transition-colors duration-100 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
			on:click={onSelectAll}
			aria-label={$i18n.t('Select All')}
		>
			<Icon name="check" size={12} strokeWidth={1.6} />
		</button>
	</Tooltip>

	<Tooltip content={$i18n.t('Download')}>
		<button
			class="flex h-5 w-5 items-center justify-center rounded transition-colors duration-100 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
			on:click={onDownload}
			aria-label={$i18n.t('Download')}
		>
			<Icon name="download" size={12} strokeWidth={1.4} />
		</button>
	</Tooltip>

	<Tooltip content={$i18n.t('Delete')}>
		<button
			class="flex h-5 w-5 items-center justify-center rounded transition-colors duration-100 text-gray-400 dark:text-gray-500 hover:text-red-500 disabled:opacity-30 disabled:hover:text-gray-400"
			on:click={onDelete}
			disabled={!canDelete}
			aria-label={$i18n.t('Delete')}
		>
			<Icon name="trash" size={12} strokeWidth={1.4} />
		</button>
	</Tooltip>

	<Tooltip content={$i18n.t('Deselect')}>
		<button
			class="flex h-5 w-5 items-center justify-center rounded transition-colors duration-100 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
			on:click={onClear}
			aria-label={$i18n.t('Deselect')}
		>
			<Icon name="xmark" size={12} strokeWidth={1.5} />
		</button>
	</Tooltip>
</div>
