<script lang="ts">
	import { getContext, onDestroy, onMount } from 'svelte';
	import { getTerminalFeatures, type TerminalConnection } from '$lib/apis/terminal';
	import { watchTerminalFiles } from '$lib/apis/terminal/events';
	import {
		gitRequest,
		gitAction,
		gitRemoteWebUrl,
		type GitStatus,
		type GitFile,
		type GitCommit,
		type GitBranch
	} from '$lib/apis/terminal/git';
	import Icon from '../FileNav/Icon.svelte';
	import GitDiff from './GitDiff.svelte';
	import { parseDiffRows } from '../Messages/diff';
	import Dropdown from '../../common/Dropdown.svelte';
	import DropdownMenu from '../../common/DropdownMenu.svelte';
	import ConfirmDialog from '../../common/ConfirmDialog.svelte';
	import Tooltip from '../../common/Tooltip.svelte';
	import GitPullRequests from './GitPullRequests.svelte';

	export let connection: TerminalConnection | null = null;
	export let directory = '.';
	export let chatId: string | null = null;
	export let active = false;
	export let onOpenFile: (path: string) => void = () => {};
	export let onOpenDirectory: (path: string) => void = () => {};
	const i18n = getContext<any>('i18n');
	export let status: GitStatus | null = null;
	let expanded = false;
	export let diffMode: 'unified' | 'split' = 'unified';
	export let hideWhitespace = false;
	let view: 'changes' | 'history' | 'pull requests' = 'changes';
	let prCapabilities: { available: boolean; default_branch?: string } | null = null;
	let prRoot = '';
	let selected: { path: string; staged: boolean; untracked: boolean } | null = null;
	let selectedCommit: GitCommit | null = null;
	let diff = '';
	$: diffStats = parseDiffRows(diff).reduce(
		(counts, row) => {
			if (row.type === 'addition') counts.additions++;
			if (row.type === 'deletion') counts.deletions++;
			return counts;
		},
		{ additions: 0, deletions: 0 }
	);
	let commits: GitCommit[] = [];
	let branches: GitBranch[] = [];
	let branchSearch = '';
	let newBranch = '';
	let creatingBranch = false;
	let creatingWorktree = false;
	let actionBranch: GitBranch | null = null;
	let worktreeSearch = '';

	let showBranches = false;
	let showWorktrees = false;
	let worktrees: { path: string; branch: string; current: boolean }[] = [];
	let worktreePath = '';
	let worktreeBranch = '';
	let showRename = false;
	let showUncommit = false;
	let showDeleteBranch = false;
	let summary = '';
	let description = '';
	let error = '';
	let detectionError = '';
	let busy = false;
	let loadingDiff = false;
	let confirmDiscard = false;
	let discardFile: GitFile | null = null;
	let height = 280;
	let resizing = false;
	let resizeY = 0;
	let resizeHeight = 0;
	let mounted = false;
	let context = '';
	let generation = 0;
	let diffGeneration = 0;
	let stopWatching: (() => void) | undefined;
	let watchError = '';
	let gitEnabled = false;
	let configuration = 0;
	let pending: Promise<void> | null = null;
	let syncAction: 'publish' | 'pull' | 'push' | 'fetch';
	$: staged = status?.files.filter((file) => file.staged) ?? [];
	$: allStaged =
		!!status?.files.length && status.files.every((file) => file.staged && !file.unstaged);
	$: someStaged = staged.length > 0 && !allStaged;
	$: additions = status?.files.reduce((sum, file) => sum + file.additions, 0) ?? 0;
	$: deletions = status?.files.reduce((sum, file) => sum + file.deletions, 0) ?? 0;
	$: branchLabel = status?.branch === '(detached)' ? status.head?.slice(0, 7) : status?.branch;
	$: remoteWebUrl = gitRemoteWebUrl(status?.remote_url);
	$: remoteHost = remoteWebUrl ? new URL(remoteWebUrl).hostname : '';
	$: remotePlatform =
		remoteHost === 'github.com'
			? 'GitHub'
			: remoteHost.includes('gitlab')
				? 'GitLab'
				: remoteHost === 'bitbucket.org'
					? 'Bitbucket'
					: remoteHost;
	$: syncAction = !status?.upstream
		? 'publish'
		: status.behind > 0
			? 'pull'
			: status.ahead > 0
				? 'push'
				: 'fetch';
	$: syncLabel = { publish: 'Publish', pull: 'Pull', push: 'Push', fetch: 'Fetch' }[syncAction];
	$: syncIcon = { publish: 'upload', pull: 'download', push: 'upload', fetch: 'refresh' }[
		syncAction
	];

	const relativeTime = (date: string) => {
		const seconds = Math.max(0, Math.floor((Date.now() - new Date(date).getTime()) / 1000));
		return seconds < 60
			? 'now'
			: seconds < 3600
				? `${Math.floor(seconds / 60)}m`
				: seconds < 86400
					? `${Math.floor(seconds / 3600)}h`
					: `${Math.floor(seconds / 86400)}d`;
	};
	const request = <T,>(
		operation: string,
		params: Record<string, string> = {},
		body?: Record<string, unknown>
	) => gitRequest<T>(connection!, chatId, status?.root ?? directory, operation, params, body);
	const refresh = (force = false): Promise<void> => {
		if (!connection || !active || !gitEnabled || (!force && document.hidden))
			return Promise.resolve();
		if (pending) return pending;
		const current = generation;
		const task = gitRequest<GitStatus>(connection, chatId, directory, 'status')
			.then((next) => {
				if (current !== generation) return;
				detectionError = '';
				if (status?.root && status.root !== next.root) resetSelection();
				status = next.is_repo ? next : null;
				if (next.root && next.root !== prRoot) {
					prRoot = next.root;
					void request<{ available: boolean; default_branch?: string }>('pr/capabilities')
						.then((data) => {
							if (current === generation) prCapabilities = data;
						})
						.catch(() => {
							if (current === generation) prCapabilities = null;
						});
				}
				if (
					selected &&
					!(next.files ?? []).some(
						(file) =>
							file.path === selected?.path && (selected.staged ? file.staged : file.unstaged)
					)
				)
					resetSelection();
			})
			.catch((reason) => {
				if (current === generation) {
					status = null;
					detectionError = String(reason instanceof Error ? reason.message : reason);
				}
			})
			.finally(() => {
				if (current === generation) pending = null;
			});
		pending = task;
		return task;
	};
	const resetSelection = () => {
		++diffGeneration;
		selected = null;
		selectedCommit = null;
		diff = '';
		loadingDiff = false;
	};
	const configure = async (key: string, enabled: boolean) => {
		const version = ++configuration;
		stopWatching?.();
		stopWatching = undefined;
		watchError = '';
		gitEnabled = false;
		if (key !== context) {
			context = key;
			++generation;
			pending = null;
			status = null;
			error = '';
			detectionError = '';
			expanded = false;
			showBranches =
				showWorktrees =
				showRename =
				showUncommit =
				showDeleteBranch =
				confirmDiscard =
					false;
			summary = description = '';
			commits = [];
			prCapabilities = null;
			prRoot = '';
			view = 'changes';
			resetSelection();
		}
		if (enabled && connection) {
			const features = await getTerminalFeatures(connection, chatId);
			if (version !== configuration || !mounted) return;
			gitEnabled = features.git === true;
			if (!gitEnabled) {
				status = null;
				return;
			}
			void refresh();
			if (features.events !== true) return;
			const current = generation;
			stopWatching = watchTerminalFiles(
				connection,
				chatId,
				directory,
				async () => {
					// An event arriving during a status request must refresh after that request.
					await pending;
					if (current === generation) await refresh();
				},
				(message) => {
					watchError = message;
				}
			);
		}
	};
	$: configure(JSON.stringify([connection, chatId, directory]), mounted && active);

	const selectFile = async (file: GitFile, staged: boolean) => {
		resetSelection();
		selected = { path: file.path, staged, untracked: file.status === 'untracked' };
		const version = diffGeneration;
		loadingDiff = true;
		error = '';
		try {
			const result = await request<{ diff: string }>('diff', {
				file: file.path,
				staged: String(staged),
				untracked: String(selected.untracked)
			});
			if (version === diffGeneration) diff = result.diff;
		} catch (reason) {
			if (version === diffGeneration)
				error = String(reason instanceof Error ? reason.message : reason);
		} finally {
			if (version === diffGeneration) loadingDiff = false;
		}
	};
	const loadHistory = async () => {
		const current = generation;
		try {
			const data = await request<GitCommit[]>('log');
			if (current === generation) commits = data;
		} catch (reason) {
			if (current === generation) error = String(reason instanceof Error ? reason.message : reason);
		}
	};
	const selectCommit = async (commit: GitCommit) => {
		resetSelection();
		selectedCommit = commit;
		const version = diffGeneration;
		loadingDiff = true;
		try {
			const result = await request<{ diff: string }>('show', { ref: commit.hash });
			if (version === diffGeneration) diff = result.diff;
		} catch (reason) {
			if (version === diffGeneration)
				error = String(reason instanceof Error ? reason.message : reason);
		} finally {
			if (version === diffGeneration) loadingDiff = false;
		}
	};
	const loadBranches = async (show: boolean) => {
		creatingBranch = false;
		if (!show) return;
		const current = generation;
		try {
			const data = await request<GitBranch[]>('branches');
			if (current === generation) branches = data;
		} catch (reason) {
			if (current === generation) error = String(reason instanceof Error ? reason.message : reason);
		}
	};
	const loadWorktrees = async (show: boolean) => {
		creatingWorktree = false;
		if (!show) return;
		const current = generation;
		try {
			const data = await request<typeof worktrees>('worktrees');
			if (current === generation) worktrees = data;
		} catch (reason) {
			if (current === generation) error = String(reason instanceof Error ? reason.message : reason);
		}
	};
	const act = async (action: string, fields: Record<string, unknown> = {}) => {
		if (busy) return;
		const current = generation;
		busy = true;
		error = '';
		try {
			const result = await gitAction<{ path?: string }>(
				connection!,
				chatId,
				status?.root ?? directory,
				action,
				fields
			);
			if (current !== generation) return;
			if (action === 'commit') summary = description = '';
			showBranches = false;
			showWorktrees = false;
			resetSelection();
			await pending;
			await refresh(true);
			if (view === 'history') await loadHistory();
			if (action === 'worktree' && result.path) onOpenDirectory(result.path);
		} catch (reason) {
			if (current === generation) error = String(reason instanceof Error ? reason.message : reason);
		} finally {
			busy = false;
		}
	};
	const paths = (files: GitFile[]) => [
		...new Set(
			files.flatMap((file) => [file.path, ...(file.original_path ? [file.original_path] : [])])
		)
	];
	const toggle = () => {
		expanded = !expanded;
		if (expanded) {
			void refresh(true);
			if (view === 'history') void loadHistory();
		}
	};
	const visibility = () => {
		if (!document.hidden) void refresh();
	};
	onMount(() => {
		mounted = true;
		document.addEventListener('visibilitychange', visibility);
		return () => document.removeEventListener('visibilitychange', visibility);
	});
	onDestroy(() => {
		mounted = false;
		++configuration;
		++generation;
		++diffGeneration;
		stopWatching?.();
	});
