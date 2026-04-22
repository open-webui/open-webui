<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { copyToClipboard } from '$lib/utils';
	import { settings } from '$lib/stores';
	import MarkdownTokens from './MarkdownTokens.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import DocumentDuplicate from '$lib/components/icons/DocumentDuplicate.svelte';

	export let id: string = '';
	export let token: any;
	export let tokenIdx: number = 0;

	export let done: boolean = true;
	export let editCodeBlock: boolean = true;
	export let sourceIds: string[] = [];
	export let onTaskClick: Function = () => {};
	export let onSourceClick: Function = () => {};

	const fenceType: string = token.fenceType ?? 'default';

	const label = fenceType.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

	let copied = false;

	const copyText = async () => {
		copied = true;
		await copyToClipboard(token.text, null, $settings?.copyFormatted ?? false);
		setTimeout(() => {
			copied = false;
		}, 1000);
	};
</script>

<div class="relative group my-2 rounded-2xl border border-gray-100 dark:border-gray-800 px-4 py-3">
	<!-- Header row: type badge + copy button -->
	<div class="flex items-center justify-between mb-2">
		<span class="text-xs font-medium text-gray-500 dark:text-gray-400">
			{label}
		</span>

		<div class="invisible group-hover:visible flex gap-0.5">
			<Tooltip content={copied ? $i18n.t('Copied') : $i18n.t('Copy')}>
				<button
					class="p-1 rounded-lg bg-transparent hover:bg-black/5 dark:hover:bg-white/5 transition"
					on:click={(e) => {
						e.stopPropagation();
						copyText();
					}}
				>
					{#if copied}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-3.5 text-green-500"
						>
							<path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
						</svg>
					{:else}
						<DocumentDuplicate className="size-3.5" strokeWidth="1.5" />
					{/if}
				</button>
			</Tooltip>
		</div>
	</div>

	<!-- Content -->
	<div class="prose-sm" dir="auto">
		<MarkdownTokens
			id={`${id}-${tokenIdx}-cf`}
			tokens={token.tokens}
			{done}
			{editCodeBlock}
			{sourceIds}
			{onTaskClick}
			{onSourceClick}
		/>
	</div>
</div>
