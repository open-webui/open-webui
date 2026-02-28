<script lang="ts">
	import { getContext, afterUpdate } from 'svelte';
	import { tick } from 'svelte';
	import Folder from '../../icons/Folder.svelte';
	import NewFolderAlt from '../../icons/NewFolderAlt.svelte';
	import Spinner from '../../common/Spinner.svelte';
	import Tooltip from '../../common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let breadcrumbs: { label: string; path: string }[] = [];
	export let selectedFile: string | null = null;
	export let loading = false;

	export let onNavigate: (path: string) => void = () => {};
	export let onRefresh: () => void = () => {};
	export let onNewFolder: () => void = () => {};
	export let onUploadFiles: (files: File[]) => void = () => {};

	let uploadInput: HTMLInputElement;
	let breadcrumbEl: HTMLDivElement;

	// Scroll breadcrumb to the end after every DOM update
	afterUpdate(() => {
		if (breadcrumbEl) breadcrumbEl.scrollLeft = breadcrumbEl.scrollWidth;
	});
</script>

<div class="flex items-center px-2 pb-1.5 shrink-0 gap-1">
	<div
		bind:this={breadcrumbEl}
		class="flex items-center flex-1 min-w-0 overflow-x-auto scrollbar-none"
	>
		{#each breadcrumbs as crumb, i}
			{#if i > 1}
				<span class="text-gray-300 dark:text-gray-600 text-xs shrink-0 select-none mx-0.5">/</span>
			{/if}
			<button
				class="text-xs shrink-0 px-1 py-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition
					{!selectedFile && i === breadcrumbs.length - 1
					? 'text-gray-700 dark:text-gray-300'
					: 'text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400'}"
				on:click={() => onNavigate(crumb.path)}
			>
				{crumb.label}
			</button>
		{/each}
		{#if selectedFile}
			<span class="text-gray-300 dark:text-gray-600 text-xs shrink-0 select-none mx-0.5">/</span>
			<span class="text-xs shrink-0 px-1.5 py-0.5 text-gray-700 dark:text-gray-300">
				{selectedFile.split('/').pop()}
			</span>
		{/if}
	</div>

	{#if !selectedFile}
		<Tooltip content={$i18n.t('Refresh')}>
			<button
				class="shrink-0 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400"
				on:click={onRefresh}
				aria-label={$i18n.t('Refresh')}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="size-3.5 {loading ? 'animate-spin' : ''}"
				>
					<path
						fill-rule="evenodd"
						d="M15.312 11.424a5.5 5.5 0 0 1-9.201 2.466l-.312-.311h2.451a.75.75 0 0 0 0-1.5H4.5a.75.75 0 0 0-.75.75v3.75a.75.75 0 0 0 1.5 0v-2.127l.13.13a7 7 0 0 0 11.712-3.138.75.75 0 0 0-1.449-.39Zm-10.624-2.85a5.5 5.5 0 0 1 9.201-2.465l.312.31H11.75a.75.75 0 0 0 0 1.5h3.75a.75.75 0 0 0 .75-.75V3.42a.75.75 0 0 0-1.5 0v2.126l-.13-.129A7 7 0 0 0 3.239 8.555a.75.75 0 0 0 1.449.39Z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
		</Tooltip>
		<Tooltip content={$i18n.t('New Folder')}>
			<button
				class="shrink-0 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400"
				on:click={onNewFolder}
				aria-label={$i18n.t('New Folder')}
			>
				<NewFolderAlt className="size-3.5" />
			</button>
		</Tooltip>
		<Tooltip content={$i18n.t('Upload')}>
			<button
				class="shrink-0 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400"
				on:click={() => uploadInput?.click()}
				aria-label={$i18n.t('Upload')}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.5"
					class="size-3.5"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5"
					/>
				</svg>
			</button>
		</Tooltip>
		<input
			bind:this={uploadInput}
			type="file"
			multiple
			hidden
			on:change={async () => {
				if (!uploadInput?.files?.length) return;
				onUploadFiles(Array.from(uploadInput.files));
				uploadInput.value = '';
			}}
		/>
	{/if}
</div>
