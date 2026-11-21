<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import type { TerminalTarget } from '$lib/apis/machines';
	import { cloneRepository } from '$lib/apis/machines/git';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Icon from './Icon.svelte';

	const i18n = getContext<any>('i18n');
	export let terminal: TerminalTarget;

	export let directory: string;
	export let disabled = false;
	export let onCloned: (path: string) => void;
	export let onCancel: () => void;
	let url = '';
	let cloning = false;
	let cloningDirectory = '';
	let error = '';
	const controller = new AbortController();
	onDestroy(() => controller.abort());

	async function submit() {
		if (disabled || cloning) return;
		cloning = true;
		cloningDirectory = directory;
		error = '';
		try {
			const path = await cloneRepository(terminal, directory, url, controller.signal);
			if (!controller.signal.aborted) onCloned(path);
		} catch (err) {
			if (!controller.signal.aborted)
				error = err instanceof Error ? err.message : $i18n.t('Failed to clone repository');
		} finally {
			cloning = false;
		}
	}
</script>

<form class="space-y-2 text-xs" on:submit|preventDefault={submit} aria-busy={cloning}>
	<div class="space-y-2 px-2">
		<label class="block">
			<span class="text-base-600 dark:text-base-400">{$i18n.t('Repository URL')}</span>
			<input
				class="mt-1 w-full h-7 rounded-lg border border-base-100/50 bg-base-50/40 px-2 text-xs text-base-700 outline-hidden transition-colors placeholder:text-base-300 focus:border-blue-400 dark:border-base-0/[0.04] dark:bg-base-0/[0.03] dark:text-base-300 dark:placeholder:text-base-700 dark:focus:border-blue-500 disabled:opacity-50"
				type="text"
				bind:value={url}
				placeholder="https://github.com/owner/repository.git"
				required
				disabled={cloning}
			/>
		</label>

		{#if error}<div
				role="alert"
				class="max-h-24 overflow-y-auto whitespace-pre-wrap break-words text-red-600 dark:text-red-400"
			>
				{error}
			</div>{/if}
	</div>
	<div class="flex items-center gap-2 px-2">
		<div
			class="min-w-0 flex-1 truncate text-base-500"
			title={cloning ? cloningDirectory : directory}
		>
			{$i18n.t('Clone into {{directory}}', { directory: cloning ? cloningDirectory : directory })}
		</div>
		<button
			type="button"
			class="h-7 shrink-0 rounded-lg px-2 hover:bg-base-100 dark:hover:bg-base-850 disabled:opacity-50"
			disabled={cloning}
			on:click={onCancel}>{$i18n.t('Cancel')}</button
		>
		<button
			type="submit"
			class="flex h-7 shrink-0 items-center gap-1.5 rounded-lg bg-base-900 px-2 text-base-0 hover:bg-base-1000 dark:bg-base-100 dark:text-base-900 {cloning
				? 'cursor-wait'
				: 'disabled:cursor-not-allowed disabled:opacity-50'}"
			disabled={disabled || cloning || !url.trim()}
			aria-busy={cloning}
		>
			{#if cloning}<Spinner className="size-4 shrink-0" />{:else}<Icon
					name="git-branch"
					size={14}
				/>{/if}
			{cloning ? $i18n.t('Cloning…') : $i18n.t('Clone repository')}
		</button>
	</div>
</form>
