<script lang="ts">
	import { getContext } from 'svelte';
	import type { Readable } from 'svelte/store';
	import {
		priorityDefs,
		priorityKey,
		type CanEditChat,
		type FolderPriority,
		type WorkspaceChat
	} from '$lib/utils/folders';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import PriorityIcon from './FolderPriorityIcon.svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	const canEdit = getContext<Readable<CanEditChat> | undefined>('folder-can-edit');

	export let chat: WorkspaceChat;
	export let disabled = false;
	export let onChange: (chat: WorkspaceChat, priority: FolderPriority) => Promise<void>;

	let show = false;
	let query = '';

	$: defs = priorityDefs((key) => $i18n.t(key));
	$: current = priorityKey(chat.priority);
	$: label = defs.find((item) => item.id === current)?.name ?? '';
	$: needle = query.trim().toLowerCase();
	$: matches = defs.filter((item) => !needle || item.name.toLowerCase().includes(needle));

	function pick(priority: FolderPriority) {
		show = false;
		query = '';
		if (priority !== current) void onChange(chat, priority);
	}

	// Enter takes the first match.
	function keys(event: KeyboardEvent) {
		if (event.isComposing || event.keyCode === 229) return;
		if (event.key === 'Enter' && matches[0]) {
			event.preventDefault();
			pick(matches[0].id);
		}
	}
</script>

<Tooltip content={label} placement="top-start" as="span" className="flex shrink-0">
	{#if $canEdit?.(chat)}
		<Dropdown bind:show align="start" onOpenChange={() => (query = '')}>
			<button
				type="button"
				class="flex size-5 shrink-0 items-center justify-center rounded-md transition-colors hover:bg-base-100 disabled:opacity-50 dark:hover:bg-base-800"
				{disabled}
				aria-label={$i18n.t('Priority for {{title}}: {{priority}}', {
					title: chat.title,
					priority: label
				})}
			>
				<PriorityIcon priority={current} />
			</button>
			<DropdownMenu slot="content" className="w-48">
				<div class="flex h-[1.6875rem] items-center gap-2 px-2">
					<input
						class="min-w-0 flex-1 bg-transparent text-[0.8125rem] outline-none placeholder:text-base-400 dark:placeholder:text-base-500"
						aria-label={$i18n.t('Set priority to…')}
						placeholder={$i18n.t('Set priority to…')}
						bind:value={query}
						on:keydown={keys}
					/>
				</div>
				<hr class="border-base-50/30 dark:border-base-800/30" />
				{#each matches as item (item.id)}
					<button
						type="button"
						role="menuitemradio"
						aria-checked={current === item.id}
						{disabled}
						on:click={() => pick(item.id)}
					>
						<PriorityIcon priority={item.id} />
						<span class="min-w-0 flex-1 truncate text-left">{item.name}</span>
						{#if current === item.id}<Check className="size-3! shrink-0" />{/if}
					</button>
				{:else}
					<div class="px-2 py-1.5 text-xs text-base-400 dark:text-base-500">
						{$i18n.t('No results')}
					</div>
				{/each}
			</DropdownMenu>
		</Dropdown>
	{:else}
		<span class="flex size-5 shrink-0 items-center justify-center" aria-label={label}>
			<PriorityIcon priority={current} />
		</span>
	{/if}
</Tooltip>
