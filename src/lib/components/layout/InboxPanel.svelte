<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import dayjs from 'dayjs';
	import { refreshInboxCount, setInboxCount } from '$lib/stores/inbox';
	import {
		inboxRequest,
		inboxLabels,
		type InboxItem,
		type InboxPage
	} from '$lib/apis/notifications/inbox';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Bell from '$lib/components/icons/Bell.svelte';
	import ProfileImage from '$lib/components/chat/Messages/ProfileImage.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	export let active = false;
	let mounted = false;
	export let onClose: () => void;
	export let onSelect: (item: InboxItem) => Promise<void>;
	const i18n = getContext<any>('i18n');
	let items: InboxItem[] = [];
	let cursor: string | null = null;
	let loading = true;
	let loaded = false;
	let loadingMore = false;
	let error = '';
	let selecting: string | null = null;
	let acknowledgedAt: string | undefined;
	let opened = false;
	let alive = true;
	let version = 0;
	let refreshPending = false;
	const dateLabel = (timestamp: string) => {
		const date = dayjs(Number(timestamp) / 1e6);
		return date.isSame(dayjs(), 'day')
			? 'Today'
			: date.isAfter(dayjs().subtract(7, 'day'))
				? 'This week'
				: 'Earlier';
	};
	const shortTime = (timestamp: string) => {
		const date = dayjs(Number(timestamp) / 1e6);
		const minutes = Math.max(0, dayjs().diff(date, 'minute'));
		if (minutes < 1) return $i18n.t('Now');
		if (minutes >= 7 * 24 * 60) return date.locale($i18n.language).format('MMM D');
		const unit = minutes < 60 ? 'minute' : minutes < 24 * 60 ? 'hour' : 'day';
		const value = unit === 'minute' ? minutes : Math.floor(minutes / (unit === 'hour' ? 60 : 1440));
		return new Intl.NumberFormat($i18n.language, {
			style: 'unit',
			unit,
			unitDisplay: 'narrow'
		}).format(value);
	};
	const load = async (more = false) => {
		const request = ++version;
		loading = true;
		loadingMore = more;
		try {
			const result = await inboxRequest<InboxPage>(
				!opened ? '/open' : more && cursor ? `?cursor=${encodeURIComponent(cursor)}` : '',
				!opened ? 'POST' : 'GET'
			);
			if (!alive || request !== version) return;
			acknowledgedAt = result.acknowledged_at ?? acknowledgedAt;
			const old = new Map(items.map((item) => [item.id, item]));
			const next = result.items.map((item) => ({
				...item,
				is_new:
					item.is_new ??
					(item.seen_at === null || item.seen_at === acknowledgedAt || old.get(item.id)?.is_new)
			}));
			items = more ? [...items, ...next.filter((item) => !old.has(item.id))] : next;
			cursor = result.next_cursor;
			if (!opened) {
				setInboxCount(result.count ?? 0);
				void refreshInboxCount();
			}
			opened = true;
			loaded = true;
			error = '';
		} catch (e) {
			if (alive && request === version) error = String(e instanceof Error ? e.message : e);
		} finally {
			if (alive && request === version) {
				loading = false;
				loadingMore = false;
				if (refreshPending && opened) {
					refreshPending = false;
					void load();
				}
			}
		}
	};
	export function refresh() {
		if (!active) return;
		if (loading) refreshPending = true;
		else if (opened) void load();
	}
	const select = async (item: InboxItem) => {
		if (selecting) return;
		selecting = item.id;
		try {
			await onSelect(item);
		} catch (e) {
			if (alive) error = String(e instanceof Error ? e.message : e);
		} finally {
			if (alive) selecting = null;
		}
	};
	const keydown = (event: KeyboardEvent) => {
		if (
			active &&
			event.key === 'Escape' &&
			event.target instanceof Element &&
			event.target.closest('#sidebar-notifications, [data-inbox-trigger]')
		) {
			event.preventDefault();
			event.stopPropagation();
			onClose();
			document.querySelector<HTMLElement>('[data-inbox-trigger]')?.focus();
		}
	};
	onMount(() => {
		mounted = true;
	});
	$: if (mounted && active) {
		opened = false;
		refreshPending = false;
		void load();
	}
	onDestroy(() => {
		alive = false;
	});
</script>

<svelte:window on:keydown={keydown} />

