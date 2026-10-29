<script lang="ts">
	import { getContext } from 'svelte';
	import type { NotePage } from '$lib/apis/notes';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	export let page: NotePage;
	export let pages: NotePage[];
	export let editable = false;
	export let busy = false;
	export let className = '';
	export let onRename: (page: NotePage) => void;
	export let onDelete: (page: NotePage) => void;
	export let onCreate: (parentId: string | null) => void;
	export let onMoveTo: (page: NotePage) => void;
	export let onMove: (id: string, direction: number) => void;
	export let onCopyLink: (id: string) => void;
	export let onDownload: (id: string, type: string) => void;
	$: siblings = pages.filter((p) => (p.parent_id ?? null) === (page.parent_id ?? null));
	$: index = siblings.findIndex((p) => p.id === page.id);
</script>

<Dropdown align="start" closeOnSelect>
	<button
		class="{className} flex size-5 items-center justify-center rounded-lg text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5"
		disabled={busy}
		aria-label={$i18n.t('Page menu')}><EllipsisHorizontal className="size-3.5" /></button
	>
	<div slot="content">
		<DropdownMenu className="note-tab-options min-w-48 text-sm">
			{#if editable}
				<button class="w-full text-start px-3 py-1.5" on:click={() => onCreate(page.id)}
					>{$i18n.t('Add subpage')}</button
				>
				<button class="w-full text-start px-3 py-1.5" on:click={() => onRename(page)}
					>{$i18n.t('Rename page')}</button
				>
				{#if page.id !== 'main'}
					<button
						class="w-full text-start px-3 py-1.5 disabled:opacity-40"
						disabled={index === 0 || siblings[index - 1]?.id === 'main'}
						on:click={() => onMove(page.id, -1)}>{$i18n.t('Move up')}</button
					>
					<button
						class="w-full text-start px-3 py-1.5 disabled:opacity-40"
						disabled={index === siblings.length - 1}
						on:click={() => onMove(page.id, 1)}>{$i18n.t('Move down')}</button
					>
					<button class="w-full text-start px-3 py-1.5" on:click={() => onMoveTo(page)}
						>{$i18n.t('Move page…')}</button
					>
				{/if}
			{/if}
			<hr class="border-gray-100 dark:border-gray-800" />
			<button class="w-full text-start px-3 py-1.5" on:click={() => onCopyLink(page.id)}
				>{$i18n.t('Copy page link')}</button
			>
			{#each ['md', 'txt', 'pdf'] as format}
				<button class="w-full text-start px-3 py-1.5" on:click={() => onDownload(page.id, format)}
					>{$i18n.t('Download page')} (.{format})</button
				>
			{/each}
			{#if editable && page.id !== 'main'}
				<hr class="border-gray-100 dark:border-gray-800" />
				<button
					class="w-full text-start px-3 py-1.5 disabled:opacity-40"
					disabled={pages.length === 1}
					on:click={() => onDelete(page)}>{$i18n.t('Delete page')}</button
				>
			{/if}
		</DropdownMenu>
	</div>
</Dropdown>
