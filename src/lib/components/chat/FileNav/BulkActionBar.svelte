<script lang="ts">
	import { getContext } from 'svelte';
	import GarbageBin from '../../icons/GarbageBin.svelte';
	import Tooltip from '../../common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let count: number = 0;
	export let hasFiles: boolean = false;

	export let onDelete: () => void = () => {};
	export let onDownload: () => void = () => {};
	export let onSelectAll: () => void = () => {};
	export let onClear: () => void = () => {};
</script>

<div class="flex items-center gap-2 px-3 py-1.5 bg-gray-50 dark:bg-gray-800/50 shrink-0">
	<span class="text-xs font-medium text-gray-600 dark:text-gray-400 flex-1 truncate">
		{$i18n.t('{{count}} selected', { count })}
	</span>

	<Tooltip content={$i18n.t('Select All')}>
		<button
			class="p-1 rounded transition text-gray-400 dark:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-600 dark:hover:text-gray-400"
			on:click={onSelectAll}
			aria-label={$i18n.t('Select All')}
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="size-3.5"
			>
				<path
					fill-rule="evenodd"
					d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
					clip-rule="evenodd"
				/>
			</svg>
		</button>
	</Tooltip>

	<Tooltip content={$i18n.t('Download')}>
		<button
			class="p-1 rounded transition text-gray-400 dark:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-600 dark:hover:text-gray-400"
			on:click={onDownload}
			aria-label={$i18n.t('Download')}
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="size-3.5"
			>
				<path
					d="M10.75 2.75a.75.75 0 0 0-1.5 0v8.614L6.295 8.235a.75.75 0 1 0-1.09 1.03l4.25 4.5a.75.75 0 0 0 1.09 0l4.25-4.5a.75.75 0 0 0-1.09-1.03l-2.955 3.129V2.75Z"
				/>
				<path
					d="M3.5 12.75a.75.75 0 0 0-1.5 0v2.5A2.75 2.75 0 0 0 4.75 18h10.5A2.75 2.75 0 0 0 18 15.25v-2.5a.75.75 0 0 0-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5Z"
				/>
			</svg>
		</button>
	</Tooltip>

	<Tooltip content={$i18n.t('Delete')}>
		<button
			class="p-1 rounded transition text-gray-400 dark:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-600 dark:hover:text-gray-400"
			on:click={onDelete}
			aria-label={$i18n.t('Delete')}
		>
			<GarbageBin className="size-3.5" />
		</button>
	</Tooltip>

	<Tooltip content={$i18n.t('Deselect')}>
		<button
			class="p-1 rounded transition text-gray-400 dark:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-600 dark:hover:text-gray-400"
			on:click={onClear}
			aria-label={$i18n.t('Deselect')}
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="size-3.5"
			>
				<path
					d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z"
				/>
			</svg>
		</button>
	</Tooltip>
</div>
