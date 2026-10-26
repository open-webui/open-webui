<script context="module" lang="ts">
	let closeActiveHoverPreview: (() => void) | null = null;
</script>

<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { LinkPreview } from 'bits-ui';
	import { mobile, settings } from '$lib/stores';
	import { getContext, tick, onDestroy } from 'svelte';
	import { copyToClipboard, formatFileSize } from '$lib/utils';
	import { listFiles, type FileEntry } from '$lib/apis/terminal';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import FileTypeIcon from './FileTypeIcon.svelte';
	import Icon from './Icon.svelte';
	import FolderOpen from '$lib/components/icons/FolderOpen.svelte';

	export let dragType = 'application/x-terminal-file-move';
	export let variant: 'terminal' | 'workspace' = 'terminal';
	export let viewMode: 'grid' | 'list' = 'list';
	const i18n: any = getContext('i18n');

	export let entry: FileEntry;
	export let currentPath: string;
	export let fullPath: string | null = null;
	export let depth = 0;
	export let rowIndex = 0;
	export let expanded = false;
	export let loadingChildren = false;
	export let folderContentsVersion = 0;
	export let terminalUrl: string = '';
	export let terminalKey: string = '';
	export let terminalSessionId: string | undefined = undefined;

	export let onOpen: (entry: FileEntry) => void = () => {};
	export let onNewFolder: ((path: string) => void) | undefined = undefined;
	export let onNewFile: ((path: string) => void) | undefined = undefined;
	export let onSelectForComparison: (() => void) | undefined = undefined;
	export let onCompareWithSelected: (() => void) | undefined = undefined;
	export let comparisonPath: string | null = null;
	export let onDownload: (path: string) => void = () => {};
	export let onDelete: (path: string, name: string) => void = () => {};
	export let onMove: (sources: string[], destFolder: string) => void | Promise<void> = () => {};
	export let onRename: (oldPath: string, newName: string) => void = () => {};

	// ── Selection ─────────────────────────────────────────────────────────
	export let selected: boolean = false;
	export let active = false;
	export let selectionMode: boolean = false;
	export let selectedPaths: Set<string> = new Set();
	export let onSelect: (
		entry: FileEntry,
		event: MouseEvent,
		path: string,
		index: number
	) => void = () => {};
	export let onLongPress: () => void = () => {};
	export let onToggleExpand: (path: string) => void = () => {};
	export let showDate: boolean = false;
	export let showHidden: boolean = false;
	export let parentWritable = true;

	$: entryPath =
		fullPath ??
		(entry.type === 'directory' ? `${currentPath}${entry.name}/` : `${currentPath}${entry.name}`);
	$: folderCard = viewMode === 'grid' && entry.type === 'directory';
	$: directoryPath = entryPath.endsWith('/') ? entryPath : `${entryPath}/`;
	$: writable = entry.writable !== false;
	$: canMutate = parentWritable && writable;
	$: menuItemClass =
		variant === 'workspace'
			? 'select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-xs hover:text-gray-900 dark:hover:text-gray-100'
			: 'select-none flex h-7 w-full items-center gap-2 rounded-lg px-2 text-xs hover:bg-gray-50/40 dark:hover:bg-white/4 transition';
	$: rowIndent = `${8 + depth * 16}px`;

	const formatRelativeTime = (epoch: number): string => {
		const diff = Math.floor(Date.now() / 1000) - epoch;
		if (diff < 60) return 'just now';
		if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
		if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
		if (diff < 2592000) return `${Math.floor(diff / 86400)}d ago`;
		if (diff < 31536000) return `${Math.floor(diff / 2592000)}mo ago`;
		return `${Math.floor(diff / 31536000)}y ago`;
	};

	let dragOverFolder = false;
	let expandTimer: ReturnType<typeof setTimeout> | null = null;
	let menuOpen = false;
	let openPreview = false;
	let dragging = false;
	const closeHoverPreview = () => (openPreview = false);
	$: hoverDisabled =
		entry.type !== 'file' ||
		!terminalUrl ||
		$mobile ||
		renaming ||
		menuOpen ||
		dragging ||
		selectionMode;
	$: if (hoverDisabled) openPreview = false;
	$: if (openPreview && closeActiveHoverPreview !== closeHoverPreview) {
		closeActiveHoverPreview?.();
		closeActiveHoverPreview = closeHoverPreview;
	}

	const clearExpandTimer = () => {
		if (!expandTimer) return;
		clearTimeout(expandTimer);
		expandTimer = null;
	};

	let folderItemCount: number | null = null;

	$: folderCountLabel =
		folderItemCount === null
			? '—'
			: folderItemCount === 1
				? $i18n.t('1 item')
				: $i18n.t('{{count}} items', { count: folderItemCount });
	const observeFolderContents = (node: Element) => {
		folderItemCount = null;
		if (!terminalUrl) return;
		let disposed = false;
		const url = terminalUrl;
		const key = terminalKey;
		const session = terminalSessionId;
		const path = directoryPath;
		const observer = new IntersectionObserver((observations) => {
			if (!observations.some((observation) => observation.isIntersecting)) return;
			observer.disconnect();
			// Only inspect visible folders; failed reads leave their contents unknown.
			void listFiles(url, key, path, session).then((result) => {
				if (!disposed && result)
					folderItemCount = result.entries.filter(
						(item) => showHidden || !item.name.startsWith('.')
					).length;
			});
		});
		observer.observe(node);
		return {
			destroy() {
				disposed = true;
				observer.disconnect();
			}
		};
	};

	// ── Rename state ─────────────────────────────────────────────────────
	let renaming = false;
	let renameValue = '';
	let renameInput: HTMLInputElement;

	const startRename = async () => {
		if (!canMutate) return;
		renameValue = entry.name;
		renaming = true;
		await tick();
		renameInput?.focus();
		if (entry.type === 'file') {
			const dotIdx = entry.name.lastIndexOf('.');
			renameInput?.setSelectionRange(0, dotIdx > 0 ? dotIdx : entry.name.length);
		} else {
			renameInput?.select();
		}
	};

	const submitRename = () => {
		const newName = renameValue.trim();
		renaming = false;
		if (!newName || newName === entry.name) return;
		onRename(entryPath.replace(/\/$/, ''), newName);
	};

	const cancelRename = () => {
		renaming = false;
		renameValue = '';
	};

	// ── Long-press for touch selection ───────────────────────────────────
	let longPressTimer: ReturnType<typeof setTimeout> | null = null;
	let didLongPress = false;

	const onPointerDown = (e: PointerEvent) => {
		if (e.pointerType !== 'touch') return;
		didLongPress = false;
		longPressTimer = setTimeout(() => {
			didLongPress = true;
			onLongPress();
			onSelect(entry, e as any, entryPath, rowIndex);
		}, 500);
	};

	const onPointerUp = () => {
		if (longPressTimer) {
			clearTimeout(longPressTimer);
			longPressTimer = null;
		}
	};

	const onPointerCancel = () => {
		if (longPressTimer) {
			clearTimeout(longPressTimer);
			longPressTimer = null;
		}
	};

	onDestroy(() => {
		if (closeActiveHoverPreview === closeHoverPreview) closeActiveHoverPreview = null;
		if (longPressTimer) clearTimeout(longPressTimer);
		clearExpandTimer();
	});

	// ── Click handler ────────────────────────────────────────────────────
	const handleClick = (e: MouseEvent) => {
		openPreview = false;
		if (renaming) return;
		if (didLongPress) {
			didLongPress = false;
			return;
		}

		// Modifier click → toggle/range select
		if (e.metaKey || e.ctrlKey || e.shiftKey) {
			e.preventDefault();
			onSelect(entry, e, entryPath, rowIndex);
			return;
		}

		// In selection mode (touch) → toggle select
		if (selectionMode) {
			onSelect(entry, e, entryPath, rowIndex);
			return;
		}

		// Normal click → open
		onOpen(entry);
	};
