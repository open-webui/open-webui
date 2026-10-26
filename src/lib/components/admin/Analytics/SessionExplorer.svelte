<script lang="ts">
	import { getContext, onMount, onDestroy, tick } from 'svelte';
	import dayjs from 'dayjs';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import ProfilePreview from '$lib/components/channel/Messages/Message/ProfilePreview.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import {
		getSessions,
		SESSION_TOKEN_RANGES,
		type Session,
		type SessionOrder,
		type SessionScope,
		type SessionOverview
	} from '$lib/apis/analytics/sessions';
	import SessionDetail from './SessionDetail.svelte';
	import { modelColor } from './UsageChart.svelte';
	import SessionSignals from './SessionSignals.svelte';

	export let scope: SessionScope;
	export let modelNames: Record<string, string> = {};
	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	let query = '';
	let modelId = '';
	let hideSubagents = false;
	let order: SessionOrder = 'tokens';
	let direction: 'asc' | 'desc' = 'desc';
	let sortFocus: SessionOrder | null = null;
	let explorer: HTMLElement;
	$: columns = [
		{ key: 'title', label: $i18n.t('Session') },
		{ key: 'user', label: $i18n.t('User') },
		{ key: 'recent', label: $i18n.t('Last active') },
		{ key: 'responses', label: $i18n.t('Responses'), numeric: true },
		{ key: 'tokens', label: $i18n.t('Tokens'), numeric: true },
		{ key: 'errors', label: $i18n.t('Response errors'), numeric: true },
		{ key: 'duration', label: $i18n.t('Span'), numeric: true }
	] as { key: SessionOrder; label: string; numeric?: boolean }[];
	function toggleSort(key: SessionOrder) {
		direction =
			order === key
				? direction === 'asc'
					? 'desc'
					: 'asc'
				: key === 'title' || key === 'user'
					? 'asc'
					: 'desc';
		order = key;
		sortFocus = key;
	}
	let tokenRange: number | null = null;
	let page = 0;
	let items: Session[] = [];
	let overview: SessionOverview | null = null;
	let overviewKey = '';
	let hasMore = false;
	let selected: Session | null = null;
	let detailPanel: HTMLElement;
	let selectedButton: HTMLElement | null = null;
	async function selectSession(session: Session, event: MouseEvent) {
		selectedButton = (event.currentTarget as HTMLTableRowElement).querySelector('button');
		selected = session;
		await tick();
		detailPanel
			?.querySelector<HTMLButtonElement>('[data-close-session]')
			?.focus({ preventScroll: true });
	}
	async function closeSession() {
		selected = null;
		await tick();
		selectedButton?.focus({ preventScroll: true });
	}
	let mounted = false;
	let loading = true;
	let error = false;
	let controller: AbortController;
	let timer: ReturnType<typeof setTimeout>;
	const pageSize = 25;
	$: formatter = new Intl.NumberFormat($i18n.language, {
		notation: 'compact',
		maximumFractionDigits: 1
	});
	$: scopeKey = JSON.stringify([scope, query, modelId, hideSubagents]);
	$: if (scopeKey) tokenRange = null;
	$: filterKey = JSON.stringify([scopeKey, order, direction, tokenRange]);
	$: if (filterKey) {
		page = 0;
		selected = null;
	}
	$: if (mounted && filterKey && page >= 0) scheduleLoad();

	function scheduleLoad() {
		clearTimeout(timer);
		controller?.abort();
		loading = true;
		error = false;
		timer = setTimeout(load, 200);
	}
	async function load() {
		controller?.abort();
		const current = new AbortController();
		controller = current;
		loading = true;
		error = false;
		try {
			const result = await getSessions(
				localStorage.token,
				scope,
				{
					...(tokenRange !== null
						? {
								token_min: SESSION_TOKEN_RANGES[tokenRange].min,
								...(SESSION_TOKEN_RANGES[tokenRange].max !== null
									? { token_max: SESSION_TOKEN_RANGES[tokenRange].max! }
									: {})
							}
						: {}),
					query,
					model_id: modelId,
					hide_subagents: hideSubagents,
					order_by: order,
					direction,
					include_summary: overviewKey !== scopeKey,
					skip: page * pageSize,
					limit: pageSize
				},
				current.signal
			);
			if (!current.signal.aborted) {
				items = result.items;
				if (result.overview) {
					overview = result.overview;
					overviewKey = scopeKey;
				}
				hasMore = result.has_more;
			}
		} catch {
			if (!current.signal.aborted) {
				error = true;
				items = [];
			}
		} finally {
			if (!current.signal.aborted) {
				loading = false;
				await tick();
				if (sortFocus && document.activeElement === document.body)
					explorer
						?.querySelector<HTMLButtonElement>(`[data-sort="${sortFocus}"]`)
						?.focus({ preventScroll: true });
				sortFocus = null;
			}
		}
	}
	const span = (seconds: number | null) =>
		seconds === null
			? $i18n.t('Not logged')
			: seconds < 60
				? `${Math.round(seconds)}s`
				: seconds < 3600
					? `${Math.round(seconds / 60)}m`
					: `${(seconds / 3600).toFixed(1)}h`;
	onMount(() => {
		mounted = true;
	});
	onDestroy(() => {
		clearTimeout(timer);
		controller?.abort();
	});
