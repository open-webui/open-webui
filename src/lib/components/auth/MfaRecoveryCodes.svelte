<script lang="ts">
	import { getContext } from 'svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	const i18n: any = getContext('i18n');
	export let codes: string[];
	export let onContinue: () => void | Promise<void>;
	let saved = false;
	let busy = false;
	let error = '';

	const continueHandler = async () => {
		if (busy || !saved) return;
		busy = true;
		error = '';
		try {
			await onContinue();
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	};

	const download = () => {
		const url = URL.createObjectURL(new Blob([codes.join('\n') + '\n'], { type: 'text/plain' }));
		const link = document.createElement('a');
		link.href = url;
		link.download = 'recovery-codes.txt';
		link.click();
		URL.revokeObjectURL(url);
	};
</script>

<div class="space-y-3 text-left text-xs">
	<div>
		<h2 class="text-base font-medium tracking-tight text-gray-700 dark:text-gray-300">
			{$i18n.t('Save your recovery codes')}
		</h2>
		<p class="mt-1 text-xs leading-5 text-gray-500 dark:text-gray-400">
			{$i18n.t('Each code works once. Save them somewhere safe; they will not be shown again.')}
		</p>
	</div>
	<ul
		class="rounded-md border border-gray-100 bg-gray-50/50 px-3 py-2 font-mono text-[0.6875rem] leading-5 text-gray-600 dark:border-white/[0.06] dark:bg-white/[0.02] dark:text-gray-400"
	>
		{#each codes as code}<li class="break-all select-all">{code}</li>{/each}
	</ul>
	<button
		type="button"
		class="text-[0.6875rem] text-gray-500 transition-colors hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
		on:click={download}>{$i18n.t('Download recovery codes')}</button
	>
	<label class="flex items-center gap-2 text-[0.6875rem] text-gray-600 dark:text-gray-400"
		><input
			class="size-3 rounded-sm accent-gray-900 dark:accent-gray-100"
			type="checkbox"
			bind:checked={saved}
			disabled={busy}
		/>{$i18n.t('I have saved my recovery codes')}</label
	>
	{#if error}<p role="alert" class="text-xs leading-4 text-red-600 dark:text-red-400">
			{error}
		</p>{/if}
	<div class="flex justify-end text-gray-700 dark:text-gray-300">
		<button
			type="button"
			class="bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-gray-200 transition w-full rounded-full font-normal text-[0.8125rem] leading-5 py-2.5 disabled:opacity-50 flex items-center justify-center gap-1.5"
			disabled={busy || !saved}
			aria-busy={busy}
			on:click={continueHandler}
		>
			{$i18n.t('Continue')}
			{#if busy}<Spinner />{/if}
		</button>
	</div>
</div>
