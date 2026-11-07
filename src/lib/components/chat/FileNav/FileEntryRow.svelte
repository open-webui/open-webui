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
	import type { GitFile } from '$lib/apis/terminal/git';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import FileTypeIcon from './FileTypeIcon.svelte';
	import FileGridIcon from './FileGridIcon.svelte';
	import Icon from './Icon.svelte';
	import FolderOpen from '$lib/components/icons/FolderOpen.svelte';

	export let dragType = 'application/x-terminal-file-move';
	export let dragContext = '';
	export let variant: 'terminal' | 'workspace' = 'terminal';
	export let viewMode: 'grid' | 'list' = 'list';
	const i18n: any = getContext('i18n');

	export let entry: FileEntry;
	export let gitFile: GitFile | null = null;
	$: gitDecoration = gitFile
		? ((
				{
					added: {
						char: 'A',
						label: $i18n.t('Added'),
						color: 'text-emerald-700/85 dark:text-emerald-300/85'
					},
					untracked: {
						char: 'U',
						label: $i18n.t('Untracked'),
						color: 'text-[#476f36] dark:text-[#91bd91]'
					},
					modified: {
						char: 'M',
						label: $i18n.t('Modified'),
						color: 'text-[#735c2a] dark:text-[#c7ad78]'
					},
					deleted: {
						char: 'D',
						label: $i18n.t('Deleted'),
						color: 'text-rose-600/85 dark:text-rose-300/85'
					},
					renamed: {
						char: 'R',
						label: $i18n.t('Renamed'),
						color: 'text-sky-600/85 dark:text-sky-300/85'
					},
					copied: {
						char: 'C',
						label: $i18n.t('Copied'),
						color: 'text-sky-600/80 dark:text-sky-300/80'
					},
					'type-changed': {
						char: 'T',
						label: $i18n.t('Type changed'),
						color: 'text-violet-600/80 dark:text-violet-300/80'
					},
					conflict: {
						char: '!',
						label: $i18n.t('Conflict'),
						color: 'text-orange-600/90 dark:text-orange-300/90'
					}
				} as Record<string, { char: string; label: string; color: string }>
			)[gitFile.status] ?? {
				char: '?',
				label: $i18n.t('Changed'),
				color: 'text-gray-700 dark:text-gray-300'
			})
		: null;
	$: nameColor = gitDecoration?.color ?? 'text-gray-800 dark:text-gray-200';
	$: gitLabel =
		gitDecoration && gitFile
			? `${entry.type === 'directory' ? $i18n.t('Contains {{status}}', { status: gitDecoration.label }) : gitDecoration.label} · ${[
					gitFile.staged ? $i18n.t('Staged changes') : '',
					gitFile.unstaged ? $i18n.t('Unstaged changes') : ''
				]
					.filter(Boolean)
					.join(', ')}`
			: '';
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
	export let onDragStart: ((event: DragEvent, path: string) => void) | null = null;
	export let onNewFolder: ((path: string) => void) | undefined = undefined;
	export let onNewFile: ((path: string) => void) | undefined = undefined;
	export let onSelectForComparison: (() => void) | undefined = undefined;
	export let onCompareWithSelected: (() => void) | undefined = undefined;
	export let comparisonPath: string | null = null;
	export let onDownload: (path: string) => void = () => {};
	export let onDelete: (path: string, name: string) => void = () => {};
	export let onMove: (sources: string[], destFolder: string) => void | Promise<void> = () => {};
	export let onRename: (oldPath: string, newName: string) => void = () => {};

	// Selection
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
	export let dateField: 'modified' | 'created' = 'modified';
	export let showHidden: boolean = false;
	export let parentWritable = true;

	$: entryDate = entry[dateField];
	$: entryPath =
		fullPath ??
		(entry.type === 'directory' ? `${currentPath}${entry.name}/` : `${currentPath}${entry.name}`);
	$: directoryPath = entryPath.endsWith('/') ? entryPath : `${entryPath}/`;
	$: writable = entry.writable !== false;
	$: canMutate = parentWritable && writable;
	$: menuItemClass =
		variant === 'workspace'
			? 'select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-xs hover:text-gray-900 dark:hover:text-gray-100'
			: 'select-none flex h-7 w-full items-center gap-2 rounded-lg px-2 text-xs hover:bg-gray-50/40 dark:hover:bg-white/4 transition';
	$: rowIndent = `${8 + depth * 16}px`;
	const fitGridName = (node: HTMLElement, name: string) => {
		const fit = () => {
			if (!node.clientWidth) return;
			node.textContent = name;
			if (node.scrollHeight <= node.clientHeight) return;
			const characters = Array.from(name);
			const dot = name.lastIndexOf('.');
			const extensionLength = dot > 0 ? Array.from(name.slice(dot)).length : 0;
			let low = Math.max(2, extensionLength + 1);
			let high = characters.length - 1;
			let fitted = name;
			while (low <= high) {
				const count = Math.floor((low + high) / 2);
				const tail = Math.max(extensionLength, Math.floor(count / 2));
				node.textContent = `${characters.slice(0, count - tail).join('')}…${characters.slice(-tail).join('')}`;
				if (node.scrollHeight <= node.clientHeight) {
					fitted = node.textContent;
					low = count + 1;
				} else high = count - 1;
			}
			node.textContent = fitted;
		};
		const observer = new ResizeObserver(fit);
		observer.observe(node);
		fit();
		return {
			update(value: string) {
				name = value;
				fit();
			},
			destroy: () => observer.disconnect()
		};
	};

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

	// Rename state
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
		if (!renaming) return;
		const newName = renameValue.trim();
		renaming = false;
		if (!newName || newName === entry.name) return;
		onRename(entryPath.replace(/\/$/, ''), newName);
	};

	const cancelRename = () => {
		renaming = false;
		renameValue = '';
	};

	// Touch uses the same drop handlers as mouse dragging, including chat attachments.
	const touchDrag = (node: HTMLButtonElement) => {
		let held = false;
		let timer: ReturnType<typeof setTimeout> | null = null;
		let start: Touch | null = null;
		let point: Touch | null = null;
		let transfer: DataTransfer | null = null;
		let target: Element | null = null;
		let ghost: HTMLDivElement | null = null;
		let frame = 0;
		let accepted = false;
		const send = (element: Element | null, type: string) =>
			element?.dispatchEvent(
				new DragEvent(type, {
					bubbles: true,
					cancelable: true,
					dataTransfer: transfer,
					clientX: point?.clientX ?? 0,
					clientY: point?.clientY ?? 0
				})
			) === false;
		const cleanup = () => {
			if (timer) clearTimeout(timer);
			cancelAnimationFrame(frame);
			send(target, 'dragleave');
			if (transfer) send(node, 'dragend');
			ghost?.remove();
			timer = null;
			start = point = null;
			transfer = null;
			target = ghost = null;
			dragging = false;
			held = false;
			document.removeEventListener('touchmove', move);
			document.removeEventListener('touchstart', cancelMultiTouch);
			document.removeEventListener('touchend', end);
			document.removeEventListener('touchcancel', cancel);
			window.removeEventListener('blur', cancel);
		};
		const update = () => {
			if (!point || !ghost) return;
			ghost.style.transform = `translate(${point.clientX + 12}px, ${point.clientY + 12}px)`;
			const next = document.elementFromPoint(point.clientX, point.clientY);
			if (next !== target) {
				send(target, 'dragleave');
				target = next;
				send(target, 'dragenter');
			}
			accepted = send(target, 'dragover');
			// Scroll the nearest list while holding near its edge.
			for (let parent = target; parent; parent = parent.parentElement) {
				if (
					!(parent instanceof HTMLElement) ||
					parent.scrollHeight <= parent.clientHeight ||
					!['auto', 'scroll'].includes(getComputedStyle(parent).overflowY)
				)
					continue;
				const rect = parent.getBoundingClientRect();
				const dy = point.clientY < rect.top + 28 ? -6 : point.clientY > rect.bottom - 28 ? 6 : 0;
				parent.scrollTop += dy;
				break;
			}
			frame = requestAnimationFrame(update);
		};
		const move = (event: TouchEvent) => {
			if (!start || event.touches.length !== 1) {
				cleanup();
				return;
			}
			point = event.touches[0];
			if (!held) {
				if (Math.hypot(point.clientX - start.clientX, point.clientY - start.clientY) > 8) cleanup();
				return;
			}
			event.preventDefault();
			if (transfer || Math.hypot(point.clientX - start.clientX, point.clientY - start.clientY) <= 8)
				return;
			transfer = new DataTransfer();
			if (send(node, 'dragstart') || !transfer.types.length) {
				cleanup();
				return;
			}
			ghost = document.createElement('div');
			ghost.textContent =
				selected && selectedPaths.size > 1 ? `${selectedPaths.size} items` : entry.name;
			ghost.style.cssText =
				'position:fixed;left:0;top:0;z-index:99999;pointer-events:none;max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;border-radius:8px;padding:6px 10px;background:#374151;color:white;font-size:12px;';
			document.body.appendChild(ghost);
			update();
		};
		const end = (event: TouchEvent) => {
			if (held) event.preventDefault();
			if (transfer) {
				point = event.changedTouches[0] ?? point;
				cancelAnimationFrame(frame);
				update();
			}
			if (transfer && accepted) send(target, 'drop');
			cleanup();
		};
		const cancel = () => cleanup();
		const cancelMultiTouch = (event: TouchEvent) => {
			if (event.touches.length > 1) cleanup();
		};
		const begin = (event: TouchEvent) => {
			cleanup();
			if (renaming || event.touches.length !== 1) return;
			start = point = event.touches[0];
			timer = setTimeout(() => {
				held = true;
				openPreview = false;
				onLongPress();
				if (!selected) onSelect(entry, event as unknown as MouseEvent, entryPath, rowIndex);
			}, 500);
			document.addEventListener('touchmove', move, { passive: false });
			document.addEventListener('touchstart', cancelMultiTouch, { passive: true });
			document.addEventListener('touchend', end, { passive: false });
			document.addEventListener('touchcancel', cancel);
			window.addEventListener('blur', cancel);
		};
		const contextMenu = (event: Event) => {
			if (start || held) event.preventDefault();
		};
		node.addEventListener('touchstart', begin, { passive: true });
		node.addEventListener('contextmenu', contextMenu);
		return {
			destroy() {
				cleanup();
				node.removeEventListener('touchstart', begin);
				node.removeEventListener('contextmenu', contextMenu);
			}
		};
	};

	onDestroy(() => {
		if (closeActiveHoverPreview === closeHoverPreview) closeActiveHoverPreview = null;
		clearExpandTimer();
	});

	// Click handler
	const handleClick = (e: MouseEvent) => {
		openPreview = false;
		if (renaming) return;

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

{#snippet gitBadge()}
	{#if gitFile && gitDecoration}
		<span
			role="img"
			aria-label={gitLabel}
			title={gitLabel}
			class="flex shrink-0 items-center gap-1 text-[0.625rem] font-mono font-medium {viewMode ===
			'list'
				? 'mx-1'
				: 'mx-0.5'}"
		>
			{#if entry.type === 'directory'}
				<span class="size-1.5 rounded-full bg-current {gitDecoration.color}"></span>
			{:else if gitFile.binary}
				<span class={gitDecoration.color}>{gitDecoration.char}</span>
			{:else}
				<span class="text-green-600 dark:text-green-400">+{gitFile.additions ?? 0}</span>
				<span class="text-red-500 dark:text-red-400">-{gitFile.deletions ?? 0}</span>
			{/if}
		</span>
	{/if}
{/snippet}

<li class="group min-w-0 {viewMode === 'grid' ? 'self-start' : ''}" data-file-row={entryPath}>
	<div
		class="w-full flex items-center transition-colors duration-75 {viewMode === 'grid'
			? 'relative rounded-xl'
			: ''} {variant === 'workspace' ? 'rounded-xl' : ''}
			{selected || active
			? viewMode === 'grid'
				? 'bg-blue-50 dark:bg-blue-500/15'
				: 'bg-gray-100 dark:bg-white/8'
			: viewMode === 'grid'
				? ''
				: 'hover:bg-gray-100 dark:hover:bg-white/10'}
			{dragOverFolder ? 'bg-blue-50 dark:bg-blue-500/15 ring-2 ring-blue-500/60 ring-inset' : ''}"
		role="presentation"
		on:dragover={(e) => {
			if (entry.type !== 'directory') return;
			if (!canMutate) {
				e.stopPropagation();
				return;
			}
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
			if (!canMutate) {
				e.stopPropagation();
				return;
			}
			const raw = e.dataTransfer?.getData(dragType);
			if (!raw) return;
			e.preventDefault();
			e.stopPropagation();
			dragOverFolder = false;
			clearExpandTimer();
			try {
				const data = JSON.parse(raw);
				if (data.context !== dragContext) return;
				const paths = (data.paths || (data.path ? [data.path] : [])) as string[];
				const destFolder = directoryPath;
				await onMove(
					paths.filter((p) => p + '/' !== destFolder && p !== destFolder),
					destFolder
				);
			} catch {}
		}}
	>
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
				class="mr-1.5 flex size-3 shrink-0 items-center justify-center rounded-[3px] border transition-colors {selected
					? 'bg-gray-100 border-gray-400 text-gray-700 dark:bg-gray-700 dark:border-gray-500 dark:text-gray-200'
					: 'border-gray-300 dark:border-gray-600'} {viewMode === 'grid'
					? 'absolute top-1.5 left-1.5 z-10 !mr-0'
					: ''}"
				on:click|stopPropagation={(event) => onSelect(entry, event, entryPath, rowIndex)}
			>
				{#if selected}<Icon name="check" size={8} strokeWidth={2} />{/if}
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
						class="flex min-w-0 flex-1 items-center rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 {viewMode ===
						'grid'
							? 'h-24 flex-col gap-0.5 px-1 py-2 text-center'
							: 'gap-1.5 py-1.5 pr-2 text-left'}"
						title={viewMode === 'grid' || hoverDisabled ? entry.name : undefined}
						aria-label={viewMode === 'grid' ? entry.name : undefined}
						draggable={canMutate || (entry.type === 'file' && onDragStart !== null)}
						on:dragend={() => (dragging = false)}
						on:dragstart={(e) => {
							openPreview = false;
							if (!canMutate && !(entry.type === 'file' && onDragStart)) {
								e.preventDefault();
								return;
							}
							dragging = true;
							const filePath = entryPath.replace(/\/$/, '');
							onDragStart?.(e, entryPath);
							// If dragging a selected item, drag all selected
							if (selected && selectedPaths.size > 1) {
								if (canMutate)
									e.dataTransfer?.setData(
										dragType,
										JSON.stringify({ paths: [...selectedPaths], context: dragContext })
									);
								// Custom drag ghost showing count
								const ghost = document.createElement('div');
								ghost.style.cssText =
									'position:fixed;top:-1000px;left:-1000px;display:flex;align-items:center;gap:0.375rem;padding:0.25rem 0.625rem;border-radius:0.5rem;background:#374151;color:#fff;font-size:0.75rem;white-space:nowrap;pointer-events:none;';
								ghost.textContent = `${selectedPaths.size} items`;
								document.body.appendChild(ghost);
								e.dataTransfer?.setDragImage(ghost, 0, 0);
								requestAnimationFrame(() => ghost.remove());
							} else if (canMutate) {
								e.dataTransfer?.setData(
									dragType,
									JSON.stringify({
										path: entry.type === 'directory' ? directoryPath : filePath,
										name: entry.name,
										context: dragContext
									})
								);
							}
						}}
						use:touchDrag
						style="-webkit-touch-callout: none; user-select: none;"
						aria-expanded={variant === 'workspace' && entry.type === 'directory'
							? expanded
							: props['aria-expanded']}
						on:click={handleClick}
						on:dblclick|preventDefault|stopPropagation={() => {
							startRename();
						}}
					>
						{#if variant === 'workspace' && viewMode === 'list'}
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
						{:else}
							{#key JSON.stringify( [terminalUrl, terminalKey, terminalSessionId, entryPath, entry.modified, entry.size] )}
								<FileGridIcon
									{entry}
									path={entryPath}
									{terminalUrl}
									{terminalKey}
									sessionId={terminalSessionId}
									itemCount={folderItemCount}
								/>
							{/key}
						{/if}
						{#if renaming}
							<!-- svelte-ignore a11y-click-events-have-key-events -->
							<input
								aria-label={$i18n.t('Rename')}
								bind:this={renameInput}
								bind:value={renameValue}
								class="flex-1 text-xs bg-transparent outline-hidden text-gray-800 dark:text-gray-200 min-w-0 {variant ===
								'workspace'
									? 'h-4 p-0 leading-4'
									: 'py-0.5'} {viewMode === 'grid'
									? 'w-full flex-none text-center ring-1 ring-blue-500 rounded'
									: ''}"
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
						{:else if viewMode === 'grid' && entry.type === 'directory'}
							<span class="h-4 w-full min-w-0 shrink-0 truncate text-xs leading-4 {nameColor}">
								{entry.name}
							</span>
						{:else if viewMode === 'grid'}
							<span
								use:fitGridName={entry.name}
								class="max-h-8 w-full min-w-0 shrink-0 overflow-hidden [overflow-wrap:anywhere] text-xs leading-4 {nameColor}"
							></span>
						{:else}
							<span class="flex-1 truncate text-xs {nameColor}">
								{entry.name}
							</span>
						{/if}
						{#if viewMode === 'list' && !renaming}
							{@render gitBadge()}
						{/if}
						{#if !writable && !renaming && variant !== 'workspace' && viewMode !== 'grid'}
							<span class="text-[0.625rem] text-gray-400 shrink-0">{$i18n.t('Read-only')}</span>
						{/if}
						{#if viewMode === 'grid' && !renaming}
							<span
								class="flex w-full min-w-0 shrink-0 items-center justify-center gap-1 text-[11px] leading-3.5 text-gray-500 dark:text-gray-400"
							>
								{@render gitBadge()}
								{#if entry.type === 'directory'}
									{#key folderContentsVersion}
										<span use:observeFolderContents class="min-w-0 truncate"
											>{folderCountLabel}</span
										>
									{/key}
								{/if}
								{#if !writable && variant !== 'workspace'}
									<span title={$i18n.t('Read-only')} aria-label={$i18n.t('Read-only')}
										><Icon name="lock" size={10} strokeWidth={1.5} /></span
									>
								{/if}
							</span>
						{:else if entry.type === 'file' && entry.size !== undefined && !renaming}
							{#if showDate && entryDate != null}
								<span class="text-[0.625rem] text-gray-400 shrink-0"
									>{formatRelativeTime(entryDate)}</span
								>
							{/if}
							<span class="text-xs text-gray-400 shrink-0">{formatFileSize(entry.size)}</span>
						{:else if entry.type === 'directory' && !renaming}
							{#if showDate && entryDate != null}
								<span class="text-[0.625rem] text-gray-400 shrink-0"
									>{formatRelativeTime(entryDate)}</span
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
							sideOffset={viewMode === 'grid' ? 4 : 12}
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
					? 'absolute left-[calc(50%_+_16px)] -top-[3px] !m-0 !h-6 !w-6 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 max-md:opacity-100'
					: ''}"
				style:opacity={viewMode === 'grid' && menuOpen ? 1 : undefined}
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
