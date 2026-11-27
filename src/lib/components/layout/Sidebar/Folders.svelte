<script lang="ts">
	import { getContext, createEventDispatcher, tick } from 'svelte';
	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	const dispatch = createEventDispatcher();

	import { toast } from 'svelte-sonner';

	import { machines, settings, type FolderListSection } from '$lib/stores';
	import { updateFolderDetails } from '$lib/stores/folderStates';
	import { updateFolderParentIdById } from '$lib/apis/folders';
	import { sortFolders } from '$lib/utils/folders';
	import { placeInSection, saveFolderListSettings } from '$lib/utils/folderSections';

	import RecursiveFolder, {
		getDraggedSectionId,
		setDraggedSectionId
	} from './RecursiveFolder.svelte';
	import SidebarSection from './Section.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EditPencilIcon from './icons/EditPencil.svelte';
	import MoreHorizontalIcon from './icons/MoreHorizontal.svelte';
	import GarbageBinIcon from '../../icons/GarbageBin.svelte';

	export let folderRegistry = {};

	export let folders: Record<string, any> = {};
	export let shiftKey = false;
	/** A section whose name opens ready to type, such as a new one. */
	export let renamingSectionId: string | null = null;

	export let onDelete: (folderId: string) => void = () => {};
	export let onFolderUnreadCounts: (counts: Record<string, number>) => void = () => {};

	type FolderGroup = { key: string; label: string; ids: string[] };

	let rootOrder: string[] = [];
	/** Where a dragged section would land beside another section. */
	let sectionDrop: { id: string; position: 'before' | 'after' } | null = null;

	$: roots = Object.values(folders).filter((f) => {
		if (!f.name) return false;
		// Root folder: no parent, or shared folder whose parent isn't in our folders
		if (f.shared) {
			return !f.parent_id || !folders[f.parent_id];
		}
		return f.parent_id === null;
	});
	$: rootIds = new Set(roots.map((f) => f.id));
	$: rootOrder = sortFolders(roots, $settings?.folderOrder?.root).map((f) => f.id);

	// Filters only hide folders; the saved order keeps them all
	$: owner = $settings?.folderOwner ?? 'all';
	// A machine that no longer has folders here filters nothing
	$: machine =
		$settings?.folderMachine === 'none' ||
		roots.some((f) => f.machine_id && f.machine_id === $settings?.folderMachine)
			? $settings?.folderMachine
			: 'all';
	$: visible = sortFolders(roots, $settings?.folderOrder?.root, $settings?.folderSort).filter(
		(f) =>
			(owner === 'all' || (owner === 'shared') === !!f.shared) &&
			(machine === 'all' || (machine === 'none' ? !f.machine_id : f.machine_id === machine))
	);

	$: sections = $settings?.folderSections ?? [];
	$: sectionIds = new Set(sections.map((section) => section.id));
	$: inSection = (id: string) => sections.some((section) => section.folderIds.includes(id));
	$: sectionFolderIds = Object.fromEntries(
		sections.map((section) => [
			section.id,
			visible.filter((f) => section.folderIds.includes(f.id)).map((f) => f.id)
		])
	);
	$: unsectioned = visible.filter((f) => !inSection(f.id));
	$: unsectionedIds = new Set(unsectioned.map((f) => f.id));

	const indexIn = (order: string[], id: string) => {
		const index = order.indexOf(id);
		return index === -1 ? order.length : index;
	};
	// Top-level folders and sections share one saved order; ones missing from it go last
	$: topOrder = [...rootOrder, ...sections.map((section) => section.id)].sort(
		(a, b) =>
			indexIn($settings?.folderOrder?.root ?? [], a) -
			indexIn($settings?.folderOrder?.root ?? [], b)
	);
	$: orderedSections = [...sections].sort(
		(a, b) => indexIn(topOrder, a.id) - indexIn(topOrder, b.id)
	);

	// Grouping takes over from sections: it groups every top-level folder and hides the
	// sections until it's off again. Grouping by machine with no machine folders left groups nothing.
	$: groupBy =
		$settings?.folderGroup === 'machine' && !roots.some((f) => f.machine_id)
			? 'none'
			: ($settings?.folderGroup ?? 'none');
	const groupKey = (folder: any, by: string): string =>
		by === 'owner'
			? folder.shared
				? folder.user_id
				: ''
			: by === 'machine'
				? (folder.machine_id ?? '')
				: '';
	const buildGroups = (
		list: any[],
		by: string,
		machineList: typeof $machines,
		t: typeof $i18n.t
	): FolderGroup[] => {
		if (by === 'none') return [{ key: '', label: '', ids: list.map((f) => f.id) }];
		const groups = new Map<string, FolderGroup>();
		for (const folder of list) {
			const key = groupKey(folder, by);
			if (!groups.has(key)) {
				const label =
					by === 'owner'
						? key
							? folder.owner_name
							: t('Yours')
						: key
							? (machineList ?? []).find((m) => m.id === key)?.name || key
							: t('No machine');
				groups.set(key, { key, label, ids: [] });
			}
			groups.get(key)!.ids.push(folder.id);
		}
		// Yours, or no machine, first; the rest by name
		return [...groups.values()].sort((a, b) =>
			!a.key ? -1 : !b.key ? 1 : a.label.localeCompare(b.label)
		);
	};
	$: groups = buildGroups(groupBy === 'none' ? unsectioned : visible, groupBy, $machines, $i18n.t);

	// Sections mix in among folders only when nothing else decides the order
	$: mixed = groupBy === 'none' && ($settings?.folderSort ?? 'manual') === 'manual';
	$: topItems = mixed ? topOrder.filter((id) => sectionIds.has(id) || unsectionedIds.has(id)) : [];

	// A section goes beside top-level folders outside sections, when mixed. When grouped, a
	// top-level folder only goes beside folders of its group, as a drag can't change a
	// folder's owner or machine.
	$: canReorder = (id: string, targetId: string) =>
		sectionIds.has(id)
			? mixed && unsectionedIds.has(targetId)
			: !rootIds.has(targetId) ||
				groupKey(folders[id], groupBy) === groupKey(folders[targetId], groupBy);

	const place = (order: string[], id: string, targetId: string, position: 'before' | 'after') => {
		const next = order.filter((item) => item !== id);
		next.splice(next.indexOf(targetId) + (position === 'after' ? 1 : 0), 0, id);
		return next;
	};

	const moveFolder = async (id: string, parentId: string | null) => {
		const res = await updateFolderParentIdById(localStorage.token, id, parentId).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (!res) return false;

		updateFolderDetails(id, res);
		dispatch('update');
		return true;
	};

	const onReorder = async (id: string, targetId: string, position: 'before' | 'after') => {
		if (sectionIds.has(id)) {
			await saveFolderListSettings({
				folderOrder: { ...$settings?.folderOrder, root: place(topOrder, id, targetId, position) }
			});
			return;
		}

		// A shared folder only moves among top-level folders; the owner's tree stays as it is
		const parentId = folders[targetId].shared ? null : folders[targetId].parent_id;

		if (!folders[id].shared && folders[id].parent_id !== parentId) {
			if (!(await moveFolder(id, parentId))) return;
		}

		const key = parentId ?? 'root';
		const order = place(
			parentId === null
				? topOrder
				: sortFolders(
						Object.values(folders).filter((f) => f.parent_id === parentId && !f.shared),
						$settings?.folderOrder?.[key]
					).map((f) => f.id),
			id,
			targetId,
			position
		);

		// A top-level folder joins the section of the folder it's placed beside; while
		// grouped, sections are hidden and keep their folders
		const targetSection = sections.find((section) => section.folderIds.includes(targetId));
		await saveFolderListSettings({
			folderOrder: { ...$settings?.folderOrder, [key]: order },
			...(groupBy === 'none' && {
				folderSections: placeInSection(
					sections,
					id,
					parentId === null ? targetSection?.id : undefined
				)
			})
		});
	};

	const addToSection = async (id: string, sectionId: string) => {
		if (!folders[id]) return;
		// A folder of yours inside another one moves to the top level; shared ones never move
		if (!folders[id].shared && folders[id].parent_id !== null) {
			if (!(await moveFolder(id, null))) return;
		}
		await saveFolderListSettings({ folderSections: placeInSection(sections, id, sectionId) });
	};

	const renameSection = (id: string, name: string) =>
		saveFolderListSettings({
			folderSections: sections.map((section) =>
				section.id === id ? { ...section, name } : section
			)
		});

	const getSectionDrop = (e: DragEvent, id: string) => {
		const dragged = getDraggedSectionId();
		if (!dragged || dragged === id) return null;
		const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
		return { id, position: e.clientY - rect.top < rect.height / 2 ? 'before' : 'after' } as const;
	};

	const onItemMove = (e) => {
		if (e.originFolderId) {
			folderRegistry[e.originFolderId]?.setFolderItems();
		}
	};
