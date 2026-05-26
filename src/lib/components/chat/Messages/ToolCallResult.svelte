<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';

	import { copyToClipboard } from '$lib/utils';
	import { decodeToolResultText, formatToolValue } from '$lib/utils/toolResults';
	import WebFetchResult from './ToolResults/WebFetchResult.svelte';
	import WebSearchResult from './ToolResults/WebSearchResult.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let id = '';
	export let name = '';
	export let argsRaw: unknown = '';
	export let resultRaw: unknown = '';
	export let done = true;

	type Tab = 'result' | 'request' | 'raw';

	const tabs: Tab[] = ['result', 'request', 'raw'];

	let activeTab: Tab = 'result';

	// Avoid eagerly decoding very large web_fetch results just to render the
	// chrome. Decode request/raw text only when that tab is visible; the rich
	// Result tab parses its own data lazily inside the specialized component.
	$: requestText = activeTab === 'request' ? formatToolValue(argsRaw) : '';
	$: resultText = activeTab === 'raw' ? decodeToolResultText(resultRaw) : '';

	const labelForTab = (tab: Tab) => {
		if (tab === 'result') return $i18n.t('Result');
		if (tab === 'request') return $i18n.t('Request');
		return $i18n.t('Raw');
	};

	const getActiveText = () => {
		if (activeTab === 'request') return formatToolValue(argsRaw);
		return decodeToolResultText(resultRaw);
	};

	const copyActive = async () => {
		if (await copyToClipboard(getActiveText())) {
			toast.success($i18n.t('Copied to clipboard'));
		}
	};
</script>

<div
	{id}
	class="my-2 overflow-hidden rounded-2xl border border-gray-100 bg-gray-50/70 text-sm dark:border-gray-800 dark:bg-gray-950/40"
>
	<div
		class="flex flex-col gap-2 border-b border-gray-100 bg-white px-2.5 py-2 dark:border-gray-800 dark:bg-gray-900 sm:flex-row sm:items-center sm:justify-between"
	>
		<div class="flex w-fit rounded-xl bg-gray-100 p-0.5 text-xs dark:bg-gray-800">
			{#each tabs as tab}
				<button
					class="rounded-lg px-2.5 py-1 font-medium transition {activeTab === tab
						? 'bg-white text-gray-900 shadow-xs dark:bg-gray-700 dark:text-white'
						: 'text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white'}"
					type="button"
					on:click={() => (activeTab = tab)}
				>
					{labelForTab(tab)}
				</button>
			{/each}
		</div>

		<button
			class="w-fit rounded-lg px-2 py-1 text-xs font-medium text-gray-500 transition hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-white"
			type="button"
			on:click={copyActive}
		>
			{$i18n.t('Copy')}
			{labelForTab(activeTab)}
		</button>
	</div>

	<div class="p-3">
		{#if activeTab === 'result'}
			{#if !done}
				<div
					class="rounded-xl border border-gray-100 bg-white px-4 py-3 text-sm text-gray-500 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-400"
				>
					{$i18n.t('The tool is still running. The result will appear here when it finishes.')}
				</div>
			{:else if name === 'web_search'}
				<WebSearchResult id={`${id}-web-search`} {resultRaw} {argsRaw} />
			{:else if name === 'web_fetch'}
				<WebFetchResult id={`${id}-web-fetch`} {resultRaw} />
			{/if}
		{:else if activeTab === 'request'}
			<div class="max-h-[48vh] overflow-y-auto rounded-xl bg-gray-950 p-3 text-xs text-gray-100">
				<pre class="whitespace-pre-wrap break-words font-mono">{requestText || '{}'}</pre>
			</div>
		{:else}
			<div class="max-h-[60vh] overflow-y-auto rounded-xl bg-gray-950 p-3 text-xs text-gray-100">
				<pre class="whitespace-pre-wrap break-words font-mono">{resultText || ''}</pre>
			</div>
		{/if}
	</div>
</div>
