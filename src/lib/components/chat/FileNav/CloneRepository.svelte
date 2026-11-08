<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import { cloneRepository } from '$lib/apis/terminal/git';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Icon from './Icon.svelte';

	const i18n = getContext<any>('i18n');
	export let terminal: { url: string; key: string };
	export let chatId: string | null;
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
			const path = await cloneRepository(
				{ baseUrl: terminal.url, key: terminal.key },
				chatId,
				directory,
				url,
				controller.signal
			);
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
			<span class="text-gray-600 dark:text-gray-400">{$i18n.t('Repository URL')}</span>
			<input
				class="mt-1 w-full h-7 rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500 disabled:opacity-50"
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
			class="min-w-0 flex-1 truncate text-gray-500"
			title={cloning ? cloningDirectory : directory}
		>
			{$i18n.t('Clone into {{directory}}', { directory: cloning ? cloningDirectory : directory })}
		</div>
		<button
			type="button"
			class="h-7 shrink-0 rounded-lg px-2 hover:bg-gray-100 dark:hover:bg-gray-850 disabled:opacity-50"
			disabled={cloning}
			on:click={onCancel}>{$i18n.t('Cancel')}</button
		>
		<button
			type="submit"
			class="flex h-7 shrink-0 items-center gap-1.5 rounded-lg bg-gray-900 px-2 text-white hover:bg-black dark:bg-gray-100 dark:text-gray-900 {cloning
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
