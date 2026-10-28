<script lang="ts">
	import { getContext, tick } from 'svelte';
	// @ts-expect-error The installed SortableJS package has no type declarations.
	import Sortable from 'sortablejs';
	import type { NotePage, NotePageOperation } from '$lib/apis/notes';
	import NativeSelect from '$lib/components/common/NativeSelect.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import {
		tabRows,
		tabAncestors,
		tabBranchIds,
		siblingMove,
		pageDropMove,
		type PageDropPosition
	} from './utils';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	import NoteTabMenu from './NoteTabMenu.svelte';
	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	export let pages: NotePage[] = [];
	export let activeId = '';
	export let editable = false;
	export let busy = false;
	export let onSelect: (id: string) => Promise<void>;
	export let onAction: (operation: Omit<NotePageOperation, 'revision'>) => Promise<string | null>;
	export let onCopyLink: (id: string) => void;
	export let onDownload: (id: string, type: string) => void;
	export let onClose: () => void;
	let collapsed = new Set<string>();
	$: rows = tabRows(pages, collapsed);
	$: allRows = tabRows(pages);
	$: focusId = rows.some(({ page }) => page.id === activeId)
		? activeId
		: [...tabAncestors(pages, activeId)]
				.reverse()
				.find((id) => rows.some(({ page }) => page.id === id));
	$: revealActive(pages, activeId);
	let moving: NotePage | null = null;
	let showMove = false;
	let moveParent = '';
	$: movingBranch = moving ? tabBranchIds(pages, moving.id) : new Set<string>();
	$: moveOptions = [
		{ value: '', label: $i18n.t('Top level') },
		...allRows
			.filter(({ page }) => !movingBranch.has(page.id))
			.map(({ page, path }) => ({ value: page.id, label: path }))
	];
	function revealActive(currentPages: NotePage[], id: string) {
		const ancestors = tabAncestors(currentPages, id);
		if (ancestors.some((id) => collapsed.has(id)))
			collapsed = new Set([...collapsed].filter((id) => !ancestors.includes(id)));
	}
	function toggleBranch(id: string) {
		const next = new Set(collapsed);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		collapsed = next;
	}
	function moveTo(page: NotePage) {
		moving = page;
		moveParent = page.parent_id ?? '';
		showMove = true;
	}

	let renaming = '';
	let title = '';
	let renameInput: HTMLInputElement;
	let deleting: NotePage | null = null;
	let confirmDelete = false;

	async function rename(page: NotePage) {
		renaming = page.id;
		title = page.title;
		await tick();
		renameInput?.focus();
		renameInput?.select();
	}
	async function commitRename() {
		if (!renaming) return;
		const id = renaming;
		renaming = '';
		if (title.trim() && title.trim() !== pages.find((p) => p.id === id)?.title) {
			await onAction({ action: 'rename', page_id: id, title: title.trim() });
		}
	}
	async function create(parentId: string | null = null) {
		let n = pages.length + 1;
		while (pages.some((p) => p.title === $i18n.t('Page {{number}}', { number: n }))) n++;
		const id = await onAction({
			action: 'create',
			parent_id: parentId,
			title: $i18n.t('Page {{number}}', { number: n })
		});
		if (id) {
			await tick();
			const page = pages.find((p) => p.id === id);
			if (page) await rename(page);
		}
	}
	function move(id: string, direction: number) {
		const operation = siblingMove(pages, id, direction);
		if (operation) return onAction(operation);
	}

	let dropTarget: { id: string; position: PageDropPosition } | null = null;
	function sortable(node: HTMLElement, disabled: boolean) {
		let draggedId = '';
		let cancelled = false;
		function trackDrop(event: MouseEvent | TouchEvent) {
			if (!draggedId || cancelled) return;
			const point = 'touches' in event ? (event.touches[0] ?? event.changedTouches[0]) : event;
			const row =
				point &&
				document
					.elementFromPoint(point.clientX, point.clientY)
					?.closest<HTMLElement>('[data-page-id]');
			dropTarget = null;
			if (!row || !node.contains(row)) return;
			const id = row.dataset.pageId!;
			const rect = row.getBoundingClientRect();
			const offset = (point.clientY - rect.top) / rect.height;
			const position: PageDropPosition =
				offset < 0.25 ? 'before' : offset > 0.75 ? 'after' : 'inside';
			if (pageDropMove(pages, draggedId, id, position)) dropTarget = { id, position };
		}
		function cancelDrag(event: KeyboardEvent) {
			if (event.key === 'Escape' && draggedId) {
				cancelled = true;
				dropTarget = null;
			}
		}
		document.addEventListener('pointermove', trackDrop);
		document.addEventListener('touchmove', trackDrop, { passive: true });
		document.addEventListener('keydown', cancelDrag);
		const instance = new Sortable(node, {
			disabled,
			// Keep the tree stable while showing an explicit nesting or ordering target.
			sort: false,
			forceFallback: true,
			fallbackOnBody: true,
			fallbackTolerance: 4,
			ghostClass: 'opacity-40',
			draggable: '[data-page-id]:not([data-page-id="main"])',
			handle: '[role="treeitem"]',
			delay: 200,
			delayOnTouchOnly: true,
			onStart: (event: { item: HTMLElement }) => {
				draggedId = event.item.dataset.pageId!;
				cancelled = false;
			},
			onEnd: (event: { originalEvent?: MouseEvent | TouchEvent }) => {
				if (event.originalEvent) trackDrop(event.originalEvent);
				const target = dropTarget;
				const operation =
					!cancelled && !event.originalEvent?.type.includes('cancel') && target
						? pageDropMove(pages, draggedId, target.id, target.position)
						: null;
				draggedId = '';
				dropTarget = null;
				if (operation && target) {
					onAction(operation).then((id) => {
						if (id) collapsed = new Set([...collapsed].filter((id) => id !== operation.parent_id));
					});
				}
			}
		});
		return {
			update: (disabled: boolean) => instance.option('disabled', disabled),
			destroy: () => {
				instance.destroy();
				document.removeEventListener('pointermove', trackDrop);
				document.removeEventListener('touchmove', trackDrop);
				document.removeEventListener('keydown', cancelDrag);
			}
		};
	}
	function navigate(event: KeyboardEvent, id: string) {
		const index = rows.findIndex(({ page }) => page.id === id);
		const row = rows[index];
		let target: string | undefined;
		if (event.key === 'ArrowRight') {
			if (row.hasChildren && collapsed.has(id)) toggleBranch(id);
			else if (row.hasChildren) target = rows[index + 1]?.page.id;
		} else if (event.key === 'ArrowLeft') {
			if (row.hasChildren && !collapsed.has(id)) toggleBranch(id);
			else target = row.page.parent_id ?? undefined;
		} else {
			const next =
				event.key === 'ArrowDown'
					? Math.min(index + 1, rows.length - 1)
					: event.key === 'ArrowUp'
						? Math.max(index - 1, 0)
						: event.key === 'Home'
							? 0
							: event.key === 'End'
								? rows.length - 1
								: -1;
			if (next < 0) return;
			target = rows[next].page.id;
		}
		event.preventDefault();
		event.stopPropagation();
		if (target)
			onSelect(target).then(() => document.getElementById(`note-page-tab-${target}`)?.focus());
	}