</script>

{#if status?.is_repo}
	<section
		class="git-panel relative shrink-0 border-t border-gray-100/50 dark:border-white/2"
		aria-label={$i18n.t('Git')}
	>
		{#if expanded}
			<div
				role="separator"
				aria-label={$i18n.t('Resize Git panel')}
				aria-orientation="horizontal"
				aria-valuenow={height}
				tabindex="0"
				class="absolute inset-x-0 -top-px h-px z-20 cursor-row-resize touch-none border-t border-transparent hover:border-gray-200 dark:hover:border-gray-800 transition"
				on:pointerdown={(event) => {
					event.preventDefault();
					(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
					resizing = true;
					resizeY = event.clientY;
					resizeHeight = height;
				}}
				on:pointermove={(event) => {
					if (resizing)
						height = Math.max(
							140,
							Math.min(window.innerHeight * 0.65, resizeHeight + resizeY - event.clientY)
						);
				}}
				on:pointerup={() => (resizing = false)}
				on:pointercancel={() => (resizing = false)}
				on:keydown={(event) => {
					if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
						event.preventDefault();
						height = Math.max(
							140,
							Math.min(window.innerHeight * 0.65, height + (event.key === 'ArrowUp' ? 20 : -20))
						);
					}
				}}
			>
				<span class="absolute inset-x-0 -top-1.5 -bottom-1.5 bg-transparent"></span>
			</div>
		{/if}
		<div class="flex min-w-0 items-center h-7 pl-3 pr-1 text-gray-400 dark:text-gray-600">
			<Dropdown side="top" maxHeight="15rem" bind:show={showBranches} onOpenChange={loadBranches}>
				<button
					class="group/selector flex min-w-0 max-w-32 shrink items-center gap-1.5 h-6 -ml-1.5 px-1.5 rounded-md hover:text-gray-700 dark:hover:text-gray-300 transition-colors duration-75"
					aria-label={$i18n.t('Switch branch')}
					disabled={busy}
					><Icon name="git-branch" size={12} /><span
						class="min-w-0 truncate whitespace-nowrap text-[0.6875rem] text-gray-600 dark:text-gray-400 group-hover/selector:text-gray-700 dark:group-hover/selector:text-gray-300"
						>{branchLabel}</span
					><Icon name="chevron-down" size={9} /></button
				>
				<div slot="content">
					<DropdownMenu className="w-56 text-xs">
						<div class="flex items-center gap-1.5 h-6 mt-0.5 mx-2">
							<Icon name="search" size={13} class="text-gray-300 dark:text-gray-600" /><input
								class="min-w-0 flex-1 bg-transparent text-[0.6875rem] text-gray-500 dark:text-gray-400 placeholder:text-gray-300 dark:placeholder:text-gray-600 outline-none"
								aria-label={$i18n.t('Search branches')}
								placeholder={$i18n.t('Search branches')}
								bind:value={branchSearch}
							/>
						</div>

						<div class="max-h-36 overflow-y-auto scrollbar-hidden py-0.5">
							{#each branches.filter((branch) => branch.name
									.toLowerCase()
									.includes(branchSearch.toLowerCase())) as branch}
								<div
									class="group flex items-center gap-1 w-full h-6 rounded-xl text-xs transition-colors duration-75 {branch.current
										? 'bg-gray-100/40 dark:bg-gray-800/25 text-gray-900 dark:text-white'
										: 'text-gray-500 dark:text-gray-400 hover:bg-gray-100/30 dark:hover:bg-gray-800/20'}"
								>
									<button
										class="flex items-center gap-2 min-w-0 flex-1 h-full px-2 text-inherit"
										disabled={busy || branch.current}
										on:click={() => act('checkout', { branch: branch.name })}
										><Icon name="git-branch" size={14} /><span class="flex-1 text-left truncate"
											>{branch.name}</span
										>{#if branch.current}<Icon
												name="check"
												size={12}
												class="text-gray-400 dark:text-gray-500"
											/>{/if}</button
									>
									<Dropdown side="top" align="end" closeOnSelect>
										<button
											class="flex items-center justify-center w-5 h-5 mr-0.5 rounded-lg shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100/30 dark:hover:bg-gray-800/20"
											aria-label={`${$i18n.t('Branch actions')} ${branch.name}`}
											><Icon name="three-dots" size={12} /></button
										>
										<div slot="content">
											<DropdownMenu className="w-40">
												{#if branch.is_local !== false}<button
														disabled={busy}
														on:click={() => {
															actionBranch = branch;
															showBranches = false;
															showRename = true;
														}}><Icon name="pencil" size={13} />{$i18n.t('Rename')}</button
													>{/if}
												<button
													on:click={async () => {
														try {
															await navigator.clipboard.writeText(branch.name);
														} catch {
															error = $i18n.t('Could not copy branch name');
														}
													}}><Icon name="copy" size={13} />{$i18n.t('Copy branch name')}</button
												>
												{#if branch.is_local !== false && !branch.current}<button
														disabled={busy}
														on:click={() => {
															actionBranch = branch;
															showBranches = false;
															showDeleteBranch = true;
														}}><Icon name="xmark" size={13} />{$i18n.t('Delete')}</button
													>{/if}
											</DropdownMenu>
										</div>
									</Dropdown>
								</div>
							{/each}
						</div>
						{#if creatingBranch}<form
								class="flex items-center gap-2 h-7 px-2"
								on:submit|preventDefault={() => act('branch', { branch: newBranch })}
							>
								<Icon name="git-branch" size={14} class="text-gray-400" /><input
									class="min-w-0 flex-1 bg-transparent text-xs outline-none text-gray-900 dark:text-white"
									aria-label={$i18n.t('New branch')}
									placeholder={$i18n.t('New branch')}
									bind:value={newBranch}
								/><button disabled={busy || !newBranch.trim()} aria-label={$i18n.t('Create branch')}
									><Icon name="check" size={12} /></button
								><button
									type="button"
									aria-label={$i18n.t('Cancel')}
									on:click={() => (creatingBranch = false)}><Icon name="xmark" size={12} /></button
								>
							</form>
						{:else}<div>
								<button
									class="flex items-center gap-2 w-full h-7 px-2 rounded-xl text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-white/5"
									on:click={() => (creatingBranch = true)}
									><Icon name="plus" size={14} />{$i18n.t('New branch')}</button
								>
							</div>{/if}
					</DropdownMenu>
				</div>
			</Dropdown>
			<Dropdown side="top" maxHeight="15rem" bind:show={showWorktrees} onOpenChange={loadWorktrees}>
				<button
					class="group/selector flex min-w-0 max-w-32 shrink items-center gap-1.5 h-6 px-1.5 rounded-md hover:text-gray-700 dark:hover:text-gray-300 transition-colors duration-75"
					aria-label={$i18n.t('Worktrees')}
					disabled={busy}
				>
					<Icon name="folder" size={12} /><span
						class="min-w-0 truncate whitespace-nowrap text-[0.6875rem] text-gray-500 dark:text-gray-500 group-hover/selector:text-gray-700 dark:group-hover/selector:text-gray-300"
						>{status.root?.split('/').pop()}</span
					><Icon name="chevron-down" size={9} />
				</button>
				<div slot="content">
					<DropdownMenu className="w-56 text-xs">
						<div class="flex items-center gap-1.5 h-6 mt-0.5 mx-2">
							<Icon name="search" size={13} class="text-gray-300 dark:text-gray-600" /><input
								class="min-w-0 flex-1 bg-transparent text-[0.6875rem] text-gray-500 dark:text-gray-400 placeholder:text-gray-300 dark:placeholder:text-gray-600 outline-none"
								aria-label={$i18n.t('Search worktrees')}
								placeholder={$i18n.t('Search worktrees')}
								bind:value={worktreeSearch}
							/>
						</div>
						<div class="max-h-36 overflow-y-auto scrollbar-hidden py-0.5">
							{#each worktrees.filter((tree) => `${tree.branch} ${tree.path}`
									.toLowerCase()
									.includes(worktreeSearch.toLowerCase())) as tree}<button
									class="flex items-center gap-2 w-full h-6 px-2 rounded-xl text-xs {tree.current
										? 'bg-gray-100 dark:bg-white/6 text-gray-900 dark:text-white'
										: 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-white/5'}"
									disabled={tree.current}
									on:click={() => {
										showWorktrees = false;
										onOpenDirectory(tree.path);
									}}
									><Icon name="folder" size={14} /><span class="min-w-0 flex-1 text-left truncate"
										>{tree.branch || tree.path.split('/').pop()}</span
									><span
										class="min-w-0 max-w-[45%] truncate text-[0.6875rem] text-gray-300 dark:text-gray-600"
										>{tree.path}</span
									>{#if tree.current}<Icon name="check" size={12} />{/if}</button
								>{/each}
						</div>
						{#if creatingWorktree}<form
								class="px-2 py-1 space-y-1"
								on:submit|preventDefault={() =>
									act('worktree', { branch: worktreeBranch, target: worktreePath })}
							>
								<input
									class="w-full h-6 bg-transparent text-xs outline-none"
									aria-label={$i18n.t('Worktree branch')}
									placeholder={$i18n.t('New branch')}
									bind:value={worktreeBranch}
								/><input
									class="w-full h-6 bg-transparent text-xs outline-none"
									aria-label={$i18n.t('Worktree directory')}
									placeholder={$i18n.t('Worktree directory')}
									bind:value={worktreePath}
								/>
								<div class="flex items-center justify-end gap-2">
									<button type="button" on:click={() => (creatingWorktree = false)}
										>{$i18n.t('Cancel')}</button
									><button disabled={busy || !worktreeBranch.trim() || !worktreePath.trim()}
										>{$i18n.t('Create worktree')}</button
									>
								</div>
							</form>
						{:else}<div>
								<button
									class="flex items-center gap-2 w-full h-7 px-2 rounded-xl text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-white/5"
									on:click={() => (creatingWorktree = true)}
									><Icon name="plus" size={14} />{$i18n.t('New worktree')}</button
								>
							</div>{/if}
					</DropdownMenu>
				</div>
			</Dropdown>
			<button
				class="flex flex-1 min-w-0 h-full items-center justify-end gap-1.5 pl-1 mr-2 text-[0.625rem] font-mono text-left whitespace-nowrap"
				aria-label={$i18n.t('Git changes')}
				aria-expanded={expanded}
				on:click={toggle}
			>
				{#if status.files.length}<span class="truncate"
						>{status.files.length} {$i18n.t('changed')}</span
					>{/if}
				{#if additions || deletions}<span class="flex gap-1 shrink-0"
						><span class="text-green-600 dark:text-green-400">+{additions}</span><span
							class="text-gray-500 dark:text-gray-400">-{deletions}</span
						></span
					>{/if}
			</button>
			{#if status.ahead || status.behind}
				<span
					class="flex shrink-0 items-center gap-1.5 text-[0.625rem] font-mono whitespace-nowrap"
				>
					{#if status.ahead}<span>↑{status.ahead}</span>{/if}
					{#if status.behind}<span>↓{status.behind}</span>{/if}
				</span>
			{/if}
			<Tooltip
				content={[$i18n.t(syncLabel), ...(watchError ? [$i18n.t(watchError)] : [])].join('\n')}
			>
				<button
					class="flex shrink-0 items-center justify-center h-6 w-6 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors duration-75"
					aria-label={$i18n.t(syncLabel)}
					on:click={() => act(syncAction)}
					disabled={busy}><Icon name={syncIcon} size={10} /></button
				>
			</Tooltip>
			<button
				class="flex h-6 w-5 items-center justify-center text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 ml-0.5 shrink-0"
				aria-label={expanded ? $i18n.t('Collapse Git panel') : $i18n.t('Expand Git panel')}
				on:click={toggle}><Icon name={expanded ? 'chevron-down' : 'chevron-up'} size={14} /></button
			>
		</div>
		{#if error}<div role="alert" class="px-3 py-2 text-xs text-gray-500 dark:text-gray-400 break-words">
				{error}
			</div>{/if}
		{#if expanded}
			<div
				class="flex flex-col min-h-0 max-h-[65dvh] border-t border-gray-100/50 dark:border-white/2"
				style:height={`${height + 32}px`}
			>
				<div
					class="flex items-center gap-0.5 px-1 h-8 shrink-0 border-b border-gray-100/50 dark:border-white/2"
				>
					{#each ['changes', 'history', ...(prCapabilities?.available ? ['pull requests'] : [])] as section}<button
							class="px-2.5 py-0.5 shrink-0 rounded-md text-[0.6875rem] font-normal transition-colors duration-75 {view ===
							section
								? 'bg-gray-100/40 dark:bg-gray-800/25 text-gray-900 dark:text-white'
								: 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'}"
							on:click={() => {
								view = section as typeof view;
								resetSelection();
								if (view === 'history') void loadHistory();
							}}
							>{$i18n.t(
								section === 'changes'
									? 'Changes'
									: section === 'history'
										? 'History'
										: 'Pull requests'
							)}{#if section === 'changes' && status.files.length}<span
									class="ml-1 text-gray-400 dark:text-gray-500">{status.files.length}</span
								>{/if}</button
						>{/each}
					<div class="flex-1"></div>
					{#if remoteWebUrl}
						<Tooltip content={$i18n.t('View on {{platform}}', { platform: remotePlatform })}>
							<a
								href={remoteWebUrl}
								target="_blank"
								rel="noopener noreferrer"
								aria-label={$i18n.t('View on {{platform}}', { platform: remotePlatform })}
								class="flex items-center justify-center w-5 h-4 py-0.5 rounded-md text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
								><Icon name="external-link" size={10} /></a
							>
						</Tooltip>
					{/if}
					<Dropdown side="top" align="end">
						<button
							class="flex items-center justify-center w-5 h-4 py-0.5 rounded-md text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
							aria-label={$i18n.t('Diff settings')}><Icon name="settings" size={10} /></button
						>
						<div slot="content">
							<DropdownMenu className="w-48"
								><div class="py-0.5 text-xs font-normal">
									<button
										class="flex h-6 w-full items-center gap-2 rounded-xl px-2 text-left text-xs text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-white/6"
										aria-pressed={hideWhitespace}
										on:click={() => (hideWhitespace = !hideWhitespace)}
										><Icon name="code" size={13} /><span class="min-w-0 flex-1 truncate"
											>{$i18n.t('Hide whitespace')}</span
										><span
											class="relative h-3.5 w-6 rounded-full {hideWhitespace
												? 'bg-gray-900 dark:bg-white'
												: 'bg-gray-300 dark:bg-gray-700'}"
											><span
												class="absolute top-0.5 h-2.5 w-2.5 rounded-full {hideWhitespace
													? 'left-3 bg-white dark:bg-black'
													: 'left-0.5 bg-white dark:bg-gray-500'}"
											></span></span
										></button
									>
									<div
										class="px-2 pb-0.5 pt-1 text-[0.625rem] leading-none uppercase text-gray-400 dark:text-gray-600"
									>
										{$i18n.t('Display')}
									</div>
									{#each ['unified', 'split'] as mode}<button
											class="flex h-6 w-full items-center gap-2 rounded-xl px-2 text-left text-xs {diffMode ===
											mode
												? 'bg-gray-100 dark:bg-white/6 text-gray-900 dark:text-white'
												: 'text-gray-500 dark:text-gray-400'}"
											on:click={() => (diffMode = mode as typeof diffMode)}
											><Icon name={mode === 'unified' ? 'list' : 'split-view'} size={13} /><span
												class="flex-1">{$i18n.t(mode === 'unified' ? 'Unified' : 'Split')}</span
											>{#if diffMode === mode}<Icon name="check" size={11} />{/if}</button
										>{/each}
								</div></DropdownMenu
							>
						</div>
					</Dropdown>
				</div>
				{#if view === 'pull requests' && connection && status.root}
					{#key status.root}<GitPullRequests
							mode={diffMode}
							{hideWhitespace}
							{connection}
							{chatId}
							directory={status.root}
							branch={status.branch}
							defaultBranch={prCapabilities?.default_branch ?? 'main'}
							onChange={() => {
								void refresh(true);
							}}
						/>{/key}
				{:else}
					<div class="flex min-h-0 flex-1 overflow-hidden">
						<div
							class="git-list min-w-0 flex-1 flex flex-col overflow-hidden"
							class:showing-diff={!!(selected || selectedCommit)}
						>
							{#if view === 'changes'}
								{#if status.files.length}
									<button
										class="flex min-w-0 items-center gap-1.5 h-7 px-2.5 border-b border-gray-100/50 dark:border-white/2 hover:bg-gray-50 dark:hover:bg-white/3 shrink-0"
										disabled={busy}
										aria-label={$i18n.t(allStaged ? 'Unstage all' : 'Stage all')}
										on:click={() =>
											act(allStaged ? 'unstage' : 'stage', { paths: paths(status?.files ?? []) })}
									>
										<span
											class="flex items-center justify-center w-3 h-3 me-1 rounded border shrink-0 border-gray-300 dark:border-gray-600 {allStaged
												? 'bg-gray-800 dark:bg-white'
												: someStaged
													? 'bg-gray-400 dark:bg-gray-500'
													: ''}"
											>{#if allStaged || someStaged}<Icon
													name={allStaged ? 'check' : 'minus'}
													size={7}
													class="text-white dark:text-black"
												/>{/if}</span
										>
										<span class="min-w-0 truncate text-[0.6875rem] text-gray-600 dark:text-gray-400"
											>{status.files.length}
											{$i18n.t(status.files.length === 1 ? 'changed file' : 'changed files')}</span
										>
									</button>
								{/if}
								<div
									class="min-h-0 min-w-0 flex-1 overflow-x-hidden overflow-y-auto scrollbar-hidden"
								>
									{#each status.files as file (file.path)}
										<div
											class="group flex min-w-0 items-center gap-1.5 w-full h-7 px-2.5 text-left transition-colors duration-75 {selected?.path ===
											file.path
												? 'bg-gray-100/40 dark:bg-gray-800/25'
												: 'hover:bg-gray-50 dark:hover:bg-white/3'}"
										>
											<button
												class="flex items-center justify-center w-3 h-3 me-1 rounded border shrink-0 border-gray-300 dark:border-gray-600 {file.staged
													? 'bg-gray-800 dark:bg-white'
													: 'hover:border-gray-500 dark:hover:border-gray-400'}"
												disabled={busy}
												aria-label={`${$i18n.t(file.staged ? 'Unstage' : 'Stage')} ${file.path}`}
												on:click={() =>
													act(file.staged ? 'unstage' : 'stage', { paths: paths([file]) })}
											>
												{#if file.staged}<Icon
														name={file.unstaged ? 'minus' : 'check'}
														size={7}
														class="text-white dark:text-black"
													/>{/if}
											</button>
											<div class="flex min-w-0 flex-1 items-center gap-0.5 h-full">
												{#if file.path.includes('/')}<button
														class="min-w-0 truncate text-[0.625rem] text-gray-400 dark:text-gray-600"
														aria-label={`${$i18n.t('View changes')} ${file.path}`}
														on:click={() => selectFile(file, file.staged)}
														>{file.path.slice(0, file.path.lastIndexOf('/') + 1)}</button
													>{/if}
												<button
													class="min-w-0 truncate text-[0.6875rem] text-gray-800 dark:text-gray-200 hover:underline"
													aria-label={`${$i18n.t('Open file')} ${file.path}`}
													on:click={() => {
														if (status?.root)
															onOpenFile(`${status.root.replace(/\/$/, '')}/${file.path}`);
													}}>{file.path.split('/').pop()}</button
												>
												<button
													class="min-w-0 flex-1 self-stretch"
													aria-label={`${$i18n.t('View changes')} ${file.path}`}
													on:click={() => selectFile(file, file.staged)}
												></button>
											</div>
											{#if file.binary}<span
													class="text-[0.625rem] font-mono font-normal text-gray-400"
													title={file.status}
													>{file.status === 'untracked' ? 'U' : file.status[0].toUpperCase()}</span
												>{:else}<button
													class="flex shrink-0 items-center gap-1 text-[0.625rem] font-mono font-normal"
													aria-label={`${$i18n.t('View changes')} ${file.path}`}
													on:click={() => selectFile(file, file.staged)}
													><span class="text-green-600 dark:text-green-400">+{file.additions}</span
													><span class="text-gray-500 dark:text-gray-400">-{file.deletions}</span
													></button
												>{/if}
											<Dropdown side="top" align="end" closeOnSelect>
												<button
													class="flex items-center justify-center w-5 h-5 rounded shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
													aria-label={`${$i18n.t('File actions')} ${file.path}`}
													><Icon name="three-dots" size={12} /></button
												>
												<div slot="content">
													<DropdownMenu className="w-44">
														<button
															on:click={() =>
																onOpenFile(`${status?.root?.replace(/\/$/, '')}/${file.path}`)}
															>{$i18n.t('Open file')}</button
														>
														{#if file.staged}<button on:click={() => selectFile(file, true)}
																>{$i18n.t('Staged changes')}</button
															>{/if}
														{#if file.unstaged}<button on:click={() => selectFile(file, false)}
																>{$i18n.t('Working tree changes')}</button
															>{/if}
														{#if file.unstaged && file.status !== 'untracked'}<button
																disabled={busy}
																on:click={() => {
																	discardFile = file;
																	confirmDiscard = true;
																}}>{$i18n.t('Discard changes')}</button
															>{/if}
													</DropdownMenu>
												</div>
											</Dropdown>
										</div>
									{/each}
									{#if !status.files.length}<div
											class="flex h-full items-center justify-center text-[0.6875rem] text-gray-400 dark:text-gray-600"
										>
											{$i18n.t('No changes')}
										</div>{/if}
								</div>
								<form
									class="border-t border-gray-100/50 dark:border-white/2 px-2 pb-1.5 shrink-0"
									on:submit|preventDefault={() =>
										act('commit', {
											message: [summary.trim(), description.trim()].filter(Boolean).join('\n\n')
										})}
								>
									<div class="rounded-lg overflow-hidden">
										<input
											class="w-full h-6 px-1 bg-transparent text-[0.6875rem] text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-600 outline-none"
											aria-label={$i18n.t('Commit summary')}
											placeholder={$i18n.t('Summary')}
											bind:value={summary}
										/>
										<textarea
											class="block w-full px-1 py-1 bg-transparent text-[0.6875rem] text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-600 outline-none resize-none border-t border-gray-100/50 dark:border-white/2"
											rows="3"
											aria-label={$i18n.t('Description')}
											placeholder={$i18n.t('Description')}
											bind:value={description}
										></textarea>
									</div>
									<button
										class="w-full h-6 mt-1 rounded-lg text-[0.6875rem] font-normal transition-colors duration-75 {staged.length &&
										summary.trim()
											? 'bg-gray-900 dark:bg-white text-white dark:text-black hover:bg-gray-800 dark:hover:bg-white/90'
											: 'bg-gray-100 dark:bg-white/6 text-gray-400 dark:text-gray-600 cursor-default'}"
										disabled={busy || !staged.length || !summary.trim()}
									>
										{staged.length
											? $i18n.t(
													staged.length === 1
														? 'Commit {{count}} file to {{branch}}'
														: 'Commit {{count}} files to {{branch}}',
													{ count: staged.length, branch: status.branch }
												)
											: $i18n.t('Commit to {{branch}}', { branch: status.branch })}
									</button>
								</form>
							{:else}
								<div class="min-h-0 flex-1 overflow-y-auto scrollbar-hidden">
									{#each commits as commit, index}<div
											class="group flex min-w-0 items-center border-b border-gray-50/50 dark:border-white/2 transition-colors duration-75 {selectedCommit?.hash ===
											commit.hash
												? 'bg-gray-100/40 dark:bg-gray-800/25'
												: 'hover:bg-gray-100/30 dark:hover:bg-gray-800/20'}"
										>
											<Tooltip content={commit.hash} className="flex min-w-0 flex-1"
												><button
													class="flex min-w-0 flex-1 items-center gap-1.5 px-2.5 py-1.5 text-left"
													on:click={() => selectCommit(commit)}
												>
													{#if index < status.ahead}<span
															class="w-1.5 h-1.5 rounded-full bg-blue-500 dark:bg-blue-400 shrink-0"
															title={$i18n.t('Unpushed')}
														></span>{/if}
													<div class="flex flex-col min-w-0 flex-1">
														<span class="text-xs text-gray-800 dark:text-gray-200 truncate"
															>{commit.message}</span
														><span
															class="text-[0.625rem] text-gray-400 dark:text-gray-600 font-mono truncate"
															>{commit.author} · {relativeTime(commit.date)}</span
														>
													</div>
												</button></Tooltip
											><Dropdown side="top" align="end" closeOnSelect
												><button
													class="flex items-center justify-center w-5 h-5 mr-1 rounded shrink-0 opacity-0 group-hover:opacity-100 focus:opacity-100 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
													aria-label={`${$i18n.t('Commit actions')} ${commit.short_hash}`}
													><Icon name="three-dots" size={12} /></button
												>
												<div slot="content">
													<DropdownMenu className="w-44"
														>{#if index === 0}<button
																disabled={busy}
																on:click={() => (showUncommit = true)}
																><Icon name="undo" size={13} />{$i18n.t('Undo last commit')}</button
															>{/if}<button
															on:click={async () => {
																try {
																	await navigator.clipboard.writeText(commit.hash);
																} catch {
																	error = $i18n.t('Could not copy commit hash');
																}
															}}><Icon name="copy" size={13} />{$i18n.t('Copy commit hash')}</button
														></DropdownMenu
													>
												</div></Dropdown
											>
										</div>{/each}
									{#if !commits.length}<div
											class="flex h-full items-center justify-center text-[0.6875rem] text-gray-400 dark:text-gray-600"
										>
											{$i18n.t('No commits yet')}
										</div>{/if}
								</div>
							{/if}
						</div>
						<div
							class="git-detail min-w-0 flex-1 flex-col overflow-hidden"
							class:showing-diff={!!(selected || selectedCommit)}
						>
							{#if selected || selectedCommit}
								<div
									class="flex items-center gap-2 px-2 h-6 shrink-0 border-b border-gray-100/50 dark:border-white/2 text-[0.625rem] font-mono text-gray-400 dark:text-gray-600"
								>
									<button
										class="git-back"
										aria-label={$i18n.t('Back to changes')}
										on:click={resetSelection}><Icon name="chevron-left" size={12} /></button
									><span class="min-w-0 flex-1 truncate"
										>{selected?.path ??
											`${selectedCommit?.short_hash} · ${selectedCommit?.message}`}</span
									>
									{#if diff && !loadingDiff}<span class="flex shrink-0 items-center gap-1"
											><span class="text-green-600 dark:text-green-400">+{diffStats.additions}</span
											><span class="text-gray-500 dark:text-gray-400">-{diffStats.deletions}</span
											></span
										>{/if}
								</div>
								<div class="min-h-0 flex-1 overflow-auto scrollbar-hidden text-[0.6875rem]">
									{#if loadingDiff}<p class="p-3 text-gray-400">
											{$i18n.t('Loading...')}
										</p>{:else if diff}<GitDiff
											code={diff}
											mode={diffMode}
											{hideWhitespace}
										/>{:else}<div
											class="flex h-full items-center justify-center text-gray-400 dark:text-gray-600"
										>
											{$i18n.t('No text changes')}
										</div>{/if}
								</div>
							{:else}<div
									class="flex h-full items-center justify-center text-[0.6875rem] text-gray-400 dark:text-gray-600"
								>
									{$i18n.t(
										view === 'history'
											? 'Select a commit to view changes'
											: 'Select a file to view changes'
									)}
								</div>{/if}
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</section>
{:else if detectionError}
	<div
		class="flex h-7 shrink-0 items-center gap-1.5 border-t border-gray-100/50 dark:border-white/2 px-3 text-[0.6875rem] text-gray-500 dark:text-gray-400"
	>
		<Icon name="git-branch" size={12} />
		<Tooltip content={detectionError} className="min-w-0 flex-1"
			><span>{$i18n.t('Git unavailable')}</span></Tooltip
		>
		<button
			class="flex h-6 w-6 items-center justify-center rounded-md hover:bg-gray-100/30 dark:hover:bg-gray-800/20"
			aria-label={$i18n.t('Retry Git detection')}
			on:click={() => refresh(true)}><Icon name="refresh" size={12} /></button
		>
	</div>
{/if}

<ConfirmDialog
	bind:show={confirmDiscard}
	title={$i18n.t('Discard changes')}
	message={$i18n.t('Discard unsaved working-tree changes to this file? This cannot be undone.')}
	on:confirm={() => {
		if (discardFile) void act('discard', { paths: paths([discardFile]) });
	}}
/>

<ConfirmDialog
	bind:show={showRename}
	title={$i18n.t('Rename branch')}
	input={true}
	inputValue={actionBranch?.name ?? ''}
	on:confirm={(event) => {
		if (actionBranch)
			void act('rename_branch', { branch: actionBranch.name, target: event.detail });
	}}
/>
<ConfirmDialog
	bind:show={showDeleteBranch}
	title={$i18n.t('Delete branch')}
	message={$i18n.t('Delete branch {{branch}}? Unmerged branches will be kept.', {
		branch: actionBranch?.name ?? ''
	})}
	on:confirm={() => {
		if (actionBranch) void act('delete_branch', { branch: actionBranch.name });
	}}
/>
<ConfirmDialog
	bind:show={showUncommit}
	title={$i18n.t('Undo last commit')}
	message={$i18n.t('Undo the last commit and keep its changes staged?')}
	on:confirm={() => act('uncommit')}
/>

<style>
	.git-panel {
		container-type: inline-size;
	}
	.git-list.showing-diff,
	.git-detail {
		display: none;
	}
	.git-detail.showing-diff {
		display: flex;
	}
	@container (min-width: 560px) {
		.git-list,
		.git-list.showing-diff {
			display: flex;
			flex: 0 0 240px;
			border-inline-end: 1px solid #8080800c;
		}
		.git-detail {
			display: flex;
		}
		.git-back {
			display: none;
		}
	}
	@container (min-width: 800px) {
		.git-list,
		.git-list.showing-diff {
			flex-basis: 288px;
		}
	}
</style>
