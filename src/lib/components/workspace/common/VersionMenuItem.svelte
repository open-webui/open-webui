<script lang="ts">
	import { getContext } from 'svelte';
	import { user } from '$lib/stores';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ProfileImage from '$lib/components/chat/Messages/ProfileImage.svelte';
	import Check from '$lib/components/icons/Check.svelte';

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
	const i18n = getContext<any>('i18n');
	$: authorId = entry?.user?.id || entry?.user_id;
	$: message = entry?.commit_message || entry?.id.slice(0, 7) || status;
	$: author =
		entry?.user?.name ||
		($user?.id === authorId ? $user.name : authorId ? $i18n.t('Unknown user') : '');
	$: date = entry?.created_at ? new Date(entry.created_at * 1000) : null;
</script>

<button
	type="button"
	role="menuitemradio"
	aria-label={status || message}
	aria-checked={selected}
	class="text-left"
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
