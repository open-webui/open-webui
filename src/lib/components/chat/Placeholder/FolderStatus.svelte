<script lang="ts">
	import { getContext } from 'svelte';
	import type { Readable } from 'svelte/store';
	import type { FolderStatus, StatusDef, WorkspaceChat } from '$lib/utils/folders';
	import { statusKey } from '$lib/utils/folders';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import Icon from '$lib/components/chat/FileNav/Icon.svelte';
	import StatusIcon from './FolderStatusIcon.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { formatElapsed } from '$lib/utils';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	const defs = getContext<Readable<StatusDef[]> | undefined>('folder-statuses');
	const manage = getContext<Readable<(() => void) | null> | undefined>('folder-statuses-manage');

	export let chat: WorkspaceChat;
	export let disabled = false;
	export let onChange: (chat: WorkspaceChat, status: FolderStatus) => Promise<void>;

	$: current = statusKey(chat.status);
	$: label = $defs?.find((item) => item.id === current)?.name ?? $i18n.t('No status');
	// "In progress · 3 days": how long this chat has been in its status.
	$: tip = chat.status_since
		? `${label} · ${formatElapsed(chat.status_since, $i18n.language)}`
		: label;
</script>

<Tooltip content={tip} placement="top-start" as="span" className="flex shrink-0">
	{#if chat.can_edit_status}
		<Dropdown align="start" closeOnSelect>
			<button
				type="button"
				class="flex size-5 shrink-0 items-center justify-center rounded-md transition-colors hover:bg-gray-100 disabled:opacity-50 dark:hover:bg-gray-800"
				{disabled}
				aria-label={$i18n.t('Status for {{title}}: {{status}}', { title: chat.title, status: tip })}
			>
				<StatusIcon status={current} />
			</button>
			<DropdownMenu slot="content" className="w-44">
				{#each $defs ?? [] as status (status.id)}
					<button
						type="button"
						role="menuitemradio"
						aria-checked={current === status.id}
						{disabled}
						on:click={() => {
							if (current !== status.id) void onChange(chat, status.id);
						}}
					>
						<StatusIcon status={status.id} />
						<span class="min-w-0 flex-1 truncate text-left">{status.name}</span>
						{#if current === status.id}<Check className="size-3! shrink-0" />{/if}
					</button>
				{/each}
				{#if $manage}
					<hr class="border-gray-50/30 dark:border-gray-800/30" />
					<button type="button" on:click={() => $manage?.()}>
						<Icon name="pencil" size={14} />{$i18n.t('Edit statuses…')}
					</button>
				{/if}
			</DropdownMenu>
		</Dropdown>
	{:else}
		<span class="flex size-5 shrink-0 items-center justify-center">
			<StatusIcon status={current} />
		</span>
	{/if}
</Tooltip>
