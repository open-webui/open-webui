<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import { beforeNavigate, goto } from '$app/navigation';
	import { mobile } from '$lib/stores';
	import { getKnowledgeById } from '$lib/apis/knowledge';
	import { createFocusTrap } from 'focus-trap';
	import Files from './Files.svelte';
	import FileViewer from './FileViewer.svelte';
	import AddContentMenu from './AddContentMenu.svelte';
	import ResizableSidePanel from '$lib/components/common/ResizableSidePanel.svelte';
	import Drawer from '$lib/components/common/Drawer.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import AdjustmentsHorizontal from '$lib/components/icons/AdjustmentsHorizontal.svelte';
	import { newViewerState, type KnowledgeFile, type KnowledgeDirectory } from './types';

	export let knowledge: { id: string; name: string; write_access?: boolean };
	export let transfers: KnowledgeFile[] = [];
	export let syncing: string | null = null;
	export let onUpload: (
		type: string,
		parent: string | null,
		breadcrumbs: KnowledgeDirectory[]
	) => void = () => {};
	export let onSync = () => {};
	export let onReset = () => {};
	const i18n = getContext<any>('i18n');
	let tree: Files;
	let selected: KnowledgeFile | null = null;
	let state = newViewerState();
	let saving = false;
	let width = 280;
	let query = '';
	let inputQuery = '';
	let includeContent = false;
	let viewOption: string | null = null;
	let sortKey = 'updated_at';
	let direction = 'desc';
	let debounce: ReturnType<typeof setTimeout>;
	let showDiscard = false;
	let pendingAction: (() => void | Promise<void>) | null = null;
	let allowNavigation = false;
	$: dirty = state.editing && state.indexed !== null && state.draft !== state.indexed;
	$: drawerOpen = $mobile && selected !== null;
	$: if (!query) inputQuery = '';

	export const refresh = async () => {
		await tree?.refresh();
	};
	export const clearRemovedSelection = (ids?: string[]) => {
		if (selected && (!ids || ids.includes(selected.id!))) {
			selected = null;
			state = newViewerState();
		}
	};
	export const guard = (action: () => void | Promise<void>) => {
		if (saving) return;
		if (dirty) {
			pendingAction = action;
			showDiscard = true;
		} else action();
	};
	const select = (file: KnowledgeFile) => {
		if (file.id === selected?.id) return;
		guard(() => {
			selected = file;
			state = newViewerState();
		});
	};
	const close = () =>
		guard(() => {
			selected = null;
			state = newViewerState();
		});
	const changed = async (file?: KnowledgeFile, removed?: string[]) => {
		if (file && file.id === selected?.id) selected = file;
		else if (removed?.includes(selected?.id || '')) {
			selected = null;
			state = newViewerState();
		} else if (!file && !removed && selected) {
			const id = selected.id;
			const result = await getKnowledgeById(localStorage.token, knowledge.id);
			if (selected?.id === id && !result.files?.some((item: KnowledgeFile) => item.id === id)) {
				selected = null;
				state = newViewerState();
			}
		}
	};
	beforeNavigate((navigation) => {
		if (allowNavigation || (!dirty && !saving)) return;
		navigation.cancel();
		if (!navigation.willUnload && navigation.to && !saving)
			guard(() => {
				allowNavigation = true;
				goto(navigation.to!.url.href).finally(() => (allowNavigation = false));
			});
	});
	const trapFocus = (node: HTMLElement) => {
		const trap = createFocusTrap(node, { escapeDeactivates: false });
		trap.activate();
		return { destroy: () => trap.deactivate() };
	};
	onDestroy(() => clearTimeout(debounce));
</script>

<ConfirmDialog
	bind:show={showDiscard}
	title={$i18n.t('Discard unsaved changes?')}
	on:confirm={() => {
		const action = pendingAction;
		pendingAction = null;
		state = { ...state, editing: false, draft: state.indexed || '' };
		action?.();
	}}
	on:cancel={() => (pendingAction = null)}
/>
<div
	class="flex h-full min-h-0 overflow-hidden rounded-2xl border border-gray-100 bg-gray-50/60 dark:border-white/5 dark:bg-white/[0.03]"
