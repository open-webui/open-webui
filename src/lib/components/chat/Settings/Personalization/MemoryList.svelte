<script
	lang="ts"
	generics="T extends { id: string; content: string; path?: string | null; folder_id?: string | null }"
>
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18n } from 'i18next';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Icon from '$lib/components/chat/FileNav/Icon.svelte';
	import FileTypeIcon from '$lib/components/chat/FileNav/FileTypeIcon.svelte';

	const i18n = getContext<Writable<I18n>>('i18n');

	type Group = { name: string; key: string; groups: Group[]; memories: T[]; count: number };

	export let memories: T[] = [];
	/** Folder names to show beside folder memories; leave empty to show none. */
	export let folderNames: Map<string, string> = new Map();
	/** Keep every group open, e.g. while searching. */
	export let expandAll = false;
	export let onEdit: (memory: T) => void = () => {};
	export let onRemove: (memory: T) => void = () => {};

	let collapsed = new Set<string>();

	const toggle = (key: string) => {
		collapsed.has(key) ? collapsed.delete(key) : collapsed.add(key);
		collapsed = collapsed;
	};

	const buildTree = (items: T[]): Group => {
		const root: Group = { name: '', key: '', groups: [], memories: [], count: 0 };
		for (const memory of items) {
			let group = root;
			for (const name of (memory.path ?? '').split('/').filter(Boolean)) {
				let child = group.groups.find((item) => item.name === name);
				if (!child) {
					const key = group.key ? `${group.key}/${name}` : name;
					child = { name, key, groups: [], memories: [], count: 0 };
					group.groups.push(child);
				}
				child.count++;
				group = child;
			}
			group.memories.push(memory);
		}
		const sort = (group: Group) => {
			group.groups.sort((a, b) => a.name.localeCompare(b.name));
			group.groups.forEach(sort);
		};
		sort(root);
		return root;
	};

	$: tree = buildTree(memories);

	// Row layout from the file browser (FileNav/FileEntryRow.svelte), with the settings tabs' softer hover.
	const rowClass =
		'flex w-full items-center rounded-xl text-left transition-colors duration-75 hover:bg-base-50 dark:hover:bg-base-0/[0.04]';
	const actionClass =
		'flex h-5 w-5 shrink-0 items-center justify-center rounded transition text-base-400 hover:text-base-600 dark:text-base-500 dark:hover:text-base-400 hover:bg-base-50/40 dark:hover:bg-base-0/4';
	const indent = (depth: number) => `${4 + depth * 16}px`;
</script>

{#snippet group(node: Group, depth: number)}
	{#each node.groups as child (child.key)}
		{@const open = expandAll || !collapsed.has(child.key)}
		<li class="min-w-0">
			<button
				type="button"
				class={rowClass}
				aria-expanded={open}
				on:click={() => toggle(child.key)}
			>
				<span
					class="mr-1.5 flex w-3 shrink-0 justify-center text-base-400 dark:text-base-600"
					style="margin-left: {indent(depth)};"
				>
					<Icon name={open ? 'chevron-down' : 'chevron-right'} size={12} strokeWidth={1.5} />
				</span>
				<span class="flex min-w-0 flex-1 items-center gap-1.5 py-1.5 pr-2">
					<FileTypeIcon name={child.name} type="directory" size={14} />
					<span class="flex-1 truncate text-xs text-base-800 dark:text-base-200">{child.name}</span>
					<span class="shrink-0 text-xs text-base-400">{child.count}</span>
				</span>
			</button>
			{#if open}
				<ul class="flex flex-col">
					{@render group(child, depth + 1)}
				</ul>
			{/if}
		</li>
	{/each}

	{#each node.memories as memory (memory.id)}
		<li class="group min-w-0">
			<div class={rowClass}>
				<span class="mr-1.5 w-3 shrink-0" style="margin-left: {indent(depth)};"></span>
				<button
					type="button"
					class="flex min-w-0 flex-1 items-center gap-1.5 py-1.5 pr-2 text-left"
					title={memory.content}
					on:click={() => onEdit(memory)}
				>
					<FileTypeIcon name="memory.md" type="file" size={14} />
					<span class="flex-1 truncate text-xs text-base-800 dark:text-base-200">
						{memory.content.split('\n')[0]}
					</span>
					{#if memory.folder_id && folderNames.has(memory.folder_id)}
						<span class="shrink-0 text-[0.625rem] text-base-400">
							{folderNames.get(memory.folder_id)}
						</span>
					{/if}
				</button>
				<div
					class="mr-1 flex shrink-0 items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100 max-md:opacity-100"
				>
					<Tooltip content={$i18n.t('Edit')}>
						<button
							type="button"
							class={actionClass}
							aria-label={$i18n.t('Edit')}
							on:click={() => onEdit(memory)}
						>
							<Icon name="pencil" size={12} strokeWidth={1.5} />
						</button>
					</Tooltip>
					<Tooltip content={$i18n.t('Delete')}>
						<button
							type="button"
							class={actionClass}
							aria-label={$i18n.t('Delete')}
							on:click={() => onRemove(memory)}
						>
							<Icon name="trash" size={12} strokeWidth={1.5} />
						</button>
					</Tooltip>
				</div>
			</div>
		</li>
	{/each}
{/snippet}

<ul class="flex min-w-0 flex-col">
	{@render group(tree, 0)}
</ul>
