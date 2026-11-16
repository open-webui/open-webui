<script lang="ts">
	import { getContext } from 'svelte';
	import type { WorkspaceChat } from '$lib/utils/folders';
	import { tagDot, type FolderTag } from '$lib/utils/tags';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import TagPicker from '$lib/components/chat/TagPicker.svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');

	export let chat: WorkspaceChat;
	export let max = 2;
	export let onChange: () => Promise<void> = async () => {};

	let show = false;
	let assigned: FolderTag[] = [];
	$: assigned = chat.tags ?? [];
</script>

{#snippet pills()}
	{#each assigned.slice(0, max) as tag (tag.id)}
		<span
			class="inline-flex h-5 min-w-0 max-w-28 items-center gap-1.5 rounded-full border border-gray-100/60 pl-2 pr-1.25 text-[0.6875rem] text-gray-600 dark:border-gray-800/60 dark:text-gray-300"
			title={tag.name}
		>
			<span class="size-1.5 shrink-0 rounded-full {tagDot(tag)}"></span>
			<span class="truncate">{tag.name}</span>
		</span>
	{/each}
	{#if assigned.length > max}
		<span
			class="inline-flex h-5 shrink-0 items-center rounded-full border border-gray-100/60 px-1.5 text-[0.6875rem] text-gray-500 dark:border-gray-800/60 dark:text-gray-400"
			title={assigned
				.slice(max)
				.map((tag) => tag.name)
				.join(', ')}>+{assigned.length - max}</span
		>
	{/if}
{/snippet}

{#if chat.can_edit_tags}
	<Dropdown bind:show align="end">
		<button
			type="button"
			class="flex min-w-0 items-center gap-1 rounded-full"
			aria-label={$i18n.t('Edit tags for {{title}}', { title: chat.title })}
			title={assigned.length ? undefined : $i18n.t('Add tags')}
		>
			{@render pills()}
			{#if !assigned.length}
				<span
					class="tag-add flex h-5 items-center gap-1 rounded-full border border-dashed border-gray-200 px-1.5 text-[0.6875rem] text-gray-400 transition-colors hover:border-gray-300 hover:text-gray-600 dark:border-gray-700 dark:text-gray-500 dark:hover:text-gray-300"
					class:open={show}
				>
					<Plus className="size-2.5" strokeWidth="2" />{$i18n.t('Tag')}
				</span>
			{/if}
		</button>

		<DropdownMenu slot="content" className="w-52 text-gray-700 dark:text-gray-200">
			<TagPicker
				chatId={chat.id}
				{assigned}
				onChange={async (next) => {
					assigned = next;
					await onChange();
				}}
			/>
		</DropdownMenu>
	</Dropdown>
{:else if assigned.length}
	<div class="flex min-w-0 items-center gap-1">{@render pills()}</div>
{/if}

<style>
	@media (hover: hover) {
		.tag-add {
			opacity: 0;
		}
		.tag-add.open,
		:global([data-folder-item]:hover) .tag-add,
		:global([data-folder-item]:focus-within) .tag-add {
			opacity: 1;
		}
	}
</style>
