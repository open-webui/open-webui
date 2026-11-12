<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import { gitRequest } from '$lib/apis/terminal/git';
	import type { TerminalTarget } from '$lib/apis/terminal';
	import Icon from '../FileNav/Icon.svelte';
	import GitDiff from './GitDiff.svelte';
	import GitListDivider from './GitListDivider.svelte';
	import Dropdown from '../../common/Dropdown.svelte';
	import DropdownMenu from '../../common/DropdownMenu.svelte';
	import ConfirmDialog from '../../common/ConfirmDialog.svelte';
	import Tooltip from '../../common/Tooltip.svelte';
	import Markdown from '../Messages/Markdown.svelte';
	import { copyToClipboard } from '$lib/utils';
	import {
		primaryButton,
		disabledButton,
		secondaryButton,
		relativeTime,
		checkName,
		checkLink,
		checkResult,
		checkOutcome,
		outcomeTone,
		checksSummary,
		checkPrompt,
		notePrompt,
		feedbackPrompt,
		conflictPrompt,
		type Check
	} from './gitPanel';
	export let target: TerminalTarget;

	export let directory: string;
	export let branch: string;
	export let defaultBranch = 'main';
	export let mode: 'unified' | 'split' = 'unified';
	export let hideWhitespace = false;
	export let listWidth = 240;
	export let maxListWidth = 240;
	export let onResizeList: (width: number) => void = () => {};
	export let onChange: () => void = () => {};

	// Drafts text into the chat composer; the chat actions are hidden without it.
	export let onDraft: ((text: string) => void) | null = null;
	type PullRequest = {
		number: number;
		title: string;
		state: string;
		isDraft: boolean;
		body: string;
		headRefName: string;
		baseRefName: string;
		url: string;
		mergeable?: string;
		reviewRequests?: { login?: string; name?: string }[];
		assignees?: { login?: string; name?: string }[];
		labels?: { name: string }[];
		reviewDecision?: string;
		author?: { login: string };
		comments?: { id: string; body: string; author?: { login: string } }[];
		reviews?: { id: string; body: string; state: string; author?: { login: string } }[];
		statusCheckRollup?: Check[];
		updatedAt?: string;
	};
	const i18n = getContext<any>('i18n');
	let prs: PullRequest[] = [];
	let selected: PullRequest | null = null;
	let state = 'open';
	let search = '';
	let view: 'summary' | 'code' | 'checks' | 'activity' = 'summary';
	let diff = '';
	let listLoading = false;
	let loading = false;
	let busy = false;
	let listError = '';
	let error = '';
	let editing = false;
	let creating = false;
	let title = '';
	let body = '';
	let base = defaultBranch;
	let head = branch;
	let draft = false;
	let comment = '';
	let mergeMethod = 'squash';
	let confirmation = false;
	let pendingAction = '';
	let listGeneration = 0;
	let generation = 0;

	$: states = [
		{ value: 'open', label: $i18n.t('Open') },
		{ value: 'closed', label: $i18n.t('Closed') },
		{ value: 'merged', label: $i18n.t('Merged') },
		{ value: 'all', label: $i18n.t('All') }
	];
	$: tabs = [
		{ value: 'summary', label: $i18n.t('Summary') },
		{ value: 'code', label: $i18n.t('Code') },
		{ value: 'checks', label: $i18n.t('Checks') },
		{ value: 'activity', label: $i18n.t('Activity') }
	] as { value: typeof view; label: string }[];
	$: mergeMethods = [
		{ value: 'squash', label: $i18n.t('Squash and merge') },
		{ value: 'merge', label: $i18n.t('Create a merge commit') },
		{ value: 'rebase', label: $i18n.t('Rebase and merge') }
	];
	$: mergeLabel = mergeMethods.find((method) => method.value === mergeMethod)?.label ?? '';
	$: actionLabels = {
		merge: mergeLabel,
		close: $i18n.t('Close pull request'),
		approve: $i18n.t('Approve'),
		'request-changes': $i18n.t('Request changes')
	} as Record<string, string>;
	$: filtered = prs.filter((pr) =>
		`${pr.number} ${pr.title}`.toLowerCase().includes(search.toLowerCase())
	);
	$: showingDetail = !!selected || creating || editing;
	$: failingChecks = (selected?.statusCheckRollup ?? []).filter(
		(check) => checkOutcome(check) === 'fail'
	);
	$: feedback = [...(selected?.comments ?? []), ...(selected?.reviews ?? [])].filter((item) =>
		item.body?.trim()
	);

	const label = (value = '') =>
		({
			OPEN: $i18n.t('Open'),
			CLOSED: $i18n.t('Closed'),
			MERGED: $i18n.t('Merged'),
			APPROVED: $i18n.t('Approved'),
			CHANGES_REQUESTED: $i18n.t('Changes requested'),
			REVIEW_REQUIRED: $i18n.t('Review required'),
			COMMENTED: $i18n.t('Commented'),
			DISMISSED: $i18n.t('Dismissed'),
			MERGEABLE: $i18n.t('No conflicts'),
			CONFLICTING: $i18n.t('Conflicts')
		})[value] ?? value.toLowerCase().replaceAll('_', ' ');
	const people = (list?: { login?: string; name?: string }[]) =>
		list?.map((person) => person.login || person.name).join(', ') || $i18n.t('None');

	const rowDetails = (pr: PullRequest) =>
		[
			`#${pr.number}`,
			pr.author?.login,
			pr.isDraft ? $i18n.t('Draft') : pr.state !== 'OPEN' ? label(pr.state) : '',
			pr.state === 'OPEN' && pr.mergeable === 'CONFLICTING' ? $i18n.t('Conflicts') : '',
			pr.state === 'OPEN' && ['APPROVED', 'CHANGES_REQUESTED'].includes(pr.reviewDecision ?? '')
				? label(pr.reviewDecision)
				: '',
			pr.updatedAt ? relativeTime(pr.updatedAt) : ''
		]
			.filter(Boolean)
			.join(' · ');
	const checksTitle = (summary: NonNullable<ReturnType<typeof checksSummary>>) =>
		$i18n.t('Checks: {{failed}} failing, {{pending}} pending, {{passed}} passing', summary);
	const copy = async (text: string) => {
		if (!(await copyToClipboard(text))) error = $i18n.t('Could not copy to clipboard');
	};
	const sendToChat = (text: string) => onDraft?.(text);

	const request = <T,>(
		operation: string,
		params: Record<string, string> = {},
		payload?: Record<string, unknown>
	) => gitRequest<T>(target, directory, `pr/${operation}`, params, payload);
	const load = async () => {
		const version = ++listGeneration;
		listLoading = true;
		listError = '';
		try {
			const data = await request<{ items: PullRequest[] }>('list', { state });
			if (version === listGeneration) prs = data.items;
		} catch (reason) {
			if (version === listGeneration)
				listError = String(reason instanceof Error ? reason.message : reason);
		} finally {
			if (version === listGeneration) listLoading = false;
		}
	};
	const select = async (pr: PullRequest, tab: typeof view = 'summary') => {
		const version = ++generation;
		selected = pr;
		creating = editing = false;
		view = tab;
		loading = true;
		error = '';
		try {
			if (tab === 'code') {
				const data = await request<{ diff: string }>('diff', { number: String(pr.number) });
				if (version === generation) diff = data.diff;
			} else if (tab === 'checks') {
				const data = await request<{ items: NonNullable<PullRequest['statusCheckRollup']> }>(
					'checks',
					{ number: String(pr.number) }
				);
				if (version === generation) selected = { ...pr, statusCheckRollup: data.items };
			} else {
				const data = await request<PullRequest>('view', { number: String(pr.number) });
				if (version === generation) selected = data;
			}
		} catch (reason) {
			if (version === generation) error = String(reason instanceof Error ? reason.message : reason);
		} finally {
			if (version === generation) loading = false;
		}
	};
	const mutate = async (action: string) => {
		if (busy) return;
		busy = true;
		error = '';
		try {
			await request(
				['approve', 'request-changes'].includes(action) ? 'review' : action,
				{},
				{
					event: action === 'request-changes' ? 'request_changes' : action,
					number: selected?.number ?? 0,
					title,
					body: ['create', 'edit'].includes(action) ? body : comment,
					base,
					head,
					draft,
					strategy: mergeMethod
				}
			);
			creating = editing = false;
			comment = '';
			onChange();
			void load();
			if (selected && action !== 'create') await select(selected, view);
		} catch (reason) {
			error = String(reason instanceof Error ? reason.message : reason);
		} finally {
			busy = false;
		}
	};
	const confirm = (action: string) => {
		pendingAction = action;
		confirmation = true;
	};
	const startCreate = () => {
		++generation;
		loading = false;
		error = '';
		selected = null;
		editing = false;
		creating = true;
		title = body = '';
		head = branch;
		base = defaultBranch;
		draft = false;
	};
	const cancelForm = () => {
		if (editing) editing = false;
		else back();
	};
	const back = () => {
		++generation;
		selected = null;
		creating = editing = false;
		diff = '';
		error = '';
		loading = false;
	};
	onMount(() => {
		void load();
	});
	onDestroy(() => {
		++generation;
		++listGeneration;
	});
