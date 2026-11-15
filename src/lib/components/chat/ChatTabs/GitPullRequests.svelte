<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import { gitRequest } from '$lib/apis/terminal/git';
	import type { TerminalConnection } from '$lib/apis/terminal';
	import Icon from '../FileNav/Icon.svelte';
	import GitDiff from './GitDiff.svelte';
	import Dropdown from '../../common/Dropdown.svelte';
	import DropdownMenu from '../../common/DropdownMenu.svelte';
	import ConfirmDialog from '../../common/ConfirmDialog.svelte';
	export let connection: TerminalConnection;
	export let chatId: string | null;
	export let directory: string;
	export let branch: string;
	export let defaultBranch = 'main';
	export let mode: 'unified' | 'split' = 'unified';
	export let hideWhitespace = false;
	export let onChange: () => void = () => {};
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
		statusCheckRollup?: {
			name?: string;
			context?: string;
			status?: string;
			conclusion?: string;
			state?: string;
		}[];
	};
	const i18n = getContext<any>('i18n');
	let prs: PullRequest[] = [];
	let selected: PullRequest | null = null;
	let state = 'open';
	let search = '';
	let view: 'summary' | 'code' | 'checks' | 'activity' = 'summary';
	let diff = '';
	let loading = false;
	let busy = false;
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
	let generation = 0;
	const request = <T,>(
		operation: string,
		params: Record<string, string> = {},
		payload?: Record<string, unknown>
	) => gitRequest<T>(connection, chatId, directory, `pr/${operation}`, params, payload);
	const load = async () => {
		const version = ++generation;
		loading = true;
		error = '';
		try {
			const data = await request<{ items: PullRequest[] }>('list', { state });
			if (version === generation) prs = data.items;
		} catch (reason) {
			if (version === generation) error = String(reason instanceof Error ? reason.message : reason);
		} finally {
			if (version === generation) loading = false;
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
			if (selected && action !== 'create') await select(selected);
			else await load();
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
	const back = () => {
		++generation;
		selected = null;
		creating = editing = false;
		diff = '';
		loading = false;
		void load();
	};
	onMount(() => {
		void load();
	});
	onDestroy(() => {
		++generation;
	});
</script>

<div class="git-pr flex min-h-0 flex-1 text-[0.6875rem]">
	<div
		class="pr-list flex min-h-0 min-w-0 flex-1 flex-col"
		class:has-selection={!!selected || creating || editing}
	>
		<div class="border-b border-gray-100/50 p-2 dark:border-white/2">
			<div class="flex min-w-0 items-center gap-1">
				{#each ['open', 'closed', 'all'] as option}<button
						class="h-6 rounded-md px-2 text-[0.6875rem] font-normal transition-colors duration-75 {state ===
						option
							? 'bg-gray-200/50 text-gray-900 dark:bg-white/8 dark:text-white'
							: 'text-gray-400 hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300'}"
						on:click={() => {
							state = option;
							void load();
						}}>{$i18n.t(option[0].toUpperCase() + option.slice(1))}</button
					>{/each}
			</div>
			<div class="mt-1.5 flex min-w-0 items-center gap-1.5">
				<div
					class="flex h-6 min-w-0 flex-1 items-center gap-1.5 rounded-md border border-gray-200 px-1.5 dark:border-white/8"
				>
					<Icon name="search" size={11} class="shrink-0 text-gray-300 dark:text-gray-600" /><input
						class="min-w-0 flex-1 bg-transparent text-[0.6875rem] text-gray-700 outline-none placeholder:text-gray-300 dark:text-gray-300 dark:placeholder:text-gray-600"
						aria-label={$i18n.t('Search pull requests')}
						placeholder={$i18n.t('Search pull requests')}
						bind:value={search}
					/>
				</div>
				<button
					class="flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-gray-400 hover:bg-gray-100 hover:text-gray-700 dark:text-gray-600 dark:hover:bg-white/6 dark:hover:text-gray-300"
					aria-label={$i18n.t('New pull request')}
					on:click={() => {
						++generation;
						loading = false;
						selected = null;
						editing = false;
						creating = true;
						title = body = '';
						head = branch;
					}}><Icon name="plus" size={13} /></button
				>
			</div>
		</div>
		{#if error && !selected && !creating && !editing}<p
				role="alert"
				class="px-2 py-1 text-gray-500 dark:text-gray-400 break-words"
			>
				{error}
			</p>{/if}
		<div class="min-h-0 flex-1 overflow-y-auto">
			{#if loading}<p class="flex h-full items-center justify-center p-3 text-center text-gray-400">
					{$i18n.t('Loading...')}
				</p>{:else}{#each prs.filter((pr) => `${pr.number} ${pr.title}`
						.toLowerCase()
						.includes(search.toLowerCase())) as pr}<button
						class="flex min-w-0 items-center gap-1.5 w-full px-2.5 py-1.5 text-left border-b border-gray-50/50 dark:border-white/2 {selected?.number ===
						pr.number
							? 'bg-gray-100/40 dark:bg-gray-800/25'
							: 'hover:bg-gray-50 dark:hover:bg-white/3'}"
						on:click={() => select(pr)}
						><Icon name="git-diff" size={12} class="shrink-0 text-gray-400 dark:text-gray-600" />
						<div class="min-w-0 flex-1">
							<div class="truncate text-xs text-gray-800 dark:text-gray-200">
								#{pr.number}
								{pr.title}
							</div>
							<div class="mt-0.5 text-[10px] text-gray-400">
								{pr.author?.login} · {pr.isDraft ? $i18n.t('Draft') : pr.state}
							</div>
						</div></button
					>{/each}{#if !prs.length}<p
						class="flex h-full items-center justify-center p-3 text-center text-gray-400"
					>
						{$i18n.t('No pull requests')}
					</p>{/if}{/if}
		</div>
	</div>
	<div
		class="pr-detail min-w-0 flex-1 flex-col overflow-hidden"
		class:has-selection={!!selected || creating || editing}
	>
		<div
			class="flex items-center gap-2 px-2 h-7 shrink-0 border-b border-gray-100/50 dark:border-white/2 text-gray-500 dark:text-gray-400"
		>
			{#if selected || creating || editing}<button
					class="pr-back"
					aria-label={$i18n.t('Back to pull requests')}
					on:click={back}><Icon name="chevron-left" size={12} /></button
				>{/if}
			{#if selected}<span class="truncate flex-1">#{selected.number} {selected.title}</span
				><Dropdown side="top" align="end" closeOnSelect
					><button aria-label={$i18n.t('Pull request actions')}
						><Icon name="three-dots" size={14} /></button
					>
					<div slot="content">
						<DropdownMenu className="w-44">
							<button disabled={busy} on:click={() => mutate('checkout')}
								>{$i18n.t('Checkout')}</button
							>
							<button
								disabled={busy}
								on:click={() => {
									editing = true;
									title = selected!.title;
									body = selected!.body;
								}}>{$i18n.t('Edit')}</button
							>
							{#if selected.state === 'OPEN'}<button
									disabled={busy}
									on:click={() => mutate('update-branch')}>{$i18n.t('Update branch')}</button
								>{#if selected.isDraft}<button disabled={busy} on:click={() => mutate('ready')}
										>{$i18n.t('Mark ready')}</button
									>{/if}<button disabled={busy} on:click={() => confirm('close')}
									>{$i18n.t('Close pull request')}</button
								>{:else if selected.state === 'CLOSED'}<button
									disabled={busy}
									on:click={() => mutate('reopen')}>{$i18n.t('Reopen')}</button
								>{/if}
							<a href={selected.url} target="_blank" rel="noopener noreferrer"
								>{$i18n.t('Open in GitHub')}</a
							>
						</DropdownMenu>
					</div></Dropdown
				>{/if}
		</div>
		{#if error}<p role="alert" class="px-3 py-1 text-gray-500 dark:text-gray-400 break-words">
				{error}
			</p>{/if}
		{#if creating || editing}
			<form
				class="min-h-0 overflow-y-auto px-3 py-2 space-y-2"
				on:submit|preventDefault={() => mutate(editing ? 'edit' : 'create')}
			>
				<input
					class="w-full rounded-lg border border-gray-200 dark:border-white/8 bg-transparent px-2 py-1.5 text-[0.6875rem] outline-none"
					aria-label={$i18n.t('Pull request title')}
					placeholder={$i18n.t('Title')}
					bind:value={title}
					required
				/>
				<textarea
					class="w-full rounded-lg border border-gray-200 dark:border-white/8 bg-transparent px-2 py-1.5 text-[0.6875rem] outline-none"
					aria-label={$i18n.t('Pull request description')}
					placeholder={$i18n.t('Description')}
					rows="3"
					bind:value={body}
				></textarea>
				{#if creating}<div class="flex gap-2">
						<input
							class="min-w-0 w-1/2 rounded bg-gray-50 dark:bg-white/5 p-1.5 text-xs"
							aria-label={$i18n.t('Base branch')}
							placeholder={$i18n.t('Base branch')}
							bind:value={base}
							required
						/><input
							class="min-w-0 w-1/2 rounded bg-gray-50 dark:bg-white/5 p-1.5 text-xs"
							aria-label={$i18n.t('Head branch')}
							placeholder={$i18n.t('Head branch')}
							bind:value={head}
							required
						/>
					</div>
					<label class="flex gap-2 items-center"
						><input type="checkbox" bind:checked={draft} />{$i18n.t('Draft')}</label
					>{/if}
				<button
					class="rounded bg-gray-100 dark:bg-white/10 px-2 py-1 disabled:opacity-40"
					disabled={busy || !title.trim()}
					>{$i18n.t(editing ? 'Save' : 'Create pull request')}</button
				>
			</form>
		{:else if selected}
			<div
				class="flex gap-1 px-2 h-7 items-center shrink-0 border-b border-gray-100/50 dark:border-white/2"
			>
				{#each ['summary', 'code', 'checks', 'activity'] as tab}<button
						class="h-5 rounded px-1.5 text-[0.625rem] font-normal {view === tab
							? 'bg-gray-200/50 text-gray-900 dark:bg-white/8 dark:text-white'
							: 'text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
						on:click={() => select(selected!, tab as typeof view)}
						>{$i18n.t(tab[0].toUpperCase() + tab.slice(1))}</button
					>{/each}
			</div>
			<div class="min-h-0 flex-1 overflow-auto">
				{#if loading}<p
						class="flex h-full items-center justify-center p-3 text-center text-gray-400"
					>
						{$i18n.t('Loading...')}
					</p>
				{:else if view === 'code'}<GitDiff code={diff} {mode} {hideWhitespace} />
				{:else if view === 'summary'}<div
						class="p-2 text-[0.6875rem] text-gray-600 dark:text-gray-400"
					>
						<div class="grid grid-cols-[5rem_minmax(0,1fr)] gap-x-3 gap-y-1">
							<span class="text-gray-400 dark:text-gray-600">{$i18n.t('Author')}</span><span
								class="truncate">{selected.author?.login ?? 'unknown'}</span
							>
							<span class="text-gray-400 dark:text-gray-600">{$i18n.t('Status')}</span><span
								class="truncate"
								>{selected.isDraft ? $i18n.t('Draft') : selected.state}{selected.reviewDecision
									? ` · ${selected.reviewDecision}`
									: ''}</span
							>
							<span class="text-gray-400 dark:text-gray-600">{$i18n.t('Reviewers')}</span><span
								class="truncate"
								>{selected.reviewRequests
									?.map((person) => person.login || person.name)
									.join(', ') || $i18n.t('none')}</span
							>
							<span class="text-gray-400 dark:text-gray-600">{$i18n.t('Assignees')}</span><span
								class="truncate"
								>{selected.assignees?.map((person) => person.login || person.name).join(', ') ||
									$i18n.t('none')}</span
							>
							<span class="text-gray-400 dark:text-gray-600">{$i18n.t('Labels')}</span><span
								class="truncate"
								>{selected.labels?.map((label) => label.name).join(', ') || $i18n.t('none')}</span
							>
							<span class="text-gray-400 dark:text-gray-600">{$i18n.t('Merge')}</span><span
								class="truncate">{selected.mergeable ?? 'unknown'}</span
							>
						</div>
						<div class="mt-2 border-t border-gray-100/50 pt-2 dark:border-white/2">
							<div class="mb-1 text-[0.625rem] uppercase text-gray-300 dark:text-gray-600">
								{$i18n.t('Description')}
							</div>
							<div
								class="max-h-28 overflow-auto whitespace-pre-wrap text-xs leading-5 text-gray-800 dark:text-gray-200"
							>
								{selected.body || $i18n.t('No description')}
							</div>
						</div>
						<div
							class="mt-2 flex flex-wrap gap-1 border-t border-gray-100/50 pt-2 dark:border-white/2"
						>
							{#if selected.state === 'OPEN'}<button
									class="pr-action"
									disabled={busy}
									on:click={() => mutate('update-branch')}>{$i18n.t('Update')}</button
								>
								{#if selected.isDraft}<button
										class="pr-action"
										disabled={busy}
										on:click={() => mutate('ready')}>{$i18n.t('Ready')}</button
									>{/if}
								{#each ['squash', 'merge', 'rebase'] as method}<button
										class="pr-action"
										disabled={busy || selected.isDraft || selected.mergeable === 'CONFLICTING'}
										on:click={() => {
											mergeMethod = method;
											confirm('merge');
										}}>{$i18n.t(method[0].toUpperCase() + method.slice(1))}</button
									>{/each}
								<button
									class="pr-action text-gray-500 dark:text-gray-400"
									disabled={busy}
									on:click={() => confirm('close')}>{$i18n.t('Close')}</button
								>
							{:else if selected.state === 'CLOSED'}<button
									class="pr-action"
									disabled={busy}
									on:click={() => mutate('reopen')}>{$i18n.t('Reopen')}</button
								>{/if}
						</div>
					</div>
				{:else if view === 'checks'}<div class="h-full min-h-0">
						{#each selected.statusCheckRollup ?? [] as check}<div
								class="flex items-center justify-between gap-2 border-b border-gray-50/50 px-2.5 py-1.5 dark:border-white/2"
							>
								<span class="truncate">{check.name ?? check.context}</span><span
									class="text-gray-400 text-[10px]"
									>{check.conclusion || check.status || check.state}</span
								>
							</div>{/each}{#if !selected.statusCheckRollup?.length}<p
								class="flex h-full items-center justify-center p-3 text-center text-gray-400"
							>
								{$i18n.t('No checks')}
							</p>{/if}
					</div>
				{:else}<div class="p-2 space-y-2">
						{#each [...(selected.comments ?? []), ...(selected.reviews ?? [])] as item}<div>
								<p class="text-[10px] text-gray-400">
									{item.author?.login}{'state' in item ? ` · ${item.state}` : ''}
								</p>
								<p class="whitespace-pre-wrap break-words">{item.body}</p>
							</div>{/each}<textarea
							class="w-full rounded-lg border border-gray-200 dark:border-white/8 bg-transparent px-2 py-1.5 text-[0.6875rem] outline-none"
							aria-label={$i18n.t('Comment')}
							placeholder={$i18n.t('Comment')}
							rows="2"
							bind:value={comment}
						></textarea>
						<div class="flex flex-wrap gap-2">
							<button disabled={busy || !comment.trim()} on:click={() => mutate('comment')}
								>{$i18n.t('Comment')}</button
							>{#if selected.state === 'OPEN'}<button
									disabled={busy}
									on:click={() => confirm('approve')}>{$i18n.t('Approve')}</button
								><button
									disabled={busy || !comment.trim()}
									on:click={() => confirm('request-changes')}>{$i18n.t('Request changes')}</button
								>{/if}
						</div>
					</div>{/if}
			</div>
		{:else}<div
				class="flex flex-1 items-center justify-center p-3 text-center text-gray-400 dark:text-gray-600"
			>
				{$i18n.t('Select a pull request')}
			</div>{/if}
	</div>
</div>

<ConfirmDialog
	bind:show={confirmation}
	title={$i18n.t('Confirm pull request action')}
	message={`${pendingAction} #${selected?.number}: ${selected?.title ?? ''}`}
	on:confirm={() => mutate(pendingAction)}
/>

<style>
	.pr-list.has-selection,
	.pr-detail {
		display: none;
	}
	.pr-detail.has-selection {
		display: flex;
	}
	.pr-action {
		height: 1.5rem;
		border-radius: 0.375rem;
		padding: 0 0.5rem;
		font-size: 0.625rem;
	}
	.pr-action:hover {
		background: #80808010;
	}
	@container (min-width: 560px) {
		.pr-list,
		.pr-list.has-selection {
			display: flex;
			flex: 0 0 240px;
			border-inline-end: 1px solid #8080800c;
		}
		.pr-detail {
			display: flex;
		}
		.pr-back {
			display: none;
		}
	}
	@container (min-width: 800px) {
		.pr-list,
		.pr-list.has-selection {
			flex-basis: 288px;
		}
	}
</style>