>
	{#if $mobile}{@render sidebar()}
	{:else}<ResizableSidePanel
			open
			side="left"
			bind:width
			minWidth={220}
			maxWidth={480}
			minSiblingWidth={320}
			className="min-h-0"
			resizerId="knowledge-files-resizer">{@render sidebar()}</ResizableSidePanel
		>{@render viewer()}{/if}
</div>
{#if $mobile}<Drawer show={drawerOpen} className="h-full" onRequestClose={close}
		><div
			class="h-full"
			role="dialog"
			aria-modal="true"
			aria-label={$i18n.t('File preview')}
			tabindex="-1"
			use:trapFocus
		>
			{@render viewer()}
		</div></Drawer
	>{/if}

{#snippet sidebar()}
	<div class="flex h-full min-h-0 w-full flex-col">
		<div class="flex shrink-0 items-center p-1.5">
			<Search className="mx-1 size-3.5 shrink-0 text-gray-400" /><input
				aria-label={$i18n.t('Search Collection')}
				placeholder={$i18n.t('Search Collection')}
				bind:value={inputQuery}
				class="h-7 min-w-0 flex-1 bg-transparent px-1 text-xs outline-none"
				on:input={() => {
					clearTimeout(debounce);
					debounce = setTimeout(() => (query = inputQuery.trim()), 300);
				}}
			/>
			<Dropdown align="end"
				><button
					type="button"
					aria-label={$i18n.t('Filter and sort')}
					class="flex h-7 w-6 shrink-0 items-center justify-center px-1 text-gray-500"
					><AdjustmentsHorizontal className="size-3.5" /></button
				>
				<div slot="content">
					<DropdownMenu className="min-w-44">
						<button
							type="button"
							role="menuitemcheckbox"
							aria-checked={includeContent}
							on:click={() => (includeContent = !includeContent)}
							>{includeContent ? '✓ ' : ''}{$i18n.t('Search file content')}</button
						>
						<hr class="border-gray-100 dark:border-gray-800" />
						{#each [{ value: null, label: 'All' }, { value: 'created', label: 'Created by you' }, { value: 'shared', label: 'Shared with you' }] as option}<button
								type="button"
								role="menuitemradio"
								aria-checked={viewOption === option.value}
								on:click={() => (viewOption = option.value)}
								>{viewOption === option.value ? '✓ ' : ''}{$i18n.t(option.label)}</button
							>{/each}
						<hr class="border-gray-100 dark:border-gray-800" />
						{#each [{ value: 'name', label: 'Name' }, { value: 'created_at', label: 'Created' }, { value: 'updated_at', label: 'Updated' }] as option}<button
								type="button"
								role="menuitemradio"
								aria-checked={sortKey === option.value}
								on:click={() => (sortKey = option.value)}
								>{sortKey === option.value ? '✓ ' : ''}{$i18n.t(option.label)}</button
							>{/each}
						<button
							type="button"
							on:click={() => (direction = direction === 'asc' ? 'desc' : 'asc')}
							>{$i18n.t(direction === 'asc' ? 'Ascending' : 'Descending')}</button
						>
					</DropdownMenu>
				</div></Dropdown
			>
			{#if knowledge.write_access}<AddContentMenu
					onUpload={(data: { type: string }) => {
						if (data.type === 'new_directory') {
							query = '';
							tree.createDirectory();
						} else onUpload(data.type, null, []);
					}}
					onSync={() => guard(onSync)}
					onReset={() => guard(onReset)}
				/>{/if}
		</div>
		{#if syncing}<p class="px-3 py-1 text-xs text-gray-500">{syncing}</p>{/if}
		<Files
			bind:this={tree}
			{knowledge}
			{transfers}
			bind:query
			{includeContent}
			{viewOption}
			{sortKey}
			{direction}
			selectedFileId={selected?.id || null}
			onSelect={select}
			{onUpload}
			onChanged={changed}
			{guard}
		/>
	</div>
{/snippet}
{#snippet viewer()}
	{#if selected}{#key selected.id}<FileViewer
				file={selected}
				writeAccess={!!knowledge.write_access && !syncing}
				mobile={$mobile}
				bind:state
				bind:saving
				onClose={close}
				onSaved={refresh}
			/>{/key}
	{:else}<div
			class="flex min-w-0 flex-1 items-center justify-center bg-white text-xs text-gray-400 dark:bg-gray-900"
		>
			{$i18n.t('Select a file to preview')}
		</div>{/if}
{/snippet}
