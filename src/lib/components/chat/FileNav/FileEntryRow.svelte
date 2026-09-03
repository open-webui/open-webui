<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, tick, onDestroy } from 'svelte';
	import { copyToClipboard, formatFileSize } from '$lib/utils';
	import type { FileEntry } from '$lib/apis/terminal';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import FileTypeIcon from './FileTypeIcon.svelte';
	import Icon from './Icon.svelte';

	const i18n: any = getContext('i18n');

	export let entry: FileEntry;
	export let currentPath: string;
	export let fullPath: string | null = null;
	export let depth = 0;
	export let rowIndex = 0;
	export let expanded = false;
	export let loadingChildren = false;
	export let terminalUrl: string = '';
	export let terminalKey: string = '';

	export let onOpen: (entry: FileEntry) => void = () => {};
	export let onDownload: (path: string) => void = () => {};
	export let onDelete: (path: string, name: string) => void = () => {};
	export let onMove: (sources: string[], destFolder: string) => void | Promise<void> = () => {};
	export let onRename: (oldPath: string, newName: string) => void = () => {};

	// ── Selection ─────────────────────────────────────────────────────────
	export let selected: boolean = false;
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
	export let parentWritable = true;

	$: entryPath =
		fullPath ??
		(entry.type === 'directory' ? `${currentPath}${entry.name}/` : `${currentPath}${entry.name}`);
	$: directoryPath = entryPath.endsWith('/') ? entryPath : `${entryPath}/`;
	$: writable = entry.writable !== false;
	$: canMutate = parentWritable && writable;
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

	const clearExpandTimer = () => {
		if (!expandTimer) return;
		clearTimeout(expandTimer);
		expandTimer = null;
	};

	// ── Rename state ─────────────────────────────────────────────────────
	let renaming = false;
	let renameValue = '';
	let renameInput: HTMLInputElement;

	const startRename = async () => {
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
		if (longPressTimer) clearTimeout(longPressTimer);
		clearExpandTimer();
	});

	// ── Click handler ────────────────────────────────────────────────────
	const handleClick = (e: MouseEvent) => {
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

<li class="group" data-file-row>
	<div
		class="w-full flex items-center transition-colors duration-75
			{selected ? 'bg-blue-50 dark:bg-blue-500/10' : 'hover:bg-gray-50/40 dark:hover:bg-white/4'}
			{dragOverFolder
			? 'bg-blue-50 dark:bg-blue-500/10 ring-1 ring-blue-400 dark:ring-blue-500 ring-inset'
			: ''}"
		role="presentation"
		on:dragover={(e) => {
			if (entry.type !== 'directory') return;
			if (!writable) return;
			if (!e.dataTransfer?.types.includes('application/x-terminal-file-move')) return;
			e.preventDefault();
			e.stopPropagation();
			dragOverFolder = true;
			if (!expanded && !expandTimer) {
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
			const raw = e.dataTransfer?.getData('application/x-terminal-file-move');
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
		{#if entry.type === 'directory'}
			<button
				type="button"
				class="mr-1.5 flex w-5 shrink-0 items-center self-stretch justify-center text-gray-400 dark:text-gray-600 hover:text-gray-600 dark:hover:text-gray-400"
				style="margin-left: {rowIndent};"
				on:click|stopPropagation={() => onToggleExpand(directoryPath)}
				aria-label={expanded ? $i18n.t('Collapse') : $i18n.t('Expand')}
			>
				<Icon
					name={expanded ? 'chevron-down' : 'chevron-right'}
					size={9}
					strokeWidth={1.5}
					class={loadingChildren ? 'animate-pulse' : ''}
				/>
			</button>
		{:else}
			<span class="mr-1.5 w-5 shrink-0 self-stretch" style="margin-left: {rowIndent};"></span>
		{/if}

		<button
			type="button"
			class="flex min-w-0 flex-1 items-center gap-2 py-1.5 pr-2 text-left"
			draggable={canMutate}
			on:dragstart={(e) => {
				if (!canMutate) {
					e.preventDefault();
					return;
				}
				const filePath = entryPath.replace(/\/$/, '');
				// If dragging a selected item, drag all selected
				if (selected && selectedPaths.size > 1) {
					e.dataTransfer?.setData(
						'application/x-terminal-file-move',
						JSON.stringify({ paths: [...selectedPaths] })
					);
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
						'application/x-terminal-file-move',
						JSON.stringify({
							path: entry.type === 'directory' ? directoryPath : filePath,
							name: entry.name
						})
					);
				}
				if (entry.type === 'file') {
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
			on:click={handleClick}
			on:dblclick|preventDefault|stopPropagation={() => {
				startRename();
			}}
		>
			{#if selectionMode || selected}
				<!-- Checkbox indicator -->
				<div
					class="size-3.5 shrink-0 rounded border transition-colors flex items-center justify-center
						{selected
						? 'bg-blue-500 dark:bg-blue-600 border-blue-500 dark:border-blue-600 text-white'
						: 'border-gray-300 dark:border-gray-600'}"
				>
					{#if selected}
						<Icon name="check" size={10} strokeWidth={2} />
					{/if}
				</div>
			{/if}
			<FileTypeIcon name={entry.name} type={entry.type} size={12} />
			{#if renaming}
				<!-- svelte-ignore a11y-click-events-have-key-events -->
				<input
					bind:this={renameInput}
					bind:value={renameValue}
					class="flex-1 text-xs bg-transparent border border-gray-100 dark:border-white/[0.06] rounded px-1.5 py-0.5 outline-none focus:border-blue-400 dark:focus:border-blue-500 text-gray-800 dark:text-gray-200 min-w-0"
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
				<span class="flex-1 text-xs text-gray-800 dark:text-gray-200 truncate">
					{entry.name}
				</span>
			{/if}
			{#if !writable && !renaming}
				<span class="text-[0.625rem] text-gray-400 shrink-0">Read-only</span>
			{/if}
			{#if entry.type === 'file' && entry.size !== undefined && !renaming}
				{#if showDate && entry.modified}
					<span class="text-[0.625rem] text-gray-400 shrink-0"
						>{formatRelativeTime(entry.modified)}</span
					>
				{/if}
				<span class="text-xs text-gray-400 shrink-0">{formatFileSize(entry.size)}</span>
			{:else if entry.type === 'directory' && showDate && entry.modified && !renaming}
				<span class="text-[0.625rem] text-gray-400 shrink-0"
					>{formatRelativeTime(entry.modified)}</span
				>
			{/if}
		</button>

		<Dropdown bind:show={menuOpen} align="end" sideOffset={4}>
			<button
				class="shrink-0 flex h-5 w-5 items-center justify-center mr-1 rounded transition
					text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-400
					hover:bg-gray-50/40 dark:hover:bg-white/4"
				aria-label={$i18n.t('More')}
			>
				<Icon name="three-dots" size={12} strokeWidth={1.4} />
			</button>

			<div slot="content">
				<DropdownMenu className="min-w-[9.375rem] z-[9999999]">
					<button
						type="button"
						class="select-none flex h-7 w-full items-center gap-2 rounded-lg px-2 text-xs hover:bg-gray-50/40 dark:hover:bg-white/4 transition"
						on:click={(e) => {
							e.stopPropagation();
							menuOpen = false;
							onOpen(entry);
						}}
					>
						<Icon
							name={entry.type === 'directory' ? 'folder' : 'eye'}
							size={12}
							strokeWidth={1.4}
						/>
						<div class="flex items-center">
							{entry.type === 'directory' ? $i18n.t('Open Folder') : $i18n.t('Open')}
						</div>
					</button>

					{#if entry.type === 'directory'}
						<button
							type="button"
							class="select-none flex h-7 w-full items-center gap-2 rounded-lg px-2 text-xs hover:bg-gray-50/40 dark:hover:bg-white/4 transition"
							on:click={(e) => {
								e.stopPropagation();
								menuOpen = false;
								onToggleExpand(directoryPath);
							}}
						>
							<Icon
								name={expanded ? 'chevron-down' : 'chevron-right'}
								size={12}
								strokeWidth={1.4}
							/>
							<div class="flex items-center">
								{expanded ? $i18n.t('Collapse') : $i18n.t('Expand')}
							</div>
						</button>
					{:else}
						<button
							type="button"
							class="select-none flex h-7 w-full items-center gap-2 rounded-lg px-2 text-xs hover:bg-gray-50/40 dark:hover:bg-white/4 transition"
							on:click={(e) => {
								e.stopPropagation();
								menuOpen = false;
								onDownload(entryPath);
							}}
						>
							<Icon name="download" size={12} strokeWidth={1.4} />
							<div class="flex items-center">{$i18n.t('Download')}</div>
						</button>
					{/if}

					<button
						type="button"
						class="select-none flex h-7 w-full items-center gap-2 rounded-lg px-2 text-xs hover:bg-gray-50/40 dark:hover:bg-white/4 transition"
						on:click={async (e) => {
							e.stopPropagation();
							menuOpen = false;
							if (await copyToClipboard(entryPath)) {
								toast.success($i18n.t('Path copied'));
							}
						}}
					>
						<Icon name="copy" size={12} strokeWidth={1.4} />
						<div class="flex items-center">{$i18n.t('Copy Path')}</div>
					</button>

					<button
						type="button"
						class="select-none flex h-7 w-full items-center gap-2 rounded-lg px-2 text-xs hover:bg-gray-50/40 dark:hover:bg-white/4 transition disabled:opacity-40 disabled:hover:bg-transparent"
						disabled={!canMutate}
						on:click={(e) => {
							e.stopPropagation();
							if (!canMutate) return;
							menuOpen = false;
							startRename();
						}}
					>
						<Icon name="pencil" size={12} strokeWidth={1.4} />
						<div class="flex items-center">{$i18n.t('Rename')}</div>
					</button>

					<button
						type="button"
						class="select-none flex h-7 w-full items-center gap-2 rounded-lg px-2 text-xs hover:bg-gray-50/40 dark:hover:bg-white/4 transition disabled:opacity-40 disabled:hover:bg-transparent"
						disabled={!canMutate}
						on:click={(e) => {
							e.stopPropagation();
							if (!canMutate) return;
							menuOpen = false;
							onDelete(entryPath.replace(/\/$/, ''), entry.name);
						}}
					>
						<Icon name="trash" size={12} strokeWidth={1.4} />
						<div class="flex items-center">{$i18n.t('Delete')}</div>
					</button>
				</DropdownMenu>
			</div>
		</Dropdown>
	</div>
</li>