</script>

{#snippet folderList(ids: string[])}
	{#if ids.length > 0}
		<div role="list">
			{#each ids as folderId (folderId)}
				{@render folderItem(folderId)}
			{/each}
		</div>
	{/if}
{/snippet}

{#snippet folderItem(folderId: string)}
	<RecursiveFolder
		className=""
		bind:folderRegistry
		{folders}
		{folderId}
		{shiftKey}
		{onDelete}
		{onItemMove}
		{onReorder}
		{canReorder}
		{onFolderUnreadCounts}
		on:import={(e) => {
			dispatch('import', e.detail);
		}}
		on:update={(e) => {
			dispatch('update', e.detail);
		}}
		on:change={(e) => {
			dispatch('change', e.detail);
		}}
	/>
{/snippet}

{#snippet sectionItem(section: FolderListSection)}
	<!-- A dragged section lands before or after this one; folders still drop inside. -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		class="relative -mx-1.5"
		on:dragover|capture={(e) => {
			sectionDrop = getSectionDrop(e, section.id);
			if (!sectionDrop) return;
			e.preventDefault();
			e.stopPropagation();
		}}
		on:dragleave={(e) => {
			if (!e.currentTarget.contains(e.relatedTarget as Node)) sectionDrop = null;
		}}
		on:drop|capture={(e) => {
			const drop = getSectionDrop(e, section.id);
			sectionDrop = null;
			if (!drop) return;
			e.preventDefault();
			e.stopPropagation();
			onReorder(getDraggedSectionId()!, section.id, drop.position);
		}}
	>
		{#if sectionDrop?.id === section.id}
			<div
				class="pointer-events-none absolute inset-x-1 z-50 h-px rounded-[1px] bg-base-800/20 dark:bg-base-200/20 {sectionDrop.position ===
				'before'
					? 'top-0'
					: 'bottom-0'}"
			></div>
		{/if}

		<SidebarSection
			id="sidebar-folder-section-{section.id}"
			name={section.name}
			sortHandle={false}
			editing={section.id === renamingSectionId}
			onRename={(name) => renameSection(section.id, name)}
			onHeadingDragStart={(e) => {
				e.dataTransfer?.setData('text/plain', JSON.stringify({ type: 'section', id: section.id }));
				e.dataTransfer?.setData('application/x-open-webui-drag', '');
				setDraggedSectionId(section.id);
			}}
			onHeadingDragEnd={() => {
				setDraggedSectionId(null);
				sectionDrop = null;
			}}
			on:drop={(e) => {
				if (e.detail.type === 'folder') addToSection(e.detail.id, section.id);
			}}
		>
			<svelte:fragment slot="action">
				<Dropdown align="start" closeOnSelect>
					<Tooltip content={$i18n.t('More')}>
						<button
							type="button"
							class="flex items-center justify-center w-7 h-7 rounded-lg text-base-300 hover:text-base-500 dark:text-base-600 dark:hover:text-base-400 transition-colors duration-100"
							aria-label={$i18n.t('More')}
						>
							<MoreHorizontalIcon className="size-3.5" strokeWidth="2" />
						</button>
					</Tooltip>

					<div slot="content">
						<DropdownMenu className="min-w-[10.625rem]">
							<button
								type="button"
								on:click={async () => {
									renamingSectionId = null;
									await tick();
									renamingSectionId = section.id;
								}}
							>
								<EditPencilIcon className="size-3.5" />
								{$i18n.t('Rename')}
							</button>
							<!-- Its folders go back among the others -->
							<button
								type="button"
								on:click={() =>
									saveFolderListSettings({
										folderSections: sections.filter((item) => item.id !== section.id)
									})}
							>
								<GarbageBinIcon className="size-3.5" />
								{$i18n.t('Delete')}
							</button>
						</DropdownMenu>
					</div>
				</Dropdown>
			</svelte:fragment>

			{@render folderList(sectionFolderIds[section.id] ?? [])}
		</SidebarSection>
	</div>
{/snippet}

{#if mixed}
	<div role="list">
		{#each topItems as id (id)}
			{@const section = sections.find((item) => item.id === id)}
			{#if section}
				{@render sectionItem(section)}
			{:else}
				{@render folderItem(id)}
			{/if}
		{/each}
	</div>
{:else}
	{#each groups as group (group.key)}
		{#if groupBy === 'none'}
			{@render folderList(group.ids)}
		{:else}
			<!-- Looks and collapses like a section; its folders still take their own drops -->
			<SidebarSection
				id="sidebar-folder-group-{groupBy}-{group.key || 'none'}"
				name={group.label}
				className="-mx-1.5"
				sortHandle={false}
				dragAndDrop={false}
			>
				{@render folderList(group.ids)}
			</SidebarSection>
		{/if}
	{/each}

	{#if groupBy === 'none'}
		{#each orderedSections as section (section.id)}
			{@render sectionItem(section)}
		{/each}
	{/if}
{/if}