</script>

<div class="flex min-h-0 min-w-0 flex-1 text-[0.6875rem]">
	<div
		class="min-w-0 flex-1 flex-col overflow-hidden @min-[560px]:flex @min-[560px]:flex-[0_0_var(--git-list-width)] {showingDetail
			? 'hidden'
			: 'flex'}"
		style:--git-list-width={`${listWidth}px`}
	>
		<div
			class="flex min-w-0 items-center gap-1.5 h-7 pl-2.5 pr-1 shrink-0 border-b border-gray-100/50 dark:border-white/2"
		>
			<Icon name="search" size={12} class="shrink-0 text-gray-300 dark:text-gray-600" /><input
				class="min-w-0 flex-1 bg-transparent text-[0.6875rem] text-gray-700 dark:text-gray-300 placeholder:text-gray-400 dark:placeholder:text-gray-600 outline-none"
				aria-label={$i18n.t('Search pull requests')}
				placeholder={$i18n.t('Search pull requests')}
				bind:value={search}
			/>
			<Dropdown align="end" closeOnSelect>
				<button
					class="flex shrink-0 items-center gap-1 h-6 px-1.5 rounded-md text-gray-400 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors duration-75"
					aria-label={$i18n.t('Filter pull requests')}
					><span class="text-[0.6875rem]"
						>{states.find((option) => option.value === state)?.label}</span
					><Icon name="chevron-down" size={9} /></button
				>
				<div slot="content">
					<DropdownMenu className="w-32">
						{#each states as option}<button
								on:click={() => {
									if (state === option.value) return;
									state = option.value;
									prs = [];
									void load();
								}}
								><span class="flex-1 text-left">{option.label}</span
								>{#if state === option.value}<Icon name="check" size={11} />{/if}</button
							>{/each}
					</DropdownMenu>
				</div>
			</Dropdown>
			<Tooltip content={$i18n.t('New pull request')}>
				<button
					class="flex items-center justify-center w-5 h-5 rounded shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
					aria-label={$i18n.t('New pull request')}
					on:click={startCreate}><Icon name="plus" size={12} /></button
				>
			</Tooltip>
		</div>
		{#if listError}<div
				role="alert"
				class="px-2.5 py-1.5 text-[0.6875rem] text-gray-500 dark:text-gray-400 break-words"
			>
				{listError}
			</div>{/if}
		<div class="min-h-0 flex-1 overflow-y-auto scrollbar-hidden">
			{#each filtered as pr (pr.number)}{@const checks =
					pr.state === 'OPEN' ? checksSummary(pr.statusCheckRollup) : null}<button
					class="flex w-full min-w-0 flex-col px-2.5 py-1.5 text-left border-b border-gray-50/50 dark:border-white/2 transition-colors duration-75 {selected?.number ===
					pr.number
						? 'bg-gray-100/40 dark:bg-gray-800/25'
						: 'hover:bg-gray-100/30 dark:hover:bg-gray-800/20'}"
					on:click={() => select(pr)}
					><span class="flex w-full min-w-0 items-center gap-1.5"
						><span class="min-w-0 flex-1 truncate text-xs text-gray-800 dark:text-gray-200"
							>{pr.title}</span
						>{#if checks}<span
								class="w-1.5 h-1.5 rounded-full shrink-0 {outcomeTone[checks.outcome]}"
								title={checksTitle(checks)}
							></span>{/if}</span
					><span class="w-full truncate text-[0.625rem] font-mono text-gray-400 dark:text-gray-600"
						>{rowDetails(pr)}</span
					></button
				>{/each}
			{#if !filtered.length}<div
					class="flex h-full items-center justify-center p-3 text-center text-[0.6875rem] text-gray-400 dark:text-gray-600"
				>
					{$i18n.t(listLoading ? 'Loading...' : 'No pull requests')}
				</div>{/if}
		</div>
	</div>
	<GitListDivider width={listWidth} max={maxListWidth} onResize={onResizeList} />
	<div
		class="min-w-0 flex-1 flex-col overflow-hidden @min-[560px]:flex {showingDetail
			? 'flex'
			: 'hidden'}"
	>
		{#if showingDetail}
			<div
				class="flex items-center gap-2 px-2 h-6 shrink-0 border-b border-gray-100/50 dark:border-white/2 text-[0.625rem] font-mono text-gray-400 dark:text-gray-600"
			>
				<button
					class="@min-[560px]:hidden"
					aria-label={$i18n.t('Back to pull requests')}
					on:click={back}><Icon name="chevron-left" size={12} /></button
				><span class="min-w-0 flex-1 truncate"
					>{selected && !creating
						? `#${selected.number} · ${selected.title}`
						: $i18n.t('New pull request')}</span
				>
				{#if onDraft && selected?.state === 'OPEN' && !creating && !editing && (failingChecks.length || feedback.length)}<button
						class="flex shrink-0 items-center gap-1 h-5 px-1.5 rounded-md font-sans text-[0.625rem] text-gray-500 dark:text-gray-400 hover:bg-gray-100/50 hover:text-gray-800 dark:hover:bg-white/5 dark:hover:text-gray-200 transition-colors duration-75"
						on:click={() =>
							selected && sendToChat(feedbackPrompt($i18n.t, selected, failingChecks, feedback))}
						><Icon name="chat-plus" size={11} />{$i18n.t('Address feedback')}</button
					>{/if}
				{#if selected && !creating && !editing}<Dropdown side="top" align="end" closeOnSelect
						><button
							class="flex items-center justify-center w-5 h-5 rounded shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
							aria-label={$i18n.t('Pull request actions')}
							><Icon name="three-dots" size={12} /></button
						>
						<div slot="content">
							<DropdownMenu className="w-44">
								<button disabled={busy} on:click={() => mutate('checkout')}
									><Icon name="git-branch" size={13} />{$i18n.t('Checkout')}</button
								>
								<button
									disabled={busy}
									on:click={() => {
										editing = true;
										title = selected?.title ?? '';
										body = selected?.body ?? '';
									}}><Icon name="pencil" size={13} />{$i18n.t('Edit')}</button
								>
								{#if selected.state === 'OPEN'}<button
										disabled={busy}
										on:click={() => mutate('update-branch')}
										><Icon name="refresh" size={13} />{$i18n.t('Update branch')}</button
									>{#if selected.isDraft}<button disabled={busy} on:click={() => mutate('ready')}
											><Icon name="check" size={13} />{$i18n.t('Mark ready')}</button
										>{/if}<button disabled={busy} on:click={() => confirm('close')}
										><Icon name="xmark" size={13} />{$i18n.t('Close pull request')}</button
									>{:else if selected.state === 'CLOSED'}<button
										disabled={busy}
										on:click={() => mutate('reopen')}
										><Icon name="undo" size={13} />{$i18n.t('Reopen')}</button
									>{/if}
								<a href={selected.url} target="_blank" rel="noopener noreferrer"
									><Icon name="external-link" size={13} />{$i18n.t('Open in GitHub')}</a
								>
								<button on:click={() => selected && copy(selected.url)}
									><Icon name="copy" size={13} />{$i18n.t('Copy link')}</button
								>
								<button on:click={() => selected && copy(selected.headRefName)}
									><Icon name="copy" size={13} />{$i18n.t('Copy branch name')}</button
								>
							</DropdownMenu>
						</div></Dropdown
					>{/if}
			</div>
		{/if}
		{#if error && showingDetail}<div
				role="alert"
				class="px-2.5 py-1.5 text-[0.6875rem] text-gray-500 dark:text-gray-400 break-words"
			>
				{error}
			</div>{/if}
		{#if creating || editing}
			<form
				class="flex min-h-0 flex-1 flex-col"
				on:submit|preventDefault={() => mutate(editing ? 'edit' : 'create')}
			>
				<div class="min-h-0 flex-1 overflow-y-auto scrollbar-hidden px-2">
					<input
						class="w-full h-7 px-1 bg-transparent text-[0.6875rem] text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-600 outline-none"
						aria-label={$i18n.t('Pull request title')}
						placeholder={$i18n.t('Title')}
						bind:value={title}
						required
					/>
					<textarea
						class="block w-full px-1 py-1 bg-transparent text-[0.6875rem] text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-600 outline-none resize-none border-t border-gray-100/50 dark:border-white/2"
						aria-label={$i18n.t('Pull request description')}
						placeholder={$i18n.t('Description')}
						rows="6"
						bind:value={body}
					></textarea>
					{#if creating}<div
							class="flex min-w-0 items-center gap-1.5 h-7 px-1 border-t border-gray-100/50 dark:border-white/2 text-gray-400 dark:text-gray-600"
						>
							<Icon name="git-branch" size={12} class="shrink-0" /><input
								class="min-w-0 flex-1 bg-transparent font-mono text-[0.625rem] text-gray-700 dark:text-gray-300 placeholder:text-gray-400 dark:placeholder:text-gray-600 outline-none"
								aria-label={$i18n.t('Base branch')}
								placeholder={$i18n.t('Base branch')}
								bind:value={base}
								required
							/><span class="shrink-0 font-mono text-[0.625rem]">←</span><input
								class="min-w-0 flex-1 bg-transparent font-mono text-[0.625rem] text-gray-700 dark:text-gray-300 placeholder:text-gray-400 dark:placeholder:text-gray-600 outline-none"
								aria-label={$i18n.t('Head branch')}
								placeholder={$i18n.t('Head branch')}
								bind:value={head}
								required
							/>
						</div>{/if}
				</div>
				<div
					class="flex items-center gap-1 px-2 py-1.5 shrink-0 border-t border-gray-100/50 dark:border-white/2"
				>
					{#if creating}<button
							type="button"
							class="flex shrink-0 items-center gap-1.5 h-6 px-1 text-[0.6875rem] text-gray-500 dark:text-gray-400"
							role="checkbox"
							aria-checked={draft}
							on:click={() => (draft = !draft)}
							><span
								class="flex items-center justify-center w-3 h-3 rounded border shrink-0 border-gray-300 dark:border-gray-600 {draft
									? 'bg-gray-800 dark:bg-white'
									: ''}"
								>{#if draft}<Icon
										name="check"
										size={7}
										class="text-white dark:text-black"
									/>{/if}</span
							>{$i18n.t('Draft')}</button
						>{/if}
					<div class="flex-1"></div>
					<button
						type="button"
						class="h-6 px-2.5 rounded-lg text-[0.6875rem] font-normal transition-colors duration-75 {secondaryButton}"
						on:click={cancelForm}>{$i18n.t('Cancel')}</button
					>
					<button
						class="h-6 px-2.5 rounded-lg text-[0.6875rem] font-normal transition-colors duration-75 {!busy &&
						title.trim()
							? primaryButton
							: disabledButton}"
						disabled={busy || !title.trim()}
						>{$i18n.t(editing ? 'Save' : 'Create pull request')}</button
					>
				</div>
			</form>
		{:else if selected}
			<div
				class="flex items-center gap-0.5 px-1 h-7 shrink-0 border-b border-gray-100/50 dark:border-white/2"
			>
				{#each tabs as tab}<button
						class="px-2 py-0.5 shrink-0 rounded-md text-[0.6875rem] font-normal transition-colors duration-75 {view ===
						tab.value
							? 'bg-gray-100/40 dark:bg-gray-800/25 text-gray-900 dark:text-white'
							: 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'}"
						on:click={() => selected && select(selected, tab.value)}>{tab.label}</button
					>{/each}
			</div>
			{#if loading}<div
					class="flex flex-1 items-center justify-center p-3 text-center text-[0.6875rem] text-gray-400 dark:text-gray-600"
				>
					{$i18n.t('Loading...')}
				</div>
			{:else if view === 'code'}<div class="min-h-0 flex-1 overflow-auto scrollbar-hidden">
					{#if diff}<GitDiff code={diff} {mode} {hideWhitespace} />{:else}<div
							class="flex h-full items-center justify-center p-3 text-center text-gray-400 dark:text-gray-600"
						>
							{$i18n.t('No text changes')}
						</div>{/if}
				</div>
			{:else if view === 'summary'}
				<div class="min-h-0 flex-1 overflow-y-auto scrollbar-hidden px-2.5 py-2">
					<dl class="grid grid-cols-[5rem_minmax(0,1fr)] gap-x-3 gap-y-1">
						<dt class="text-gray-400 dark:text-gray-600">{$i18n.t('Author')}</dt>
						<dd class="truncate text-gray-700 dark:text-gray-300">
							{selected.author?.login ?? $i18n.t('Unknown')}
						</dd>
						<dt class="text-gray-400 dark:text-gray-600">{$i18n.t('Branch')}</dt>
						<dd class="truncate font-mono text-[0.625rem] text-gray-700 dark:text-gray-300">
							{selected.baseRefName} ← {selected.headRefName}
						</dd>
						<dt class="text-gray-400 dark:text-gray-600">{$i18n.t('Status')}</dt>
						<dd class="truncate text-gray-700 dark:text-gray-300">
							{selected.isDraft ? $i18n.t('Draft') : label(selected.state)}{selected.reviewDecision
								? ` · ${label(selected.reviewDecision)}`
								: ''}
						</dd>
						<dt class="text-gray-400 dark:text-gray-600">{$i18n.t('Reviewers')}</dt>
						<dd class="truncate text-gray-700 dark:text-gray-300">
							{people(selected.reviewRequests)}
						</dd>
						<dt class="text-gray-400 dark:text-gray-600">{$i18n.t('Assignees')}</dt>
						<dd class="truncate text-gray-700 dark:text-gray-300">{people(selected.assignees)}</dd>
						<dt class="text-gray-400 dark:text-gray-600">{$i18n.t('Labels')}</dt>
						<dd class="truncate text-gray-700 dark:text-gray-300">
							{selected.labels?.map((item) => item.name).join(', ') || $i18n.t('None')}
						</dd>
						{#if selected.state === 'OPEN'}<dt class="text-gray-400 dark:text-gray-600">
								{$i18n.t('Merge')}
							</dt>
							<dd class="truncate text-gray-700 dark:text-gray-300">
								{selected.mergeable ? label(selected.mergeable) : $i18n.t('Unknown')}
							</dd>{/if}
					</dl>
					<div
						class="mt-3 pb-1 text-[0.625rem] leading-none uppercase text-gray-400 dark:text-gray-600"
					>
						{$i18n.t('Description')}
					</div>
					{#if selected.body?.trim()}<div
							class="markdown-prose-xs max-w-none break-words text-gray-800 dark:text-gray-200"
						>
							<Markdown
								id={`pr-${selected.number}-body`}
								content={selected.body}
								allowHtml={false}
								allowEmbeds={false}
								editCodeBlock={false}
							/>
						</div>{:else}<div class="text-xs text-gray-400 dark:text-gray-600">
							{$i18n.t('No description')}
						</div>{/if}
				</div>
				{#if selected.state === 'OPEN'}<div
						class="flex items-center gap-1 px-2 py-1.5 shrink-0 border-t border-gray-100/50 dark:border-white/2"
					>
						{#if selected.isDraft}<button
								class="flex-1 h-6 rounded-lg text-[0.6875rem] font-normal transition-colors duration-75 {busy
									? disabledButton
									: primaryButton}"
								disabled={busy}
								on:click={() => mutate('ready')}>{$i18n.t('Mark ready')}</button
							>{:else}
							{@const blocked = busy || selected.mergeable === 'CONFLICTING'}
							{#if onDraft && selected.mergeable === 'CONFLICTING'}<button
									class="flex flex-1 items-center justify-center gap-1.5 h-6 rounded-lg text-[0.6875rem] font-normal transition-colors duration-75 {primaryButton}"
									on:click={() => selected && sendToChat(conflictPrompt($i18n.t, selected))}
									><Icon name="chat-plus" size={11} />{$i18n.t('Resolve conflicts in chat')}</button
								>{:else}<button
									class="flex-1 h-6 rounded-lg text-[0.6875rem] font-normal transition-colors duration-75 {blocked
										? disabledButton
										: primaryButton}"
									disabled={blocked}
									on:click={() => confirm('merge')}>{mergeLabel}</button
								>
								<Dropdown side="top" align="end" closeOnSelect>
									<button
										class="flex items-center justify-center w-6 h-6 rounded-lg shrink-0 transition-colors duration-75 {secondaryButton}"
										aria-label={$i18n.t('Merge method')}
										><Icon name="chevron-up" size={10} /></button
									>
									<div slot="content">
										<DropdownMenu className="w-48">
											{#each mergeMethods as method}<button
													on:click={() => (mergeMethod = method.value)}
													><span class="flex-1 text-left">{method.label}</span
													>{#if mergeMethod === method.value}<Icon
															name="check"
															size={11}
														/>{/if}</button
												>{/each}
										</DropdownMenu>
									</div>
								</Dropdown>{/if}
						{/if}
					</div>
				{:else if selected.state === 'CLOSED'}<div
						class="flex items-center px-2 py-1.5 shrink-0 border-t border-gray-100/50 dark:border-white/2"
					>
						<button
							class="flex-1 h-6 rounded-lg text-[0.6875rem] font-normal transition-colors duration-75 {secondaryButton}"
							disabled={busy}
							on:click={() => mutate('reopen')}>{$i18n.t('Reopen')}</button
						>
					</div>{/if}
			{:else if view === 'checks'}<div class="min-h-0 flex-1 overflow-y-auto scrollbar-hidden">
					{#each selected.statusCheckRollup ?? [] as check}
						{@const outcome = checkOutcome(check)}
						{@const link = checkLink(check)}
						<div
							class="group flex min-w-0 items-center gap-1.5 h-7 px-2.5 border-b border-gray-50/50 dark:border-white/2"
						>
							<span class="w-1.5 h-1.5 rounded-full shrink-0 {outcomeTone[outcome]}"
							></span>{#if link}<a
									class="min-w-0 flex-1 truncate text-[0.6875rem] text-gray-800 dark:text-gray-200 hover:underline"
									href={link}
									target="_blank"
									rel="noopener noreferrer">{checkName(check)}</a
								>{:else}<span
									class="min-w-0 flex-1 truncate text-[0.6875rem] text-gray-800 dark:text-gray-200"
									>{checkName(check)}</span
								>{/if}
							{#if onDraft && outcome === 'fail' && selected.state === 'OPEN'}<button
									class="flex shrink-0 items-center gap-1 h-5 px-1.5 rounded-md font-sans text-[0.625rem] text-gray-500 dark:text-gray-400 hover:bg-gray-100/50 hover:text-gray-800 dark:hover:bg-white/5 dark:hover:text-gray-200 transition-colors duration-75"
									on:click={() => selected && sendToChat(checkPrompt($i18n.t, selected, check))}
									><Icon name="chat-plus" size={11} />{$i18n.t('Fix')}</button
								>{/if}<span
								class="shrink-0 font-mono text-[0.625rem] text-gray-400 dark:text-gray-600"
								>{checkResult(check)}</span
							>
						</div>
					{/each}
					{#if !selected.statusCheckRollup?.length}<div
							class="flex h-full items-center justify-center p-3 text-center text-[0.6875rem] text-gray-400 dark:text-gray-600"
						>
							{$i18n.t('No checks')}
						</div>{/if}
				</div>
			{:else}
				{@const activity = [
					...(selected.comments ?? []).map((item) => ({ ...item, state: '' })),
					...(selected.reviews ?? [])
				]}
				<div class="min-h-0 flex-1 overflow-y-auto scrollbar-hidden">
					{#each activity as item, index}<div
							class="group px-2.5 py-1.5 border-b border-gray-50/50 dark:border-white/2"
						>
							<div class="flex min-w-0 items-center gap-1.5 h-5">
								<span
									class="min-w-0 flex-1 truncate font-mono text-[0.625rem] text-gray-400 dark:text-gray-600"
									>{item.author?.login ?? $i18n.t('Unknown')}{item.state
										? ` · ${label(item.state)}`
										: ''}</span
								>{#if onDraft && item.body?.trim()}<button
										class="opacity-0 group-hover:opacity-100 focus:opacity-100 flex shrink-0 items-center gap-1 h-5 px-1.5 rounded-md font-sans text-[0.625rem] text-gray-500 dark:text-gray-400 hover:bg-gray-100/50 hover:text-gray-800 dark:hover:bg-white/5 dark:hover:text-gray-200 transition-colors duration-75"
										on:click={() => selected && sendToChat(notePrompt($i18n.t, selected, item))}
										><Icon name="chat-plus" size={11} />{$i18n.t('Add to chat')}</button
									>{/if}
							</div>
							{#if item.body?.trim()}<div
									class="markdown-prose-xs max-w-none break-words text-gray-800 dark:text-gray-200"
								>
									<Markdown
										id={`pr-${selected.number}-activity-${index}`}
										content={item.body}
										allowHtml={false}
										allowEmbeds={false}
										editCodeBlock={false}
									/>
								</div>{/if}
						</div>{/each}
					{#if !activity.length}<div
							class="flex h-full items-center justify-center p-3 text-center text-[0.6875rem] text-gray-400 dark:text-gray-600"
						>
							{$i18n.t('No activity')}
						</div>{/if}
				</div>
				<form
					class="border-t border-gray-100/50 dark:border-white/2 px-2 pb-1.5 shrink-0"
					on:submit|preventDefault={() => mutate('comment')}
				>
					<textarea
						class="block w-full px-1 py-1.5 bg-transparent text-[0.6875rem] text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-600 outline-none resize-none"
						aria-label={$i18n.t('Comment')}
						placeholder={$i18n.t('Leave a comment')}
						rows="2"
						bind:value={comment}
					></textarea>
					<div class="flex items-center gap-1 mt-1">
						{#if selected.state === 'OPEN'}<button
								type="button"
								class="h-6 px-2.5 rounded-lg text-[0.6875rem] font-normal transition-colors duration-75 {secondaryButton}"
								disabled={busy}
								on:click={() => confirm('approve')}>{$i18n.t('Approve')}</button
							><button
								type="button"
								class="h-6 px-2.5 rounded-lg text-[0.6875rem] font-normal transition-colors duration-75 {secondaryButton}"
								disabled={busy || !comment.trim()}
								on:click={() => confirm('request-changes')}>{$i18n.t('Request changes')}</button
							>{/if}
						<button
							class="flex-1 h-6 rounded-lg text-[0.6875rem] font-normal transition-colors duration-75 {!busy &&
							comment.trim()
								? primaryButton
								: disabledButton}"
							disabled={busy || !comment.trim()}>{$i18n.t('Comment')}</button
						>
					</div>
				</form>
			{/if}
		{:else}<div
				class="flex h-full items-center justify-center p-3 text-center text-[0.6875rem] text-gray-400 dark:text-gray-600"
			>
				{$i18n.t('Select a pull request')}
			</div>{/if}
	</div>
</div>

<ConfirmDialog
	bind:show={confirmation}
	title={actionLabels[pendingAction] ?? $i18n.t('Confirm pull request action')}
	message={selected ? `#${selected.number} · ${selected.title}` : ''}
	on:confirm={() => mutate(pendingAction)}
/>
