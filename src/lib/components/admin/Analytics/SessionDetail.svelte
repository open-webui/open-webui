<script lang="ts">
	import { getContext, onMount, onDestroy, tick } from 'svelte';
	import dayjs from 'dayjs';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import ProfilePreview from '$lib/components/channel/Messages/Message/ProfilePreview.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import SessionUsageChart from './SessionUsageChart.svelte';
	import SessionWaterfall from './SessionWaterfall.svelte';
	import { modelColor } from './UsageChart.svelte';
	import {
		getSessionTrace,
		type Session,
		type SessionScope,
		type SessionChart,
		type TraceItem,
		type TraceView
	} from '$lib/apis/analytics/sessions';

	export let session: Session;
	export let scope: SessionScope;
	export let modelNames: Record<string, string>;
	export let onClose: () => void;
	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	let items: TraceItem[] = [];
	let expanded = new Set<string>();
	type Row = { item: TraceItem; offset: number; expandable?: boolean; failed?: boolean };
	$: groups = groupItems(items, page);
	$: rows =
		view === 'all'
			? groups.flatMap((group) => [
					group.header,
					...(expanded.has(group.id) ? group.operations : [])
				])
			: items.map((item, index): Row => ({ item, offset: page * 50 + index }));
	function groupItems(items: TraceItem[], page: number) {
		const grouped = new Map<string, { id: string; header: Row; operations: Row[] }>();
		items.forEach((item, index) => {
			let group = grouped.get(item.message_id);
			if (!group) {
				group = {
					id: item.message_id,
					header: {
						item:
							item.index < 0
								? item
								: {
										...item,
										index: -1,
										type: 'response',
										status: null,
										started_at: null,
										ended_at: null,
										duration_seconds: null
									},
						offset: page * 50 + index,
						failed: false
					},
					operations: []
				};
				grouped.set(item.message_id, group);
			}
			group.header.failed ||= item.status === 'failed';
			if (item.index >= 0) group.operations.push({ item, offset: page * 50 + index });
			group.header.expandable = group.operations.length > 0;
		});
		return [...grouped.values()];
	}
	function toggleGroup(id: string) {
		const next = new Set(expanded);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		expanded = next;
	}
	let view: TraceView = 'all';
	let visualization: 'tokens' | 'timeline' = 'tokens';
	let chart: SessionChart | null = null;
	let targetOffset: number | null = null;
	let page = 0;
	let hasMore = false;
	let loading = true;
	let error = false;
	let mounted = false;
	let controller: AbortController;
	let content: HTMLElement;
	$: formatter = new Intl.NumberFormat($i18n.language, {
		notation: 'compact',
		maximumFractionDigits: 1
	});
	$: if (mounted && view && page >= 0) load();

	async function load() {
		controller?.abort();
		expanded = new Set();
		const current = new AbortController();
		controller = current;
		loading = true;
		error = false;
		try {
			const result = await getSessionTrace(
				localStorage.token,
				session.id,
				scope,
				page * 50,
				view,
				current.signal,
				chart === null
			);
			if (!current.signal.aborted) {
				items = result.items;
				hasMore = result.has_more;
				session = result.session;
				if (result.chart) chart = result.chart;
			}
		} catch {
			if (!current.signal.aborted) error = true;
		} finally {
			if (!current.signal.aborted) {
				loading = false;
				await tick();
				if (targetOffset !== null && !error) revealResponse();
				else if (content) content.scrollTop = 0;
			}
		}
	}

	async function revealResponse() {
		const group = groups.find((group) => group.header.offset === targetOffset);
		if (group) expanded = new Set([...expanded, group.id]);
		await tick();
		const row = content?.querySelector<HTMLElement>(`[data-trace-offset="${targetOffset}"]`);
		row?.scrollIntoView({ block: 'nearest' });
		row?.focus({ preventScroll: true });
	}
	async function jumpToResponse(offset: number) {
		targetOffset = offset;
		view = 'all';
		page = Math.floor(offset / 50);
		await tick();
		if (!loading) revealResponse();
	}
	function filterTrace(next: TraceView) {
		targetOffset = null;
		view = next;
		page = 0;
	}

	const label = (item: TraceItem) =>
		item.type === 'response'
			? modelNames[item.model_id || ''] || item.model_id || $i18n.t('Response')
			: item.name ||
				{
					function_call: $i18n.t('Tool call'),
					function_call_output: $i18n.t('Tool result'),
					reasoning: $i18n.t('Reasoning'),
					'open_webui:code_interpreter': $i18n.t('Code interpreter')
				}[item.type || ''] ||
				item.type ||
				$i18n.t('Saved item');
	const status = (item: TraceItem) =>
		({
			completed: $i18n.t('Completed'),
			failed: $i18n.t('Failed'),
			in_progress: $i18n.t('In progress'),
			pending: $i18n.t('Pending'),
			cancelled: $i18n.t('Cancelled'),
			rejected: $i18n.t('Rejected')
		})[item.status || ''] || '';
	const duration = (seconds: number) =>
		seconds < 1
			? `${Math.round(seconds * 1000)}ms`
			: seconds < 60
				? `${seconds.toFixed(1)}s`
				: `${(seconds / 60).toFixed(1)}m`;
	onMount(() => {
		mounted = true;
	});
	onDestroy(() => {
		controller?.abort();
	});