<section
	id="sidebar-notifications"
	aria-label={$i18n.t('Notifications')}
	class="flex min-h-0 flex-1 flex-col pt-2.5"
	style:display={active ? undefined : 'none'}
>
	<div
		class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-1.5 pb-3"
		class:flex={!items.length}
		class:flex-col={!items.length}
	>
		{#if error}<div role="alert" class="px-2.5 py-2 text-xs text-red-500">
				<p>{error}</p>
				<button
					type="button"
					class="mt-1 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
					on:click={() => load()}>{$i18n.t('Retry')}</button
				>
			</div>{/if}
		{#each items as item, index (item.id)}
			{#if index === 0 || dateLabel(item.created_at) !== dateLabel(items[index - 1].created_at)}<div
					class="px-2.5 pt-3 pb-1.5 text-[0.6875rem] font-normal leading-4 text-gray-500 dark:text-gray-400"
				>
					{$i18n.t(dateLabel(item.created_at))}
				</div>{/if}
			<button
				type="button"
				class="my-0.5 flex w-full items-start gap-2.5 rounded-lg px-2 py-2 text-start font-normal hover:bg-gray-100 dark:hover:bg-gray-900 transition-colors duration-75 disabled:opacity-60"
				disabled={!!selecting}
				on:click={() => select(item)}
			>
				<span class="sr-only">{$i18n.t(item.read_at ? 'Read' : 'Unread')}</span>
				<span class="relative mt-0.5 flex size-5 shrink-0 items-center justify-center">
					{#if item.actor}
						<ProfileImage
							src={`${WEBUI_API_BASE_URL}/users/${encodeURIComponent(item.actor.id)}/profile/image`}
							className="size-5 rounded-full!"
						/>
					{:else}
						<Bell className="size-3.5 text-gray-500 dark:text-gray-400" />
					{/if}
					{#if item.is_new}
						<span
							class="absolute -bottom-0.5 -end-0.5 size-1.5 rounded-full bg-sky-500 ring-2 ring-gray-50 dark:bg-sky-400 dark:ring-gray-950"
							aria-label={$i18n.t('New')}
						></span>
					{/if}
				</span>
				<div class="min-w-0 flex-1">
					<div class="flex items-start gap-1.5">
						<span
							class="min-w-0 flex-1 line-clamp-2 break-words text-xs leading-[1.125rem] text-gray-800 dark:text-gray-200"
						>
							{$i18n.t(inboxLabels[item.event_type] ?? 'Notification', {
								name: item.actor?.name ?? $i18n.t('Unknown User')
							})}
						</span>
						<time
							datetime={dayjs(Number(item.created_at) / 1e6).toISOString()}
							title={dayjs(Number(item.created_at) / 1e6)
								.locale($i18n.language)
								.format('LLLL')}
							aria-label={dayjs(Number(item.created_at) / 1e6)
								.locale($i18n.language)
								.fromNow()}
							class="shrink-0 text-[0.625rem] leading-[1.125rem] text-gray-500 dark:text-gray-400"
						>
							{shortTime(item.created_at)}
						</time>
					</div>
					{#if item.title}
						<div
							class="mt-0.5 truncate text-xs leading-[1.125rem] text-gray-600 dark:text-gray-400"
							title={item.title}
						>
							{item.title}
						</div>
					{/if}
					{#if item.preview || item.data.message}
						<div
							class="mt-0.5 {item.resource_type
								? 'line-clamp-1'
								: ''} whitespace-pre-wrap break-words text-xs leading-[1.125rem] text-gray-500 dark:text-gray-400"
						>
							{item.preview || item.data.message}
						</div>
					{/if}
				</div>
			</button>
		{/each}
		{#if loading && !loaded}<div class="flex justify-center p-5">
				<Spinner className="size-5" />
			</div>{:else if !error && !items.length}<p
				class="flex flex-1 items-center justify-center px-4 py-6 text-center text-xs text-gray-500 dark:text-gray-400"
			>
				{$i18n.t('No notifications found.')}
			</p>{:else if cursor}<button
				type="button"
				class="mx-2.5 my-3 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
				disabled={loading}
				on:click={() => load(true)}>{$i18n.t(loadingMore ? 'Loading...' : 'Load more')}</button
			>{:else if items.length}<p
				class="px-4 py-4 text-center text-[0.6875rem] text-gray-400 dark:text-gray-500"
			>
				{$i18n.t('You have reached the end.')}
			</p>{/if}
	</div>
</section>
