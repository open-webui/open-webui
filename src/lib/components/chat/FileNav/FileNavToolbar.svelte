<script lang="ts">
	import { getContext, afterUpdate } from 'svelte';
	import Spinner from '../../common/Spinner.svelte';
	import Tooltip from '../../common/Tooltip.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Icon from './Icon.svelte';

	const i18n: any = getContext('i18n');

	export let breadcrumbs: { label: string; path: string }[] = [];
	export let selectedFile: string | null = null;
	export let loading = false;
	export let writable = true;

	export let onNavigate: (path: string) => void = () => {};
	export let onRefresh: () => void = () => {};
	export let onNewFolder: () => void = () => {};
	export let onNewFile: () => void = () => {};
	export let onUploadFiles: (files: File[]) => void = () => {};
	export let onDownloadDir: () => void = () => {};
	export let onMove: (source: string, destFolder: string) => void = () => {};

	// Sort controls
	export let sortBy: 'name' | 'date' = 'name';
	export let sortAsc: boolean = true;
	export let onSort: (mode: 'name' | 'date') => void = () => {};

	// Back / forward navigation
	export let canGoBack = false;
	export let canGoForward = false;
	export let onGoBack: () => void = () => {};
	export let onGoForward: () => void = () => {};

	let dragOverCrumb: number | null = null;

	let uploadInput: HTMLInputElement;
	let breadcrumbEl: HTMLDivElement;

	const showSeparator = (index: number) =>
		index > 0 && (breadcrumbs[0]?.label !== '/' || index > 1);

	// Scroll breadcrumb to the end after every DOM update
	afterUpdate(() => {
		if (breadcrumbEl) breadcrumbEl.scrollLeft = breadcrumbEl.scrollWidth;
	});
</script>