</script>

<div class="min-w-0">
	<section
		bind:this={explorer}
		aria-label={$i18n.t('Sessions')}
		class="min-w-0 flex-1 text-xs text-gray-500 dark:text-gray-400"
	>
		{#if overview && overviewKey === scopeKey && !error}<SessionSignals
				{overview}
				selectedRange={tokenRange}
				onSelect={(index) => (tokenRange = index)}
			/>{/if}
		<div class="flex flex-wrap items-center justify-between gap-3 mb-3">
			<input
				type="search"
				bind:value={query}
				maxlength="200"
				aria-label={$i18n.t('Search sessions')}
				placeholder={$i18n.t('Search sessions, users or folders')}
				class="min-w-0 h-7 w-full sm:w-56 bg-transparent p-0 text-xs text-gray-500 dark:text-gray-400 placeholder:text-gray-400 outline-none focus:text-gray-900 dark:focus:text-gray-100"
			/>
			<div class="flex w-full sm:w-auto items-center gap-x-4">
				<select
					bind:value={modelId}
					aria-label={$i18n.t('Model')}
					class="min-w-0 w-fit max-w-40 pr-5 py-1 text-xs bg-transparent outline-none text-gray-500 dark:text-gray-400"
				>
					<option value="">{$i18n.t('All models')}</option>
					{#each Object.entries(modelNames).sort( (a, b) => a[1].localeCompare(b[1]) ) as [id, name]}<option
							value={id}>{name}</option
						>{/each}
				</select>
				<div class="ml-auto shrink-0">
					<Dropdown align="end" closeOnSelect>
						<button
							type="button"
							aria-label={$i18n.t('Session options')}
							class="flex items-center justify-center p-1.5 text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
						>
							<EllipsisHorizontal className="size-4" />
						</button>
						<div slot="content">
							<DropdownMenu className="min-w-48">
								<button
									type="button"
									role="menuitemcheckbox"
									aria-checked={hideSubagents}
									on:click={() => (hideSubagents = !hideSubagents)}
								>
									<span class="flex-1 text-left">{$i18n.t('Hide sub-agents')}</span>
									<span class="size-3.5 shrink-0"
										>{#if hideSubagents}<Check className="size-3.5" />{/if}</span
									>
								</button>
							</DropdownMenu>
						</div>
					</Dropdown>
				</div>
			</div>
		</div>
		<div aria-busy={loading} class="min-h-40">
			{#if loading}
				<div
					class="flex justify-center py-12"
					role="status"
					aria-label={$i18n.t('Loading sessions')}
				>
					<Spinner className="size-5" />
				</div>
			{:else if error}
				<div role="alert" class="py-12 text-center">
					{$i18n.t('Unable to load sessions.')}
					<button type="button" class="underline underline-offset-2 ml-2" on:click={load}
						>{$i18n.t('Retry')}</button
					>
				</div>
			{:else if !items.length}
				<div class="py-12 text-center">{$i18n.t('No sessions match these filters.')}</div>
			{:else}
				<div class="max-h-[22rem] overflow-auto scrollbar-hover">
					<table class="session-table w-full text-left text-xs tabular-nums whitespace-nowrap">
						<thead class="sticky top-0 z-10 bg-white dark:bg-gray-900 text-[0.6875rem]">
							<tr>
								{#each columns as column}
									<th
										scope="col"
										class="font-normal"
										aria-sort={order === column.key
											? direction === 'asc'
												? 'ascending'
												: 'descending'
											: 'none'}
										title={column.key === 'duration'
											? $i18n.t('First to last saved message, including idle time')
											: undefined}
									>
										<button
											type="button"
											data-sort={column.key}
											on:click={() => toggleSort(column.key)}
											class="w-full flex gap-1.5 items-center px-2.5 py-1.5 text-left font-normal cursor-pointer select-none focus-visible:outline focus-visible:outline-1 focus-visible:outline-gray-400"
											class:justify-end={column.numeric}
										>
											{column.label}
											{#if order === column.key}
												{#if direction === 'asc'}<ChevronUp className="size-2" />{:else}<ChevronDown
														className="size-2"
													/>{/if}
											{:else}<span class="invisible"><ChevronUp className="size-2" /></span>{/if}
										</button>
									</th>
								{/each}
							</tr>
						</thead>
						<tbody>
							{#each items as session (session.id)}
								<!-- The native title button provides keyboard activation; its click bubbles to the row. -->
								<tr
									on:click={(event) => selectSession(session, event)}
									class="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
									class:bg-gray-50={selected?.id === session.id}
									class:dark:bg-gray-850={selected?.id === session.id}
								>
									<td class="px-2.5 py-1.5">
										<button
											type="button"
											class="text-left block w-full max-w-[12rem] sm:max-w-80 rounded-sm focus-visible:outline focus-visible:outline-1 focus-visible:outline-gray-400"
										>
											<span
												class="block truncate text-gray-900 dark:text-gray-200"
												title={session.title}>{session.title || $i18n.t('Untitled chat')}</span
											>
											<span
												class="flex items-center gap-2 text-[0.6875rem] text-gray-400 dark:text-gray-500 mt-0.5"
												><span class="truncate max-w-40"
													>{session.folder_name ||
														(session.model_id
															? modelNames[session.model_id] || session.model_id
															: $i18n.t('No model recorded'))}</span
												>{#if session.forked_from}<span class="shrink-0">{$i18n.t('Fork')}</span
													>{/if}{#if session.kind === 'subagent'}<span class="shrink-0"
														>{$i18n.t('Sub-agent')}</span
													>{/if}{#if !session.folder_name && session.model_count > 1}<span
														class="shrink-0">+{session.model_count - 1}</span
													>{/if}</span
											>
										</button>
									</td>
									<td class="px-2.5 py-1.5"
										>{#if session.user_id}
											<ProfilePreview
												user={{ id: session.user_id, name: session.user_name }}
												side="right"
												align="center"
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
												<span class="block max-w-28 truncate"
													>{session.user_name || $i18n.t('User')}</span
												>
											</ProfilePreview>
										{:else}<span>{session.user_name || '-'}</span>{/if}</td
									>
									<td
										class="px-2.5 py-1.5"
										title={session.last_active
											? dayjs.unix(session.last_active).format('YYYY-MM-DD HH:mm:ss')
											: ''}
										>{session.last_active
											? dayjs
													.unix(session.last_active)
													.locale($i18n.language)
													.format('MMM D, HH:mm')
											: $i18n.t('Not logged')}</td
									>
									<td class="px-2.5 py-1.5 text-right"
										>{session.responses.toLocaleString($i18n.language)}</td
									>
									<td
										class="px-2.5 py-1.5 text-right"
										title={`${session.recorded_responses}/${session.responses} ${$i18n.t('responses with recorded usage')}`}
										><div class="flex items-center justify-end gap-3">
											<span class="w-20 h-1.5 shrink-0" aria-hidden="true">
												{#if session.recorded_responses && overview && overview.max_tokens > 0}
													<span
														data-token-bar
														class="block h-full"
														style:width={`${(100 * session.tokens) / overview.max_tokens}%`}
														style:background={session.model_count === 1 && session.model_id
															? modelColor(session.model_id)
															: 'var(--color-gray-400)'}
													></span>
												{/if}
											</span>
											<span class="min-w-12"
												>{session.recorded_responses
													? formatter.format(session.tokens)
													: '-'}{#if session.recorded_responses > 0 && session.complete_responses < session.responses}<span
														class="text-gray-400">*</span
													>{/if}</span
											>
										</div></td
									>
									<td class="px-2.5 py-1.5 text-right">{session.errors}</td>
									<td class="px-2.5 py-1.5 text-right">{span(session.span_seconds)}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		</div>
		<div
			class="mt-3 flex items-center justify-between gap-3 text-[0.6875rem] text-gray-400 dark:text-gray-500"
		>
			<span
				title={$i18n.t(
					'One session per chat. Counts cover the selected date range; span includes idle time.'
				)}>{$i18n.t('- usage not recorded · * partial usage')}</span
			>
			<div class="flex items-center gap-2">
				<button
					type="button"
					aria-label={$i18n.t('Previous sessions')}
					disabled={loading || page === 0}
					class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 disabled:opacity-30"
					on:click={() => page--}><ChevronLeft className="size-3.5" /></button
				><span>{$i18n.t('Page')} {page + 1}</span><button
					type="button"
					aria-label={$i18n.t('Next sessions')}
					disabled={loading || error || !hasMore}
					class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 disabled:opacity-30"
					on:click={() => page++}><ChevronRight className="size-3.5" /></button
				>
			</div>
		</div>
	</section>
	{#if selected}
		<Modal
			show={true}
			size="lg"
			ariaLabel={$i18n.t('Session details')}
			onRequestClose={closeSession}
		>
			<div bind:this={detailPanel} class="p-5">
				<SessionDetail session={selected} {scope} {modelNames} onClose={closeSession} />
			</div>
		</Modal>
	{/if}
</div>
