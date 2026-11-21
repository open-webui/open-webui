<script lang="ts">
	import { getContext } from 'svelte';
	import { WEBUI_NAME } from '$lib/stores';
	import { WEBUI_VERSION } from '$lib/constants';
	import { formatDateDetails, formatElapsedShort, formatShortDate } from '$lib/utils';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n: any = getContext('i18n');

	type RecentChat = {
		id: string;
		title?: string;
		updated_at?: number;
		last_read_at?: number | null;
		active?: boolean;
		pending_approval?: boolean;
	};

	export let chats: RecentChat[] = [];
	// Shown when there are no suggestions either, as the suggestions list would.
	export let showIdentifier = false;

	// "45s", "12m", "3h", "5d" for the last week, then a short date.
	const formatTime = (seconds: number) =>
		Date.now() / 1000 - seconds < 7 * 86400
			? formatElapsedShort(seconds)
			: formatShortDate(seconds, $i18n.language);

	// Same rule as the sidebar: never read, or updated since it was last read.
	const isUnread = (chat: RecentChat) =>
		!chat.active && (chat.last_read_at == null || (chat.updated_at ?? 0) > chat.last_read_at);
</script>

<div class="w-full px-1 text-left">
	<h3 id="recent-chats-heading" class="mb-1 -mx-1 text-xs text-base-400 dark:text-base-500">
		{$i18n.t('chat.placeholder.recentChats')}
	</h3>

	<ul aria-labelledby="recent-chats-heading">
		{#each chats as chat (chat.id)}
			{@const unread = isUnread(chat)}
			<li>
				<a
					href="/c/{chat.id}"
					class="group flex items-center gap-2 h-7 -mx-2 px-2 rounded-lg text-sm transition-colors duration-75 hover:bg-base-50 dark:hover:bg-base-850"
					title={chat.updated_at ? formatDateDetails(chat.updated_at, $i18n.language) : undefined}
				>
					{#if chat.pending_approval}
						<span
							class="size-1.5 shrink-0 rounded-full bg-yellow-500"
							role="status"
							aria-label={$i18n.t('Waiting for approval')}
						></span>
					{:else if chat.active}
						<span class="shrink-0"><Spinner className="size-3" /></span>
					{:else if unread}
						<span class="size-1.5 shrink-0 rounded-full bg-sky-500" aria-hidden="true"></span>
					{/if}
					<span
						dir="auto"
						class="flex-1 min-w-0 truncate transition-colors duration-75 group-hover:text-base-900 dark:group-hover:text-base-100 {unread
							? 'text-base-800 dark:text-base-200'
							: 'text-base-500 dark:text-base-400'}"
					>
						{chat.title}
					</span>
					{#if chat.updated_at}
						<span class="shrink-0 text-xs tabular-nums text-base-400 dark:text-base-600">
							{formatTime(chat.updated_at)}
						</span>
					{/if}
				</a>
			</li>
		{/each}
	</ul>

	{#if showIdentifier}
		<!-- LICENSE covers this Open WebUI footer identifier.
		Do not alter, remove, obscure, or replace it except as LICENSE permits:
		https://docs.openwebui.com/license. -->
		<div class="mt-2 text-xs text-base-600 dark:text-base-400">
			{$WEBUI_NAME} ‧ v{WEBUI_VERSION}
		</div>
	{/if}
</div>