<div class="flex items-center px-2 pb-1.5 shrink-0 gap-1">
	<!-- Back -->
	<Tooltip content={$i18n.t('Back')}>
		<button
			class="shrink-0 p-1 rounded transition {canGoBack
				? 'text-gray-400 dark:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-600 dark:hover:text-gray-400'
				: 'text-gray-200 dark:text-gray-700 cursor-default'}"
			on:click={onGoBack}
			disabled={!canGoBack}
			aria-label={$i18n.t('Back')}
		>
			<Icon name="chevron-left" size={14} strokeWidth={1.5} />
		</button>
	</Tooltip>

	<!-- Forward -->
	<Tooltip content={$i18n.t('Forward')}>
		<button
			class="shrink-0 p-1 rounded transition {canGoForward
				? 'text-gray-400 dark:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-600 dark:hover:text-gray-400'
				: 'text-gray-200 dark:text-gray-700 cursor-default'}"
			on:click={onGoForward}
			disabled={!canGoForward}
			aria-label={$i18n.t('Forward')}
		>
			<Icon name="chevron-right" size={14} strokeWidth={1.5} />
		</button>
	</Tooltip>

	<div
		bind:this={breadcrumbEl}
		class="flex items-center flex-1 min-w-0 overflow-x-auto scrollbar-none"
	>
		{#each breadcrumbs as crumb, i}
			{#if showSeparator(i)}
				<span class="text-gray-300 dark:text-gray-600 text-xs shrink-0 select-none mx-0.5">/</span>
			{/if}
			<button
				class="text-xs shrink-0 px-1 py-0.5 rounded transition
					{!selectedFile && i === breadcrumbs.length - 1
					? 'text-gray-700 dark:text-gray-300'
					: 'text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400'}
					{dragOverCrumb === i
					? 'bg-blue-50 dark:bg-blue-900/30 ring-1 ring-blue-400 dark:ring-blue-500'
					: ''}"
				on:click={() => onNavigate(crumb.path)}
				on:dragover={(e) => {
					if (!writable) return;
					if (!e.dataTransfer?.types.includes('application/x-terminal-file-move')) return;
					e.preventDefault();
					e.stopPropagation();
					dragOverCrumb = i;
				}}
				on:dragleave={() => {
					if (dragOverCrumb === i) dragOverCrumb = null;
				}}
				on:drop={(e) => {
					if (!writable) return;
					const raw = e.dataTransfer?.getData('application/x-terminal-file-move');
					if (!raw) return;
					e.preventDefault();
					e.stopPropagation();
					dragOverCrumb = null;
					try {
						const data = JSON.parse(raw);
						const paths = data.paths || (data.path ? [data.path] : []);
						for (const p of paths) onMove(p, crumb.path);
					} catch {}
				}}
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
	{#if !writable}
		<span class="text-[0.625rem] text-gray-400 dark:text-gray-500 shrink-0"> Read-only </span>
	{/if}

	<Tooltip content={$i18n.t('Refresh')}>
		<button
			class="shrink-0 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400"
			on:click={onRefresh}
			aria-label={$i18n.t('Refresh')}
		>
			<Icon name="refresh" size={14} strokeWidth={1.4} class={loading ? 'animate-spin' : ''} />
		</button>
	</Tooltip>

	{#if !selectedFile}
		<Dropdown align="end" sideOffset={4}>
			<Tooltip content={$i18n.t('Sort')}>
				<button
					class="shrink-0 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400"
					aria-label={$i18n.t('Sort')}
				>
					<Icon name="sort" size={14} strokeWidth={1.4} />
				</button>
			</Tooltip>

			<div slot="content">
				<DropdownMenu className="min-w-[9.375rem] z-[9999999]">
					<button
						type="button"
						class="select-none flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[0.8125rem] hover:bg-gray-50/40 dark:hover:bg-gray-800/40 transition"
						on:click={() => onSort('name')}
					>
						<span class="flex-1 text-left">{$i18n.t('Name')}</span>
						{#if sortBy === 'name'}
							<Icon
								name="chevron-up"
								size={12}
								strokeWidth={1.5}
								class="text-gray-500 dark:text-gray-400 transition-transform {sortAsc
									? ''
									: 'rotate-180'}"
							/>
						{/if}
					</button>
					<button
						type="button"
						class="select-none flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[0.8125rem] hover:bg-gray-50/40 dark:hover:bg-gray-800/40 transition"
						on:click={() => onSort('date')}
					>
						<span class="flex-1 text-left">{$i18n.t('Date Modified')}</span>
						{#if sortBy === 'date'}
							<Icon
								name="chevron-up"
								size={12}
								strokeWidth={1.5}
								class="text-gray-500 dark:text-gray-400 transition-transform {sortAsc
									? ''
									: 'rotate-180'}"
							/>
						{/if}
					</button>
				</DropdownMenu>
			</div>
		</Dropdown>
		<Tooltip content={$i18n.t('New Folder')}>
			<button
				class="shrink-0 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400 disabled:opacity-30 disabled:hover:bg-transparent"
				on:click={onNewFolder}
				disabled={!writable}
				aria-label={$i18n.t('New Folder')}
			>
				<Icon name="folder" size={14} strokeWidth={1.4} />
			</button>
		</Tooltip>
		<Tooltip content={$i18n.t('New File')}>
			<button
				class="shrink-0 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400 disabled:opacity-30 disabled:hover:bg-transparent"
				on:click={onNewFile}
				disabled={!writable}
				aria-label={$i18n.t('New File')}
			>
				<Icon name="empty-page" size={14} strokeWidth={1.4} />
			</button>
		</Tooltip>
		<Tooltip content={$i18n.t('Download')}>
			<button
				class="shrink-0 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400"
				on:click={onDownloadDir}
				aria-label={$i18n.t('Download')}
			>
				<Icon name="download" size={14} strokeWidth={1.4} />
			</button>
		</Tooltip>
		<Tooltip content={$i18n.t('Upload')}>
			<button
				class="shrink-0 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400 disabled:opacity-30 disabled:hover:bg-transparent"
				on:click={() => uploadInput?.click()}
				disabled={!writable}
				aria-label={$i18n.t('Upload')}
			>
				<Icon name="upload" size={14} strokeWidth={1.4} />
			</button>
		</Tooltip>
		<input
			bind:this={uploadInput}
			type="file"
			multiple
			hidden
			on:change={async () => {
				if (!writable || !uploadInput?.files?.length) return;
				onUploadFiles(Array.from(uploadInput.files));
				uploadInput.value = '';
			}}
		/>
	{:else}
		<slot />
	{/if}
</div>
