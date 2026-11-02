<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import type { TerminalConnection } from '$lib/apis/terminal';
	import { gitRequest, type GitFile } from '$lib/apis/terminal/git';
	import GitDiff from '../ChatTabs/GitDiff.svelte';
	import Spinner from '../../common/Spinner.svelte';

	export let connection: TerminalConnection | null;
	export let chatId: string | null;
	export let root: string;
	export let file: GitFile | null;
	export let active = true;
	export let mode: 'unified' | 'split' = 'unified';
	export let hideWhitespace = false;
	export let resourceVersion = 0;
	const i18n = getContext<any>('i18n');
	let diff = '';
	let loading = false;
	let error = '';
	let generation = 0;

	const load = async (
		server: TerminalConnection | null,
		session: string | null,
		directory: string,
		entry: GitFile | null,
		enabled: boolean,
		ignoreWhitespace: boolean,
		_version: number
	) => {
		const current = ++generation;
		if (!enabled || !server) return;
		error = '';
		if (!entry || entry.binary) {
			diff = '';
			loading = false;
			return;
		}
		loading = true;
		try {
			const result = await gitRequest<{ diff: string }>(server, session, directory, 'diff', {
				file: entry.path,
				staged: String(entry.staged && !entry.unstaged),
				untracked: String(entry.status === 'untracked'),
				ignore_whitespace: String(ignoreWhitespace)
			});
			if (current === generation) diff = result.diff;
		} catch (reason) {
			if (current === generation) {
				diff = '';
				error = reason instanceof Error ? reason.message : String(reason);
			}
		} finally {
			if (current === generation) loading = false;
		}
	};
	$: void load(connection, chatId, root, file, active, hideWhitespace, resourceVersion);
	onDestroy(() => {
		++generation;
	});
</script>

<div
	class="h-full min-h-0 overflow-auto scrollbar-hidden"
	role="region"
	aria-label={$i18n.t('File changes')}
	aria-busy={loading}
>
	{#if error}<div role="alert" class="p-3 text-xs text-gray-500 dark:text-gray-400">
			{error}<button
				class="ml-2 underline"
				on:click={() =>
					load(connection, chatId, root, file, active, hideWhitespace, resourceVersion)}
				>{$i18n.t('Retry')}</button
			>
		</div>
	{:else if loading && !diff}<div class="flex h-full items-center justify-center">
			<Spinner className="size-4" />
		</div>
	{:else if file?.binary}<div
			class="flex h-full items-center justify-center p-3 text-xs text-gray-400"
		>
			{$i18n.t('Binary file changed')}
		</div>
	{:else if diff}<GitDiff code={diff} {mode} {hideWhitespace} />
	{:else}<div class="flex h-full items-center justify-center p-3 text-xs text-gray-400">
			{$i18n.t('No changes')}
		</div>{/if}
</div>