</script>

<section id="note-tabs-panel" aria-label={$i18n.t('Pages')} class="flex h-full min-h-0 flex-col">
	<div class="flex h-8 shrink-0 items-center justify-between px-3 text-xs text-gray-500">
		<span>{$i18n.t('Pages')}</span>

		<button
			class="flex size-5 items-center justify-center rounded-lg hover:text-gray-900 dark:hover:text-white"
			aria-label={$i18n.t('Close pages')}
			on:click={onClose}><XMark className="size-3.5" /></button
		>
	</div>

	<div class="min-h-0 flex-1 overflow-y-auto px-2 pb-2">
		<div role="tree" aria-label={$i18n.t('Pages')} use:sortable={!editable || busy || !!renaming}>
			{#each rows as { page, depth, hasChildren, position, siblings, path } (page.id)}
				<div
					data-page-id={page.id}
					data-drop-position={dropTarget?.id === page.id ? dropTarget.position : undefined}
					style:margin-inline-start={`${Math.min(depth, 6) * 12}px`}
					class="page-row group relative flex items-center rounded-xl px-1 text-gray-800 dark:text-gray-200 transition {activeId ===
					page.id
						? 'bg-gray-50/60 dark:bg-gray-800/60'
						: 'hover:bg-gray-50/60 dark:hover:bg-gray-800/60'}"
				>
					{#if hasChildren}
						<button
							class="flex size-5 shrink-0 items-center justify-center rounded text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
							aria-label={$i18n.t(
								collapsed.has(page.id) ? 'Expand {{title}}' : 'Collapse {{title}}',
								{ title: page.title }
							)}
							aria-expanded={!collapsed.has(page.id)}
							on:click={() => toggleBranch(page.id)}
						>
							{#if collapsed.has(page.id)}<ChevronRight className="size-3" />{:else}<ChevronDown
									className="size-3"
								/>{/if}
						</button>
					{:else}<span class="size-5 shrink-0" aria-hidden="true"></span>{/if}
					{#if renaming === page.id}
						<input
							bind:this={renameInput}
							bind:value={title}
							maxlength="200"
							aria-label={$i18n.t('Page title')}
							class="h-[1.6875rem] min-w-0 flex-1 border-0 bg-transparent px-1 py-0 text-[0.8125rem] leading-5 font-normal outline-hidden focus:ring-0"
							on:blur={commitRename}
							on:keydown={(event) => {
								if (event.isComposing) return;
								if (event.key === 'Enter') {
									event.preventDefault();
									commitRename();
								}
								if (event.key === 'Escape') renaming = '';
							}}
						/>
					{:else}
						<button
							id={`note-page-tab-${page.id}`}
							role="treeitem"
							aria-level={depth + 1}
							aria-posinset={position}
							aria-setsize={siblings}
							aria-expanded={hasChildren ? !collapsed.has(page.id) : undefined}
							aria-selected={activeId === page.id}
							aria-controls="note-content-container"
							tabindex={focusId === page.id ? 0 : -1}
							disabled={busy}
							class="flex min-w-0 flex-1 items-center h-[1.6875rem] rounded-xl px-1 text-start text-[0.8125rem] leading-5 font-normal"
							title={path}
							on:click={() => onSelect(page.id)}
							on:keydown={(event) => navigate(event, page.id)}
							><span class="truncate">{page.title}</span></button
						>
					{/if}
					{#if editable}
						<button
							class="flex size-5 shrink-0 items-center justify-center rounded-lg text-gray-500 hover:text-gray-900 dark:hover:text-white {activeId ===
							page.id
								? ''
								: 'sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100'}"
							aria-label={$i18n.t('Add subpage to {{title}}', { title: page.title })}
							title={$i18n.t('Add subpage')}
							disabled={busy}
							on:click={() => create(page.id)}
							><Plus className="size-3.5" strokeWidth="1.5" /></button
						>
					{/if}
					<NoteTabMenu
						{page}
						{pages}
						{editable}
						{busy}
						{onCopyLink}
						{onDownload}
						onRename={rename}
						onMove={move}
						onMoveTo={moveTo}
						onCreate={create}
						onDelete={(page) => {
							deleting = page;
							confirmDelete = true;
						}}
						className={activeId === page.id
							? ''
							: 'sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100'}
					/>
				</div>
			{/each}
		</div>
		{#if editable}
			<button
				class="mt-1 flex h-[1.6875rem] w-full items-center rounded-xl px-7 text-start text-[0.8125rem] text-gray-500 hover:bg-gray-50/60 hover:text-gray-900 dark:hover:bg-gray-800/60 dark:hover:text-gray-100 transition disabled:opacity-40"
				disabled={busy}
				on:click={() => create(null)}>{$i18n.t('Add page')}</button
			>
		{/if}
	</div>
</section>

<ConfirmDialog
	bind:show={confirmDelete}
	title={$i18n.t('Delete page?')}
	on:confirm={() => deleting && onAction({ action: 'delete', page_id: deleting.id })}
>
	<div>
		{$i18n.t('Delete "{{title}}"? This cannot be undone.', { title: deleting?.title ?? '' })}
		{#if deleting && pages.some((page) => page.parent_id === deleting.id)}<p class="mt-2">
				{$i18n.t('Its subpages will be kept and moved up one level.')}
			</p>{/if}
	</div>
</ConfirmDialog>

<ConfirmDialog
	bind:show={showMove}
	title={$i18n.t('Move page')}
	confirmLabel={$i18n.t('Move')}
	on:confirm={() =>
		moving &&
		moveParent !== (moving.parent_id ?? '') &&
		onAction({ action: 'move', page_id: moving.id, parent_id: moveParent || null })}
>
	<div class="text-sm text-gray-500">
		{$i18n.t('Choose a parent page. Subpages move with this page.')}
	</div>
	<label class="block mt-3 text-sm">
		<span>{$i18n.t('Parent page')}</span>
		<NativeSelect
			bind:value={moveParent}
			options={moveOptions}
			className="w-full mt-2 rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-900 outline-hidden"
		/>
	</label>
</ConfirmDialog>

<style>
	.page-row[data-drop-position='inside'] {
		background-color: color-mix(in srgb, currentColor 8%, transparent);
	}
	.page-row[data-drop-position='before']::before,
	.page-row[data-drop-position='after']::after {
		content: '';
		position: absolute;
		inset-inline: 4px;
		height: 1px;
		border-radius: 1px;
		background: color-mix(in srgb, currentColor 20%, transparent);
		pointer-events: none;
	}
	.page-row[data-drop-position='before']::before {
		top: -1px;
	}
	.page-row[data-drop-position='after']::after {
		bottom: -1px;
	}
</style>