</script>

<section
	aria-label={$i18n.t('Session details')}
	class="flex max-h-[calc(100dvh-6rem)] min-w-0 flex-col text-xs font-normal text-gray-500 dark:text-gray-400"
>
	<div class="flex shrink-0 items-start gap-3 mb-3">
		<h3 class="min-w-0 flex-1 text-sm font-normal text-gray-900 dark:text-gray-100 line-clamp-2">
			{session.title || $i18n.t('Untitled chat')}
		</h3>
		<a
			href={`/c/${encodeURIComponent(session.id)}`}
			target="_blank"
			rel="noopener noreferrer"
			class="shrink-0 py-1 hover:text-gray-900 dark:hover:text-gray-100">{$i18n.t('Open chat')} ↗</a
		>
		<button
			type="button"
			data-close-session
			aria-label={$i18n.t('Close session details')}
			on:click={onClose}
			class="shrink-0 rounded-lg p-1 hover:bg-gray-50 dark:hover:bg-gray-800"
			><XMark className="size-4" /></button
		>
	</div>
	<div
		bind:this={content}
		class="min-h-0 overflow-y-auto overscroll-contain scrollbar-hover"
		data-session-content
	>
		<div class="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-[0.6875rem]">
			{#if session.user_id}
				<ProfilePreview
					user={{ id: session.user_id, name: session.user_name }}
					side="bottom"
					align="start"
					sideOffset={6}
					className="gap-1.75"
				>
					<img
						src={`${WEBUI_API_BASE_URL}/users/${session.user_id}/profile/image`}
						alt=""
						class="size-4 rounded-full object-cover shrink-0"
						loading="lazy"
						on:error={(event) => {
							const image = event.currentTarget as HTMLImageElement;
							if (!image.src.endsWith('/user.png')) image.src = '/user.png';
						}}
					/>
					<span class="block max-w-28 truncate">{session.user_name || $i18n.t('User')}</span>
				</ProfilePreview>
			{:else}<span>{session.user_name || '-'}</span>{/if}
			{#if session.started_at}<span
					>{dayjs
						.unix(session.started_at)
						.locale($i18n.language)
						.format('MMM D, YYYY · HH:mm')}</span
				>{/if}
			{#if session.kind === 'subagent'}<span>{$i18n.t('Sub-agent')}</span>{/if}
		</div>
		<dl class="flex flex-wrap items-baseline gap-x-4 gap-y-1 mb-3">
			<div class="flex gap-1.5">
				<dt>{$i18n.t('Prompts')}</dt>
				<dd class="tabular-nums text-gray-900 dark:text-gray-200">{session.prompts}</dd>
			</div>
			<div class="flex gap-1.5">
				<dt>{$i18n.t('Responses')}</dt>
				<dd class="tabular-nums text-gray-900 dark:text-gray-200">{session.responses}</dd>
			</div>
			{#if session.recorded_responses}<div
					class="flex gap-1.5"
					title={`${session.recorded_responses}/${session.responses} ${$i18n.t('responses with recorded usage')}`}
				>
					<dt>{$i18n.t('Tokens')}</dt>
					<dd class="tabular-nums text-gray-900 dark:text-gray-200">
						{formatter.format(session.tokens)}{session.complete_responses < session.responses
							? '*'
							: ''}
					</dd>
				</div>{/if}
			{#if session.cache_read != null}<div class="flex gap-1.5">
					<dt>{$i18n.t('Cache read')}</dt>
					<dd class="tabular-nums text-gray-900 dark:text-gray-200">
						{formatter.format(session.cache_read)}
					</dd>
				</div>{/if}
			{#if session.cache_write != null}<div class="flex gap-1.5">
					<dt>{$i18n.t('Cache write')}</dt>
					<dd class="tabular-nums text-gray-900 dark:text-gray-200">
						{formatter.format(session.cache_write)}
					</dd>
				</div>{/if}
		</dl>
		<div
			class="flex items-center gap-3 mb-2"
			role="group"
			aria-label={$i18n.t('Session visualization')}
		>
			{#each [{ id: 'tokens', label: $i18n.t('Tokens') }, { id: 'timeline', label: $i18n.t('Timeline') }] as option}
				<button
					type="button"
					aria-pressed={visualization === option.id}
					class="py-1 hover:text-gray-900 dark:hover:text-gray-100"
					class:text-gray-900={visualization === option.id}
					class:dark:text-gray-100={visualization === option.id}
					on:click={() => (visualization = option.id as typeof visualization)}
					>{option.label}</button
				>
			{/each}
		</div>
		{#if visualization === 'tokens'}
			{#if chart?.usage.some((bar) => bar.recorded > 0)}
				<SessionUsageChart usage={chart.usage} onSelect={jumpToResponse} />
			{:else if !loading && !error}
				<p class="mb-4 text-[0.6875rem] text-gray-400 dark:text-gray-500">
					{$i18n.t('Token usage not recorded')}
				</p>
			{/if}
		{:else if !loading && !error}
			<SessionWaterfall {items} {page} {label} {status} />
		{/if}
		<div class="flex items-center gap-3 mb-2" aria-label={$i18n.t('Trace filter')}>
			{#each [{ id: 'all', label: $i18n.t('All') }, { id: 'tools', label: $i18n.t('Tools') }, { id: 'errors', label: $i18n.t('Errors') }] as filter}
				<button
					type="button"
					aria-pressed={view === filter.id}
					class="py-1 hover:text-gray-900 dark:hover:text-gray-100"
					class:text-gray-900={view === filter.id}
					class:dark:text-gray-100={view === filter.id}
					on:click={() => filterTrace(filter.id as TraceView)}>{filter.label}</button
				>
			{/each}
		</div>
		<div aria-busy={loading} aria-label={$i18n.t('Saved execution sequence')}>
			{#if loading}<div
					class="flex justify-center py-12"
					role="status"
					aria-label={$i18n.t('Loading trace')}
				>
					<Spinner className="size-5" />
				</div>
			{:else if error}<div role="alert" class="py-12 text-center">
					{$i18n.t('Unable to load session.')}
					<button type="button" class="underline ml-2" on:click={load}>{$i18n.t('Retry')}</button>
				</div>
			{:else}
				{#each rows as row (`${row.item.message_id}:${row.item.index}`)}
					{@const item = row.item}
					{#if item.index < 0}
						<button
							type="button"
							data-model-group
							aria-expanded={view === 'all' && row.expandable
								? expanded.has(item.message_id)
								: undefined}
							aria-disabled={view !== 'all' || !row.expandable}
							on:click={() => {
								if (view === 'all' && row.expandable) toggleGroup(item.message_id);
							}}
							class="block w-full text-left mt-2 py-1.5 px-2.5 hover:text-gray-900 dark:hover:text-gray-100 focus-visible:outline focus-visible:outline-1 focus-visible:outline-gray-400"
							data-trace-offset={row.offset}
							class:bg-gray-50={view === 'all' && targetOffset === row.offset}
							class:dark:bg-gray-850={view === 'all' && targetOffset === row.offset}
						>
							<div class="flex items-center gap-2">
								<span
									class="size-2 shrink-0"
									style:background={item.model_id
										? modelColor(item.model_id)
										: 'var(--color-gray-400)'}
								></span><span
									class="min-w-0 truncate text-gray-900 dark:text-gray-200"
									title={label(item)}>{label(item)}</span
								>{#if row.failed || item.status === 'failed'}<span>{$i18n.t('Errors')}</span
									>{/if}{#if item.duration_seconds !== null}<span
										data-response-duration
										class="shrink-0 text-[0.6875rem] tabular-nums"
										title={`${$i18n.t('Response duration')} · ${dayjs.unix(item.started_at!).format('MMM D, HH:mm:ss')}–${dayjs.unix(item.ended_at!).format('MMM D, HH:mm:ss')}`}
										>{duration(item.duration_seconds)}</span
									>{/if}{#if item.created_at}<span
										class="ml-auto shrink-0 text-[0.6875rem] tabular-nums"
										>{dayjs.unix(item.created_at).format('HH:mm')}</span
									>{/if}
								{#if view === 'all' && row.expandable}<ChevronRight
										className={`size-3 shrink-0 ${expanded.has(item.message_id) ? 'rotate-90' : ''}`}
									/>{/if}
							</div>
						</button>
					{:else}
						<div class:ps-4={view === 'all'}>
							<div
								data-operation
								title={item.error_type || undefined}
								aria-label={[
									label(item),
									status(item),
									item.duration_seconds !== null ? duration(item.duration_seconds) : ''
								]
									.filter(Boolean)
									.join(' · ')}
								class="flex items-center gap-2 w-full text-left px-2.5 py-1.5"
							>
								<span
									class="size-2 shrink-0"
									style:background={item.model_id
										? modelColor(item.model_id)
										: 'var(--color-gray-400)'}
								></span>
								<span
									class="min-w-0 flex-1 truncate text-gray-900 dark:text-gray-200"
									title={label(item)}>{label(item)}</span
								>
								{#if status(item)}<span class="text-[0.6875rem] shrink-0">{status(item)}</span>{/if}

								{#if item.duration_seconds !== null}<span
										class="text-[0.6875rem] tabular-nums shrink-0 min-w-12 text-right"
										>{duration(item.duration_seconds)}</span
									>{/if}
							</div>
						</div>
					{/if}
				{:else}<p class="py-12 text-center">
						{$i18n.t('No saved items match this filter.')}
					</p>{/each}
			{/if}
		</div>
	</div>
	<div class="flex shrink-0 items-center justify-end gap-2 pt-3 text-[0.6875rem]">
		<button
			type="button"
			aria-label={$i18n.t('Previous trace items')}
			disabled={loading || page === 0}
			class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 disabled:opacity-30"
			on:click={() => {
				targetOffset = null;
				page--;
			}}><ChevronLeft className="size-3.5" /></button
		>
		<span>{$i18n.t('Page')} {page + 1}</span>
		<button
			type="button"
			aria-label={$i18n.t('Next trace items')}
			disabled={loading || error || !hasMore}
			class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 disabled:opacity-30"
			on:click={() => {
				targetOffset = null;
				page++;
			}}><ChevronRight className="size-3.5" /></button
		>
	</div>
</section>