</script>

<li class="group min-w-0 {viewMode === 'grid' ? 'self-start' : ''}" data-file-row>
	<div
		class="w-full flex items-center transition-colors duration-75 {viewMode === 'grid'
			? folderCard
				? 'relative h-17'
				: 'relative h-[3.875rem] rounded-md border border-black/[0.06] bg-gray-50/40 dark:border-white/[0.06] dark:bg-gray-900'
			: ''} {variant === 'workspace' ? 'rounded-xl' : ''}
			{folderCard
			? ''
			: selected || active
				? 'bg-gray-100 dark:bg-white/8'
				: 'hover:bg-gray-50/40 dark:hover:bg-white/4'}
			{dragOverFolder && !folderCard
			? 'bg-gray-100 dark:bg-white/8 ring-1 ring-black/15 dark:ring-white/15 ring-inset'
			: ''}"
		role="presentation"
		on:dragover={(e) => {
			if (entry.type !== 'directory') return;
			if (!writable) return;
			if (!e.dataTransfer?.types.includes(dragType)) return;
			e.preventDefault();
			e.stopPropagation();
			dragOverFolder = true;
			if (viewMode === 'list' && !expanded && !expandTimer) {
				expandTimer = setTimeout(() => {
					onToggleExpand(directoryPath);
					expandTimer = null;
				}, 600);
			}
		}}
		on:dragleave={(e) => {
			if (entry.type !== 'directory') return;
			e.stopPropagation();
			dragOverFolder = false;
			clearExpandTimer();
		}}
		on:drop={async (e) => {
			if (entry.type !== 'directory') return;
			if (!writable) return;
			const raw = e.dataTransfer?.getData(dragType);
			if (!raw) return;
			e.preventDefault();
			e.stopPropagation();
			dragOverFolder = false;
			clearExpandTimer();
			try {
				const data = JSON.parse(raw);
				const paths = (data.paths || (data.path ? [data.path] : [])) as string[];
				const destFolder = directoryPath;
				await onMove(
					paths.filter((p) => p + '/' !== destFolder && p !== destFolder),
					destFolder
				);
			} catch {}
		}}
	>
		{#if folderCard}
			<svg
				class="pointer-events-none absolute inset-0 h-full w-full {dragOverFolder
					? 'text-black/25 dark:text-white/25'
					: 'text-black/10 dark:text-white/10'}"
				viewBox="0 0 200 68"
				preserveAspectRatio="none"
				fill="none"
				stroke="currentColor"
				stroke-width="1"
				aria-hidden="true"
			>
				<!-- The back, sloped tab, and front are one folder silhouette. -->
				<path
					d="M1 19V8Q1 1 9 1H54Q58 1 61 4L65 7Q67 9 71 9H191Q199 9 199 15V19"
					vector-effect="non-scaling-stroke"
				/>
				{#if folderItemCount !== null && folderItemCount > 0}
					<path
						d="M7 13V12Q7 9 12 9H188Q193 9 193 12V13Z"
						vector-effect="non-scaling-stroke"
						class="fill-gray-50 text-black/10 dark:fill-[color-mix(in_srgb,var(--color-gray-900),white_4%)] dark:text-white/10"
					/>
				{/if}
				<path
					d="M1 20Q1 13 9 13H191Q199 13 199 20V60Q199 67 191 67H9Q1 67 1 60Z"
					vector-effect="non-scaling-stroke"
					class={selected || active || dragOverFolder
						? 'fill-black/5 dark:fill-white/8'
						: 'fill-transparent group-hover:fill-black/[0.02] dark:group-hover:fill-white/4'}
				/>
			</svg>
		{/if}
		{#if viewMode === 'list' && variant === 'workspace'}
			<span class="shrink-0" style:width={rowIndent}></span>
		{:else if viewMode === 'list' && entry.type === 'directory'}
			<button
				type="button"
				class="mr-1.5 flex w-3 shrink-0 items-center self-stretch justify-center text-gray-400 dark:text-gray-600 hover:text-gray-600 dark:hover:text-gray-400"
				style="margin-left: {rowIndent};"
				on:click|stopPropagation={() => onToggleExpand(directoryPath)}
				aria-label={expanded ? $i18n.t('Collapse') : $i18n.t('Expand')}
			>
				<Icon
					name={expanded ? 'chevron-down' : 'chevron-right'}
					size={12}
					strokeWidth={1.5}
					class={loadingChildren ? 'animate-pulse' : ''}
				/>
			</button>
		{:else if viewMode === 'list'}
			<span class="mr-1.5 w-3 shrink-0 self-stretch" style="margin-left: {rowIndent};"></span>
		{/if}

		{#if selectionMode || selected}
			<button
				type="button"
				role="checkbox"
				aria-checked={selected}
				aria-label={$i18n.t('Select {{name}}', { name: entry.name })}
				class="mr-2 flex size-3.5 shrink-0 items-center justify-center rounded border transition-colors {selected
					? 'bg-gray-900 border-gray-900 text-white dark:bg-gray-200 dark:border-gray-200 dark:text-gray-900'
					: 'border-gray-300 dark:border-gray-600'} {viewMode === 'grid'
					? 'absolute bottom-[0.3125rem] left-1.5 z-10'
					: ''}"
				on:click|stopPropagation={(event) => onSelect(entry, event, entryPath, rowIndex)}
			>
				{#if selected}<Icon name="check" size={10} strokeWidth={2} />{/if}
			</button>
		{/if}

		<LinkPreview.Root
			openDelay={300}
			closeDelay={0}
			disabled={hoverDisabled}
			bind:open={openPreview}
		>
			<LinkPreview.Trigger>
				{#snippet child({ props })}
					<button
						{...props}
						type="button"
						class="flex min-w-0 flex-1 items-center {viewMode === 'grid'
							? folderCard
								? 'h-17 flex-col !items-start justify-start gap-0.5 px-1.5 pt-4 pb-1.5 text-left'
								: 'h-15 flex-col !items-start justify-start gap-0.5 p-1.5 text-left'
							: 'gap-1.5 py-1.5 pr-2 text-left'}"
						title={hoverDisabled ? entry.name : undefined}
						draggable={canMutate}
						on:dragend={() => (dragging = false)}
						on:dragstart={(e) => {
							openPreview = false;
							if (!canMutate) {
								e.preventDefault();
								return;
							}
							dragging = true;
							const filePath = entryPath.replace(/\/$/, '');
							// If dragging a selected item, drag all selected
							if (selected && selectedPaths.size > 1) {
								e.dataTransfer?.setData(dragType, JSON.stringify({ paths: [...selectedPaths] }));
								// Custom drag ghost showing count
								const ghost = document.createElement('div');
								ghost.style.cssText =
									'position:fixed;top:-1000px;left:-1000px;display:flex;align-items:center;gap:0.375rem;padding:0.25rem 0.625rem;border-radius:0.5rem;background:#374151;color:#fff;font-size:0.75rem;white-space:nowrap;pointer-events:none;';
								ghost.textContent = `${selectedPaths.size} items`;
								document.body.appendChild(ghost);
								e.dataTransfer?.setDragImage(ghost, 0, 0);
								requestAnimationFrame(() => ghost.remove());
							} else {
								e.dataTransfer?.setData(
									dragType,
									JSON.stringify({
										path: entry.type === 'directory' ? directoryPath : filePath,
										name: entry.name
									})
								);
							}
							if (entry.type === 'file' && terminalUrl) {
								e.dataTransfer?.setData(
									'application/x-terminal-file',
									JSON.stringify({
										path: filePath,
										name: entry.name,
										url: terminalUrl,
										key: terminalKey
									})
								);
							}
						}}
						on:pointerdown={onPointerDown}
						on:pointerup={onPointerUp}
						on:pointercancel={onPointerCancel}
						aria-expanded={variant === 'workspace' && entry.type === 'directory'
							? expanded
							: props['aria-expanded']}
						on:click={handleClick}
						on:dblclick|preventDefault|stopPropagation={() => {
							startRename();
						}}
					>
						{#if variant === 'workspace'}
							{#if entry.type === 'directory'}
								<Icon
									name={expanded ? 'chevron-down' : 'chevron-right'}
									size={12}
									strokeWidth={1.5}
								/>
							{:else}<span class="w-3 shrink-0"></span>{/if}
						{/if}
						{#if viewMode === 'list'}
							<FileTypeIcon name={entry.name} type={entry.type} size={14} />
						{/if}
						{#if renaming}
							<!-- svelte-ignore a11y-click-events-have-key-events -->
							<input
								bind:this={renameInput}
								bind:value={renameValue}
								class="flex-1 text-xs bg-transparent outline-hidden text-gray-800 dark:text-gray-200 min-w-0 {variant ===
								'workspace'
									? 'h-4 p-0 leading-4'
									: 'py-0.5'} {viewMode === 'grid' ? 'w-full pr-6' : ''}"
								on:keydown={(e) => {
									if (e.key === 'Enter') {
										e.preventDefault();
										submitRename();
									}
									if (e.key === 'Escape') {
										e.preventDefault();
										cancelRename();
									}
								}}
								on:blur={submitRename}
								on:click|stopPropagation
							/>
						{:else}
							<span
								class="text-xs text-gray-800 dark:text-gray-200 {viewMode === 'grid'
									? 'w-full shrink-0 line-clamp-2 break-words pr-5'
									: 'flex-1 truncate'}"
							>
								{entry.name}
							</span>
						{/if}
						{#if !writable && !renaming && variant !== 'workspace' && viewMode !== 'grid'}
							<span class="text-[0.625rem] text-gray-400 shrink-0">{$i18n.t('Read-only')}</span>
						{/if}
						{#if viewMode === 'grid' && !renaming}
							<span
								class="mt-auto flex w-full min-w-0 shrink-0 items-center gap-1 text-[0.5625rem] leading-3 text-gray-500 dark:text-gray-400 {selectionMode ||
								selected
									? 'pl-5'
									: ''}"
							>
								{#if entry.type === 'directory'}
									{#key folderContentsVersion}
										<span use:observeFolderContents class="min-w-0 flex-1 truncate"
											>{folderCountLabel}</span
										>
									{/key}
								{:else}
									<span class="min-w-0 truncate rounded bg-black/5 px-1 uppercase dark:bg-white/5">
										{entry.name.includes('.')
											? entry.name.split('.').pop() || $i18n.t('File')
											: $i18n.t('File')}
									</span>
									{#if entry.size !== undefined}
										<span class="ml-auto shrink-0">{formatFileSize(entry.size)}</span>
									{/if}
								{/if}
								{#if !writable && variant !== 'workspace'}
									<span title={$i18n.t('Read-only')} aria-label={$i18n.t('Read-only')}
										><Icon name="lock" size={10} strokeWidth={1.5} /></span
									>
								{/if}
							</span>
						{:else if entry.type === 'file' && entry.size !== undefined && !renaming}
							{#if showDate && entry.modified}
								<span class="text-[0.625rem] text-gray-400 shrink-0"
									>{formatRelativeTime(entry.modified)}</span
								>
							{/if}
							<span class="text-xs text-gray-400 shrink-0">{formatFileSize(entry.size)}</span>
						{:else if entry.type === 'directory' && !renaming}
							{#if showDate && entry.modified}
								<span class="text-[0.625rem] text-gray-400 shrink-0"
									>{formatRelativeTime(entry.modified)}</span
								>
							{/if}
							{#if terminalUrl}
								{#key folderContentsVersion}
									<span use:observeFolderContents class="text-xs text-gray-400 shrink-0"
										>{folderCountLabel}</span
									>
								{/key}
							{/if}
						{/if}
					</button>
				{/snippet}
			</LinkPreview.Trigger>
			{#if openPreview}
				{#key JSON.stringify( [terminalUrl, terminalKey, terminalSessionId, entryPath, entry.modified, entry.size] )}
					{#await import('./FileHoverPreview.svelte') then { default: FileHoverPreview }}
						<FileHoverPreview
							{entry}
							path={entryPath}
							{terminalUrl}
							{terminalKey}
							sessionId={terminalSessionId}
						/>
					{/await}
				{/key}
			{/if}
		</LinkPreview.Root>

		<Dropdown bind:show={menuOpen} align="end" sideOffset={4}>
			<button
				type="button"
				class="shrink-0 flex {($settings?.highContrastMode ?? false)
					? 'h-6 w-6'
					: 'h-5 w-5'} items-center justify-center mr-1 rounded transition
					text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-400
					hover:bg-gray-50/40 dark:hover:bg-white/4 {viewMode === 'grid'
					? folderCard
						? 'absolute right-0 top-4'
						: 'absolute right-0 top-1'
					: ''}"
				aria-label={$i18n.t('More')}
			>
				<Icon name="three-dots" size={12} strokeWidth={1.4} />
			</button>

			<div slot="content">
				<DropdownMenu className="min-w-[9.375rem] z-[9999999]">
					{#if entry.type === 'directory' && onNewFolder}
						<button
							type="button"
							class="{menuItemClass} disabled:opacity-40 disabled:hover:bg-transparent"
							disabled={!writable}
							on:click|stopPropagation={() => {
								if (!writable) return;
								menuOpen = false;
								onNewFolder?.(directoryPath);
							}}
						>
							<Icon name="folder-plus" size={14} strokeWidth={1.5} />
							<div class="flex items-center">{$i18n.t('New Folder')}</div>
						</button>
					{/if}
					{#if entry.type === 'directory' && onNewFile}
						<button
							type="button"
							class="{menuItemClass} disabled:opacity-40 disabled:hover:bg-transparent"
							disabled={!writable}
							on:click|stopPropagation={() => {
								if (!writable) return;
								menuOpen = false;
								onNewFile?.(directoryPath);
							}}
						>
							<Icon name="file-plus" size={14} strokeWidth={1.5} />
							<div class="flex items-center">{$i18n.t('New File')}</div>
						</button>
					{/if}
					{#if entry.type === 'directory' && (onNewFolder || onNewFile)}
						<div class="my-1 border-t border-gray-100 dark:border-white/10" role="separator"></div>
					{/if}
					{#if variant !== 'workspace' || entry.type !== 'directory'}
						<button
							type="button"
							class={menuItemClass}
							on:click={(e) => {
								e.stopPropagation();
								menuOpen = false;
								onOpen(entry);
							}}
						>
							{#if entry.type === 'directory'}
								<FolderOpen className="size-3.5 shrink-0" />
							{:else}
								<Icon name="eye" size={14} strokeWidth={1.5} />
							{/if}
							<div class="flex items-center">
								{entry.type === 'directory' ? $i18n.t('Open Folder') : $i18n.t('Open')}
							</div>
						</button>
					{/if}
					{#if entry.type === 'file' && onSelectForComparison}
						<button
							type="button"
							class={menuItemClass}
							on:click|stopPropagation={() => {
								menuOpen = false;
								onSelectForComparison?.();
							}}
						>
							<Icon name="page" size={14} strokeWidth={1.5} /><span
								>{$i18n.t('Select for Compare')}</span
							>
						</button>
						{#if onCompareWithSelected}
							<button
								type="button"
								class="{menuItemClass} disabled:opacity-40"
								disabled={comparisonPath === entryPath}
								on:click|stopPropagation={() => {
									menuOpen = false;
									onCompareWithSelected?.();
								}}
							>
								<Icon name="split-horizontal" size={14} strokeWidth={1.5} /><span
									>{$i18n.t('Compare with Selected')}</span
								>
							</button>
						{/if}
					{/if}
					{#if entry.type === 'directory'}
						{#if viewMode === 'list'}
							<button
								type="button"
								class={menuItemClass}
								on:click={(e) => {
									e.stopPropagation();
									menuOpen = false;
									onToggleExpand(directoryPath);
								}}
							>
								<Icon
									name={expanded ? 'chevron-down' : 'chevron-right'}
									size={14}
									strokeWidth={1.5}
								/>
								<div class="flex items-center">
									{expanded ? $i18n.t('Collapse') : $i18n.t('Expand')}
								</div>
							</button>
						{/if}
					{:else}
						<button
							type="button"
							class={menuItemClass}
							on:click={(e) => {
								e.stopPropagation();
								menuOpen = false;
								onDownload(entryPath);
							}}
						>
							<Icon name="download-tray" size={14} strokeWidth={1.5} />
							<div class="flex items-center">{$i18n.t('Download')}</div>
						</button>
					{/if}

					<button
						type="button"
						class={menuItemClass}
						on:click={async (e) => {
							e.stopPropagation();
							menuOpen = false;
							if (await copyToClipboard(entryPath)) {
								toast.success($i18n.t('Path copied'));
							}
						}}
					>
						<Icon name="copy" size={14} strokeWidth={1.5} />
						<div class="flex items-center">{$i18n.t('Copy Path')}</div>
					</button>

					<button
						type="button"
						class="{menuItemClass} disabled:opacity-40 disabled:hover:bg-transparent"
						disabled={!canMutate}
						on:click={(e) => {
							e.stopPropagation();
							if (!canMutate) return;
							menuOpen = false;
							startRename();
						}}
					>
						<Icon name="pencil" size={14} strokeWidth={1.5} />
						<div class="flex items-center">{$i18n.t('Rename')}</div>
					</button>

					<button
						type="button"
						class="{menuItemClass} disabled:opacity-40 disabled:hover:bg-transparent"
						disabled={!canMutate}
						on:click={(e) => {
							e.stopPropagation();
							if (!canMutate) return;
							menuOpen = false;
							onDelete(entryPath.replace(/\/$/, ''), entry.name);
						}}
					>
						<Icon name="trash" size={14} strokeWidth={1.5} />
						<div class="flex items-center">{$i18n.t('Delete')}</div>
					</button>
				</DropdownMenu>
			</div>
		</Dropdown>
	</div>
</li>
