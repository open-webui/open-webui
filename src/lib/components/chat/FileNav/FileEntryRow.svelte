<script lang="ts">
	import { getContext } from 'svelte';
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import type { FileEntry } from '$lib/apis/terminal';
	import Folder from '../../icons/Folder.svelte';
	import EllipsisHorizontal from '../../icons/EllipsisHorizontal.svelte';
	import GarbageBin from '../../icons/GarbageBin.svelte';

	const i18n = getContext('i18n');

	export let entry: FileEntry;
	export let currentPath: string;
	export let terminalUrl: string;
	export let terminalKey: string;

	export let onOpen: (entry: FileEntry) => void = () => {};
	export let onDownload: (path: string) => void = () => {};
	export let onDelete: (path: string, name: string) => void = () => {};

	export let formatSize: (bytes?: number) => string = () => '';
</script>

<li class="group">
	<div
		class="w-full flex items-center hover:bg-gray-50 dark:hover:bg-gray-800 transition"
	>
		<button
			class="flex-1 flex items-center gap-2 px-3 py-1.5 text-left min-w-0"
			draggable={entry.type === 'file'}
			on:dragstart={(e) => {
				if (entry.type !== 'file') return;
				e.dataTransfer?.setData(
					'application/x-terminal-file',
					JSON.stringify({
						path: `${currentPath}${entry.name}`,
						name: entry.name,
						url: terminalUrl,
						key: terminalKey
					})
				);
			}}
			on:click={() => onOpen(entry)}
		>
			{#if entry.type === 'directory'}
				<Folder className="size-4 shrink-0 text-blue-400 dark:text-blue-300" />
			{:else}
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.5"
					class="size-4 shrink-0 text-gray-400"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
					/>
				</svg>
			{/if}
			<span class="flex-1 text-xs text-gray-800 dark:text-gray-200 truncate">
				{entry.name}
			</span>
			{#if entry.type === 'file' && entry.size !== undefined}
				<span class="text-xs text-gray-400 shrink-0">{formatSize(entry.size)}</span>
			{/if}
		</button>

		<DropdownMenu.Root>
			<DropdownMenu.Trigger
				class="shrink-0 p-0.5 mr-1 rounded-lg transition
					text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-400
					hover:bg-gray-100 dark:hover:bg-gray-800"
				on:click={(e) => e.stopPropagation()}
				aria-label={$i18n.t('More')}
			>
				<EllipsisHorizontal className="size-3.5" />
			</DropdownMenu.Trigger>

			<DropdownMenu.Content
				strategy="fixed"
				class="w-full max-w-[150px] rounded-2xl p-1 z-[9999999] bg-white dark:bg-gray-850 dark:text-white shadow-lg border border-gray-100 dark:border-gray-800"
				sideOffset={4}
				side="bottom"
				align="end"
				transition={flyAndScale}
			>
				{#if entry.type !== 'directory'}
					<DropdownMenu.Item
						type="button"
						class="select-none flex rounded-xl py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition items-center gap-2 text-sm"
						on:click={(e) => {
							e.stopPropagation();
							onDownload(`${currentPath}${entry.name}`);
						}}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="size-4"
						>
							<path
								d="M10.75 2.75a.75.75 0 0 0-1.5 0v8.614L6.295 8.235a.75.75 0 1 0-1.09 1.03l4.25 4.5a.75.75 0 0 0 1.09 0l4.25-4.5a.75.75 0 0 0-1.09-1.03l-2.955 3.129V2.75Z"
							/>
							<path
								d="M3.5 12.75a.75.75 0 0 0-1.5 0v2.5A2.75 2.75 0 0 0 4.75 18h10.5A2.75 2.75 0 0 0 18 15.25v-2.5a.75.75 0 0 0-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5Z"
							/>
						</svg>
						<div class="flex items-center">{$i18n.t('Download')}</div>
					</DropdownMenu.Item>
				{/if}

				<DropdownMenu.Item
					type="button"
					class="select-none flex rounded-xl py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition items-center gap-2 text-sm"
					on:click={(e) => {
						e.stopPropagation();
						onDelete(`${currentPath}${entry.name}`, entry.name);
					}}
				>
					<GarbageBin className="size-4" />
					<div class="flex items-center">{$i18n.t('Delete')}</div>
				</DropdownMenu.Item>
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</div>
</li>
