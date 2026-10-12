<script lang="ts">
	import { getContext } from 'svelte';
	import { user } from '$lib/stores';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ProfileImage from '$lib/components/chat/Messages/ProfileImage.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	let showActions = false;

	export let entry: {
		id: string;
		commit_message?: string | null;
		created_at?: number;
		user_id?: string;
		user?: { id?: string; name?: string } | null;
	} | null = null;
	export let status = '';
	export let selected = false;
	export let onSelect: () => void;
	export let onDelete: (() => void) | undefined = undefined;
	export let deleteDisabledReason = '';
	const i18n = getContext<any>('i18n');
	$: authorId = entry?.user?.id || entry?.user_id;
	$: message = entry?.commit_message || entry?.id.slice(0, 7) || status;
	$: author =
		entry?.user?.name ||
		($user?.id === authorId ? $user.name : authorId ? $i18n.t('Unknown user') : '');
	$: date = entry?.created_at ? new Date(entry.created_at * 1000) : null;
</script>

<div
	class="group flex h-[1.6875rem] w-full items-center rounded-xl hover:bg-gray-50/60 dark:hover:bg-gray-800/60"
>
	<button
		type="button"
		role="menuitemradio"
		aria-label={status || message}
		aria-checked={selected}
		class="flex h-full min-w-0 flex-1 items-center gap-2 rounded-xl px-2 text-left"
		title={entry
			? `${entry.id}${date ? ` · ${date.toLocaleString($i18n.language)}` : ''}`
			: undefined}
		on:click={onSelect}
	>
		<Tooltip as="span" className="flex shrink-0" content={author} allowHTML={false}>
			<ProfileImage
				src={authorId ? `/api/v1/users/${authorId}/profile/image` : '/user.png'}
				className="size-4 shrink-0 rounded-full!"
			/>
		</Tooltip>
		<Tooltip as="span" className="block min-w-0 flex-1" content={message} allowHTML={false}>
			<span class="block truncate text-xs">{message}</span>
		</Tooltip>
		{#if status && entry}<span class="shrink-0 text-[0.625rem] text-gray-400">{status}</span>{/if}
		{#if selected}<Check className="size-3.5 shrink-0 text-blue-500" />{/if}
	</button>
	{#if onDelete || deleteDisabledReason}
		<Dropdown bind:show={showActions} align="end">
			<button
				type="button"
				aria-label={$i18n.t('More Options')}
				class="mr-0.5 flex size-6 shrink-0 items-center justify-center rounded-lg text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
				><EllipsisHorizontal className="size-3.5" /></button
			>
			<div slot="content">
				<DropdownMenu className="min-w-32">
					<button
						type="button"
						disabled={!!deleteDisabledReason}
						class="disabled:cursor-not-allowed disabled:opacity-40"
						title={deleteDisabledReason || undefined}
						on:click={() => {
							showActions = false;
							onDelete?.();
						}}><GarbageBin className="size-3.5" /><span>{$i18n.t('Delete')}</span></button
					>
				</DropdownMenu>
			</div>
		</Dropdown>
	{/if}
</div>
