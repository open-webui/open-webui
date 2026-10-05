<script lang="ts">
	import { getContext } from 'svelte';
	const i18n: any = getContext('i18n');
	export let codes: string[];
	export let onContinue: () => void;
	let saved = false;

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
		<h2 class="text-base font-medium tracking-tight text-gray-900 dark:text-white">
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
		class="text-[0.6875rem] text-gray-500 transition-colors hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
		on:click={download}>{$i18n.t('Download recovery codes')}</button
	>
	<label class="flex items-center gap-2 text-[0.6875rem] text-gray-600 dark:text-gray-400"
		><input
			class="size-3 rounded-sm accent-gray-900 dark:accent-gray-100"
			type="checkbox"
			bind:checked={saved}
		/>{$i18n.t('I have saved my recovery codes')}</label
	>
	<div class="flex justify-end text-black dark:text-white">
		<button
			type="button"
			class="bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-normal text-[0.8125rem] leading-5 py-2.5 disabled:opacity-50 flex justify-center"
			disabled={!saved}
			on:click={onContinue}>{$i18n.t('Continue')}</button
		>
	</div>
</div>
