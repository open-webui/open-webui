<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import { gitRequest } from '$lib/apis/terminal/git';
	import type { TerminalTarget } from '$lib/apis/terminal';
	import Icon from '../FileNav/Icon.svelte';
	import GitListDivider from './GitListDivider.svelte';
	import Dropdown from '../../common/Dropdown.svelte';
	import DropdownMenu from '../../common/DropdownMenu.svelte';
	import Tooltip from '../../common/Tooltip.svelte';
	import Markdown from '../Messages/Markdown.svelte';
	import { copyToClipboard } from '$lib/utils';
	import {
		primaryButton,
		disabledButton,
		secondaryButton,
		relativeTime,
		issuePrompt
	} from './gitPanel';
	export let target: TerminalTarget;

	export let directory: string;
	export let listWidth = 240;
	export let maxListWidth = 240;
	export let onResizeList: (width: number) => void = () => {};
	export let onChange: () => void = () => {};
	// Drafts text into the chat composer; the chat actions are hidden without it.
	export let onDraft: ((text: string) => void) | null = null;
	type Issue = {
		number: number;
		title: string;
		state: string;
		stateReason?: string;
		author?: { login: string };
		labels?: { name: string }[];
		assignees?: { login?: string; name?: string }[];
		url: string;
		updatedAt?: string;
		createdAt?: string;
		body?: string;
		comments?: { id?: string; body: string; createdAt?: string; author?: { login: string } }[];
	};
	const i18n = getContext<any>('i18n');
	let issues: Issue[] = [];
	let selected: Issue | null = null;
	let state = 'open';
	let search = '';
	let listLoading = false;
	let loading = false;
	let busy = false;
	let listError = '';
	let error = '';
	let editing = false;
	let creating = false;
	let title = '';
	let body = '';
	let comment = '';
	let listGeneration = 0;
	let generation = 0;

	$: states = [
		{ value: 'open', label: $i18n.t('Open') },
		{ value: 'closed', label: $i18n.t('Closed') },
		{ value: 'all', label: $i18n.t('All') }
	];
	$: filtered = issues.filter((issue) =>
		`${issue.number} ${issue.title}`.toLowerCase().includes(search.toLowerCase())
	);
	$: showingDetail = !!selected || creating || editing;

	const status = (issue: Issue) =>
		issue.state === 'OPEN'
			? $i18n.t('Open')
			: issue.stateReason === 'NOT_PLANNED'
				? $i18n.t('Not planned')
				: issue.stateReason === 'DUPLICATE'
					? $i18n.t('Duplicate')
					: $i18n.t('Closed');
	const people = (list?: { login?: string; name?: string }[]) =>
		list?.map((person) => person.login || person.name).join(', ') || $i18n.t('None');

	const copy = async (text: string) => {
		if (!(await copyToClipboard(text))) error = $i18n.t('Could not copy to clipboard');
	};
	const commentPrompt = (issue: Issue, item: NonNullable<Issue['comments']>[number]) =>
		[
			$i18n.t('Comment from @{{author}} on issue #{{number}} ({{title}}):', {
				author: item.author?.login ?? 'unknown',
				number: issue.number,
				title: issue.title
			}),
			item.body
				.trim()
				.split('\n')
				.map((line) => `> ${line}`)
				.join('\n')
		].join('\n\n');

	const request = <T,>(
		operation: string,
		params: Record<string, string> = {},
		payload?: Record<string, unknown>
	) => gitRequest<T>(target, directory, `issue/${operation}`, params, payload);
	const load = async () => {
		const version = ++listGeneration;
		listLoading = true;
		listError = '';
		try {
			const data = await request<{ items: Issue[] }>('list', { state });
			if (version === listGeneration) issues = data.items;
		} catch (reason) {
			if (version === listGeneration)
				listError = String(reason instanceof Error ? reason.message : reason);
		} finally {
			if (version === listGeneration) listLoading = false;
		}
	};
	const select = async (issue: Issue) => {
		const version = ++generation;
		selected = issue;
		creating = editing = false;
		loading = true;
		error = '';
		try {
			const data = await request<Issue>('view', { number: String(issue.number) });
			if (version === generation) selected = data;
		} catch (reason) {
			if (version === generation) error = String(reason instanceof Error ? reason.message : reason);
		} finally {
			if (version === generation) loading = false;
		}
	};
	const mutate = async (action: string, reason = 'completed') => {
		if (busy) return;
		busy = true;
		error = '';
		try {
			await request(
				action,
				{},
				{
					number: selected?.number ?? 0,
					title,
					body: ['create', 'edit'].includes(action) ? body : comment,
					reason
				}
			);
			const wasCreating = creating;
			creating = editing = false;
			comment = '';
			onChange();
			void load();
			if (selected && !wasCreating) await select(selected);
		} catch (reason) {
			error = String(reason instanceof Error ? reason.message : reason);
		} finally {
			busy = false;
		}
	};
	const startCreate = () => {
		++generation;
		loading = false;
		error = '';
		selected = null;
		editing = false;
		creating = true;
		title = body = '';
	};
	const back = () => {
		++generation;
		selected = null;
		creating = editing = false;
		error = '';
		loading = false;
	};
	const cancelForm = () => {
		if (editing) editing = false;
		else back();
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
				aria-label={$i18n.t('Search issues')}
				placeholder={$i18n.t('Search issues')}
				bind:value={search}
			/>
			<Dropdown align="end" closeOnSelect>
				<button
					class="flex shrink-0 items-center gap-1 h-6 px-1.5 rounded-md text-gray-400 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors duration-75"
					aria-label={$i18n.t('Filter issues')}
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
									issues = [];
									void load();
								}}
								><span class="flex-1 text-left">{option.label}</span
								>{#if state === option.value}<Icon name="check" size={11} />{/if}</button
							>{/each}
					</DropdownMenu>
				</div>
			</Dropdown>
			<Tooltip content={$i18n.t('New issue')}>
				<button
					class="flex items-center justify-center w-5 h-5 rounded shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
					aria-label={$i18n.t('New issue')}
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
			{#each filtered as issue (issue.number)}<button
					class="flex w-full min-w-0 flex-col px-2.5 py-1.5 text-left border-b border-gray-50/50 dark:border-white/2 transition-colors duration-75 {selected?.number ===
					issue.number
						? 'bg-gray-100/40 dark:bg-gray-800/25'
						: 'hover:bg-gray-100/30 dark:hover:bg-gray-800/20'}"
					on:click={() => select(issue)}
					><span class="w-full truncate text-xs text-gray-800 dark:text-gray-200"
						>{issue.title}</span
					><span class="w-full truncate text-[0.625rem] font-mono text-gray-400 dark:text-gray-600"
						>#{issue.number}{issue.author?.login ? ` · ${issue.author.login}` : ''}{issue.updatedAt
							? ` · ${relativeTime(issue.updatedAt)}`
							: ''}{issue.state !== 'OPEN' ? ` · ${status(issue)}` : ''}</span
					></button
				>{/each}
			{#if !filtered.length}<div
					class="flex h-full items-center justify-center p-3 text-center text-[0.6875rem] text-gray-400 dark:text-gray-600"
				>
					{$i18n.t(listLoading ? 'Loading...' : 'No issues')}
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
				<button class="@min-[560px]:hidden" aria-label={$i18n.t('Back to issues')} on:click={back}
					><Icon name="chevron-left" size={12} /></button
				><span class="min-w-0 flex-1 truncate"
					>{selected && !creating
						? `#${selected.number} · ${selected.title}`
						: $i18n.t('New issue')}</span
				>
				{#if onDraft && selected && !creating && !editing && !loading}<button
						class="flex shrink-0 items-center gap-1 h-5 px-1.5 rounded-md font-sans text-[0.625rem] text-gray-500 dark:text-gray-400 hover:bg-gray-100/50 hover:text-gray-800 dark:hover:bg-white/5 dark:hover:text-gray-200 transition-colors duration-75"
						on:click={() => selected && onDraft?.(issuePrompt($i18n.t, selected))}
						><Icon name="chat-plus" size={11} />{$i18n.t('Work on this')}</button
					>{/if}
				{#if selected && !creating && !editing}<Dropdown side="top" align="end" closeOnSelect
						><button
							class="flex items-center justify-center w-5 h-5 rounded shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
							aria-label={$i18n.t('Issue actions')}><Icon name="three-dots" size={12} /></button
						>
						<div slot="content">
							<DropdownMenu className="w-44">
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
										on:click={() => mutate('close', 'completed')}
										><Icon name="check" size={13} />{$i18n.t('Close as completed')}</button
									><button disabled={busy} on:click={() => mutate('close', 'not planned')}
										><Icon name="xmark" size={13} />{$i18n.t('Close as not planned')}</button
									>{:else}<button disabled={busy} on:click={() => mutate('reopen')}
										><Icon name="undo" size={13} />{$i18n.t('Reopen')}</button
									>{/if}
								<a href={selected.url} target="_blank" rel="noopener noreferrer"
									><Icon name="external-link" size={13} />{$i18n.t('Open in GitHub')}</a
								>
								<button on:click={() => selected && copy(selected.url)}
									><Icon name="copy" size={13} />{$i18n.t('Copy link')}</button
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
						aria-label={$i18n.t('Issue title')}
						placeholder={$i18n.t('Title')}
						bind:value={title}
						required
					/>
					<textarea
						class="block w-full px-1 py-1 bg-transparent text-[0.6875rem] text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-600 outline-none resize-none border-t border-gray-100/50 dark:border-white/2"
						aria-label={$i18n.t('Issue description')}
						placeholder={$i18n.t('Description')}
						rows="8"
						bind:value={body}
					></textarea>
				</div>
				<div
					class="flex items-center justify-end gap-1 px-2 py-1.5 shrink-0 border-t border-gray-100/50 dark:border-white/2"
				>
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
						disabled={busy || !title.trim()}>{$i18n.t(editing ? 'Save' : 'Create issue')}</button
					>
				</div>
			</form>
		{:else if selected}
			{#if loading}<div
					class="flex flex-1 items-center justify-center p-3 text-center text-[0.6875rem] text-gray-400 dark:text-gray-600"
				>
					{$i18n.t('Loading...')}
				</div>
			{:else}
				<div class="min-h-0 flex-1 overflow-y-auto scrollbar-hidden">
					<div class="px-2.5 py-2">
						<dl class="grid grid-cols-[5rem_minmax(0,1fr)] gap-x-3 gap-y-1">
							<dt class="text-gray-400 dark:text-gray-600">{$i18n.t('Author')}</dt>
							<dd class="truncate text-gray-700 dark:text-gray-300">
								{selected.author?.login ?? $i18n.t('Unknown')}
							</dd>
							<dt class="text-gray-400 dark:text-gray-600">{$i18n.t('Status')}</dt>
							<dd class="truncate text-gray-700 dark:text-gray-300">{status(selected)}</dd>
							<dt class="text-gray-400 dark:text-gray-600">{$i18n.t('Assignees')}</dt>
							<dd class="truncate text-gray-700 dark:text-gray-300">
								{people(selected.assignees)}
							</dd>
							<dt class="text-gray-400 dark:text-gray-600">{$i18n.t('Labels')}</dt>
							<dd class="truncate text-gray-700 dark:text-gray-300">
								{selected.labels?.map((item) => item.name).join(', ') || $i18n.t('None')}
							</dd>
							{#if selected.createdAt}<dt class="text-gray-400 dark:text-gray-600">
									{$i18n.t('Opened')}
								</dt>
								<dd class="truncate font-mono text-[0.625rem] text-gray-700 dark:text-gray-300">
									{relativeTime(selected.createdAt)}
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
									id={`issue-${selected.number}-body`}
									content={selected.body}
									allowHtml={false}
									allowEmbeds={false}
									editCodeBlock={false}
								/>
							</div>{:else}<div class="text-xs text-gray-400 dark:text-gray-600">
								{$i18n.t('No description')}
							</div>{/if}
					</div>
					{#if selected.comments?.length}<div
							class="px-2.5 pt-2 pb-1 border-t border-gray-100/50 dark:border-white/2 text-[0.625rem] leading-none uppercase text-gray-400 dark:text-gray-600"
						>
							{$i18n.t('Comments')}
						</div>
						{#each selected.comments as item, index}<div
								class="group px-2.5 py-1.5 border-b border-gray-50/50 dark:border-white/2"
							>
								<div class="flex min-w-0 items-center gap-1.5 h-5">
									<span
										class="min-w-0 flex-1 truncate font-mono text-[0.625rem] text-gray-400 dark:text-gray-600"
										>{item.author?.login ?? $i18n.t('Unknown')}{item.createdAt
											? ` · ${relativeTime(item.createdAt)}`
											: ''}</span
									>{#if onDraft && item.body?.trim()}<button
											class="opacity-0 group-hover:opacity-100 focus:opacity-100 flex shrink-0 items-center gap-1 h-5 px-1.5 rounded-md font-sans text-[0.625rem] text-gray-500 dark:text-gray-400 hover:bg-gray-100/50 hover:text-gray-800 dark:hover:bg-white/5 dark:hover:text-gray-200 transition-colors duration-75"
											on:click={() => selected && onDraft?.(commentPrompt(selected, item))}
											><Icon name="chat-plus" size={11} />{$i18n.t('Add to chat')}</button
										>{/if}
								</div>
								<div
									class="markdown-prose-xs max-w-none break-words text-gray-800 dark:text-gray-200"
								>
									<Markdown
										id={`issue-${selected.number}-comment-${index}`}
										content={item.body}
										allowHtml={false}
										allowEmbeds={false}
										editCodeBlock={false}
									/>
								</div>
							</div>{/each}{/if}
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
						<button
							type="button"
							class="h-6 px-2.5 rounded-lg text-[0.6875rem] font-normal transition-colors duration-75 {secondaryButton}"
							disabled={busy}
							on:click={() =>
								selected?.state === 'OPEN' ? mutate('close', 'completed') : mutate('reopen')}
							>{$i18n.t(
								selected.state === 'OPEN'
									? comment.trim()
										? 'Close with comment'
										: 'Close issue'
									: comment.trim()
										? 'Reopen with comment'
										: 'Reopen'
							)}</button
						>
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
				{$i18n.t('Select an issue')}
			</div>{/if}
	</div>
</div>
