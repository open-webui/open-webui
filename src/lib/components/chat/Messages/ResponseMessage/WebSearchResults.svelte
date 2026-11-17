<script lang="ts">
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Clipboard from '$lib/components/icons/Clipboard.svelte';
	import { copyToClipboard } from '$lib/utils';
	import { getI18n } from '$lib/utils/context';

	const i18n = getI18n();

	type WebSearchStatus = { urls: string[]; query: string };

	export let status: WebSearchStatus = { urls: [], query: '' };
	let state = false;
	$: copyTooltipContent = $i18n.t('Copy to clipboard');

	const copyQueryToClipboard = async () => {
		if (!status?.query) {
			return;
		}

		await copyToClipboard(status.query);
		copyTooltipContent = $i18n.t('Copied to clipboard');
		setTimeout(() => {
			copyTooltipContent = $i18n.t('Copy to clipboard');
		}, 2000);
	};
</script>

<Collapsible bind:open={state} className="w-full space-y-1">
	<div
		class="flex items-start gap-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition"
	>
		<div class="min-w-0 flex-1">
			<slot />
		</div>

		<div class="mt-0.5 shrink-0">
			{#if state}
				<ChevronUp strokeWidth="3.5" className="size-3.5 " />
			{:else}
				<ChevronDown strokeWidth="3.5" className="size-3.5 " />
			{/if}
		</div>
	</div>
	<div
		class="text-sm border border-gray-300/30 dark:border-gray-700/50 rounded-xl mb-1.5"
		slot="content"
	>
		{#if status?.query}
			<div
				class="group/query relative flex flex-col items-center px-4 pt-3 pb-2 text-center border-b border-gray-300/30 dark:border-gray-700/50"
			>
				<span
					class="text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide group-hover/query:text-gray-500 dark:group-hover/query:text-gray-400 transition"
				>
					Search query
				</span>
				<div class="mt-1 max-w-full">
					<span
						class="text-gray-800 dark:text-gray-200 line-clamp-1 group-hover/query:text-gray-600 dark:group-hover/query:text-gray-400 transition font-medium"
					>
						{status.query}
					</span>
				</div>
				<div
					class="absolute right-4 top-1/2 flex opacity-0 pointer-events-none -translate-y-1/2 items-center gap-1 transition group-hover/query:opacity-100 group-hover/query:pointer-events-auto group-focus-within/query:opacity-100 group-focus-within/query:pointer-events-auto [@media(hover:none)]:opacity-100 [@media(hover:none)]:pointer-events-auto"
				>
					<Tooltip content={copyTooltipContent} tippyOptions={{ hideOnClick: false }}>
						<button
							type="button"
							class="shrink-0 rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800 dark:hover:text-gray-200 transition"
							aria-label={copyTooltipContent}
							on:click|stopPropagation={copyQueryToClipboard}
						>
							<Clipboard className="size-4" strokeWidth="1.5" />
						</button>
					</Tooltip>
				</div>
			</div>
		{/if}

		{#each status.urls as url, urlIdx}
			<a
				href={url}
				target="_blank"
				class="flex w-full items-center p-3 px-4 {urlIdx === 0
					? ''
					: 'border-t border-gray-300/30 dark:border-gray-700/50'} group/item justify-between font-normal text-gray-800 dark:text-gray-300"
			>
				<div class=" line-clamp-1">
					{url}
				</div>

				<div
					class=" ml-1 text-white dark:text-gray-900 group-hover/item:text-gray-600 dark:group-hover/item:text-white transition"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="size-4"
					>
						<path
							fill-rule="evenodd"
							d="M4.22 11.78a.75.75 0 0 1 0-1.06L9.44 5.5H5.75a.75.75 0 0 1 0-1.5h5.5a.75.75 0 0 1 .75.75v5.5a.75.75 0 0 1-1.5 0V6.56l-5.22 5.22a.75.75 0 0 1-1.06 0Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
			</a>
		{/each}
	</div>
</Collapsible>
