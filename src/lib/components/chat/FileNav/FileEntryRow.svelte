<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, tick, onDestroy } from 'svelte';
	import { formatFileSize } from '$lib/utils';
	import type { FileEntry } from '$lib/apis/terminal';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Folder from '../../icons/Folder.svelte';
	import EllipsisHorizontal from '../../icons/EllipsisHorizontal.svelte';
	import GarbageBin from '../../icons/GarbageBin.svelte';
	import Pencil from '../../icons/Pencil.svelte';
	import Clipboard from '../../icons/Clipboard.svelte';

	const i18n = getContext('i18n');

	export let entry: FileEntry;
	export let currentPath: string;
	export let terminalUrl: string = '';
	export let terminalKey: string = '';

	export let onOpen: (entry: FileEntry) => void = () => {};
	export let onDownload: (path: string) => void = () => {};
	export let onDelete: (path: string, name: string) => void = () => {};
	export let onMove: (source: string, destFolder: string) => void = () => {};
	export let onRename: (oldPath: string, newName: string) => void = () => {};

	// ── Selection ─────────────────────────────────────────────────────────
	export let selected: boolean = false;
	export let selectionMode: boolean = false;
	export let selectedPaths: Set<string> = new Set();
	export let onSelect: (entry: FileEntry, event: MouseEvent) => void = () => {};
	export let onLongPress: () => void = () => {};

	let dragOverFolder = false;

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
		onRename(`${currentPath}${entry.name}`, newName);
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
			onSelect(entry, e as any);
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
			onSelect(entry, e);
			return;
		}

		// In selection mode (touch) → toggle select
		if (selectionMode) {
			onSelect(entry, e);
			return;
		}

		// Normal click → open
		onOpen(entry);
	};
</script>

<li class="group">
	<div
		class="w-full flex items-center transition
			{selected ? 'bg-blue-50 dark:bg-blue-900/20' : 'hover:bg-gray-50 dark:hover:bg-gray-800'}
			{dragOverFolder
			? 'bg-blue-50 dark:bg-blue-900/30 ring-1 ring-blue-400 dark:ring-blue-500 ring-inset'
			: ''}"
		role={entry.type === 'directory' ? 'button' : undefined}
		on:dragover={(e) => {
			if (entry.type !== 'directory') return;
			if (!e.dataTransfer?.types.includes('application/x-terminal-file-move')) return;
			e.preventDefault();
			e.stopPropagation();
			dragOverFolder = true;
		}}
		on:dragleave={(e) => {
			if (entry.type !== 'directory') return;
			e.stopPropagation();
			dragOverFolder = false;
		}}
		on:drop={(e) => {
			if (entry.type !== 'directory') return;
			const raw = e.dataTransfer?.getData('application/x-terminal-file-move');
			if (!raw) return;
			e.preventDefault();
			e.stopPropagation();
			dragOverFolder = false;
			try {
				const data = JSON.parse(raw);
				const paths = data.paths || (data.path ? [data.path] : []);
				const destFolder = `${currentPath}${entry.name}/`;
				for (const p of paths) {
					if (p + '/' === destFolder || p === destFolder) continue;
					onMove(p, destFolder);
				}
			} catch {}
		}}
	>
		<button
			class="flex-1 flex items-center gap-2 px-3 py-1.5 text-left min-w-0"
			draggable={true}
			on:dragstart={(e) => {
				const filePath = `${currentPath}${entry.name}`;
				// If dragging a selected item, drag all selected
				if (selected && selectedPaths.size > 1) {
					e.dataTransfer?.setData(
						'application/x-terminal-file-move',
						JSON.stringify({ paths: [...selectedPaths] })
					);
					// Custom drag ghost showing count
					const ghost = document.createElement('div');
					ghost.style.cssText =
						'position:fixed;top:-1000px;left:-1000px;display:flex;align-items:center;gap:6px;padding:4px 10px;border-radius:8px;background:#374151;color:#fff;font-size:12px;white-space:nowrap;pointer-events:none;';
					ghost.textContent = `${selectedPaths.size} items`;
					document.body.appendChild(ghost);
					e.dataTransfer?.setDragImage(ghost, 0, 0);
					requestAnimationFrame(() => ghost.remove());
				} else {
					e.dataTransfer?.setData(
						'application/x-terminal-file-move',
						JSON.stringify({ path: filePath, name: entry.name })
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
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="size-2.5"
						>
							<path
								fill-rule="evenodd"
								d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
								clip-rule="evenodd"
							/>
						</svg>
					{/if}
				</div>
			{/if}
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
			{#if renaming}
				<!-- svelte-ignore a11y-click-events-have-key-events -->
				<input
					bind:this={renameInput}
					bind:value={renameValue}
					class="flex-1 text-xs bg-transparent border border-gray-200 dark:border-gray-700 rounded px-1.5 py-0.5 outline-none focus:border-blue-400 dark:focus:border-blue-500 text-gray-800 dark:text-gray-200 min-w-0"
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
			{#if entry.type === 'file' && entry.size !== undefined && !renaming}
				<span class="text-xs text-gray-400 shrink-0">{formatFileSize(entry.size)}</span>
			{/if}
		</button>

		<Dropdown align="end" sideOffset={4}>
			<button
				class="shrink-0 p-0.5 mr-1 rounded-lg transition
					text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-400
					hover:bg-gray-100 dark:hover:bg-gray-800"
				aria-label={$i18n.t('More')}
			>
				<EllipsisHorizontal className="size-3.5" />
			</button>

			<div slot="content">
				<div
					class="min-w-[150px] rounded-2xl p-1 z-[9999999] bg-white dark:bg-gray-850 dark:text-white shadow-lg border border-gray-100 dark:border-gray-800"
				>
					<button
						type="button"
						class="select-none flex rounded-xl py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition items-center gap-2 text-sm"
						on:click={(e) => {
							e.stopPropagation();
							const path =
								entry.type === 'directory'
									? `${currentPath}${entry.name}/`
									: `${currentPath}${entry.name}`;
							onDownload(path);
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
					</button>

					<button
						type="button"
						class="select-none flex rounded-xl py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition items-center gap-2 text-sm"
						on:click={(e) => {
							e.stopPropagation();
							const path =
								entry.type === 'directory'
									? `${currentPath}${entry.name}/`
									: `${currentPath}${entry.name}`;
							navigator.clipboard.writeText(path).then(() => {
								toast.success($i18n.t('Path copied'));
							});
						}}
					>
						<Clipboard className="size-4" strokeWidth="1.5" />
						<div class="flex items-center">{$i18n.t('Copy Path')}</div>
					</button>

					<button
						type="button"
						class="select-none flex rounded-xl py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition items-center gap-2 text-sm"
						on:click={(e) => {
							e.stopPropagation();
							startRename();
						}}
					>
						<Pencil className="size-4" strokeWidth="1.5" />
						<div class="flex items-center">{$i18n.t('Rename')}</div>
					</button>

					<button
						type="button"
						class="select-none flex rounded-xl py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition items-center gap-2 text-sm"
						on:click={(e) => {
							e.stopPropagation();
							onDelete(`${currentPath}${entry.name}`, entry.name);
						}}
					>
						<GarbageBin className="size-4" />
						<div class="flex items-center">{$i18n.t('Delete')}</div>
					</button>
				</div>
			</div>
		</Dropdown>
	</div>
</li>
