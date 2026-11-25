<script lang="ts">
	import { getContext } from 'svelte';
	import { copyToClipboard } from '$lib/utils';

	const i18n = getContext<any>('i18n');

	export let contextUsage: any = null;
	export let queuedCount = 0;
	export let taskCount = 0;
	export let chatId = '';
	export let onCompact: (() => void) | undefined = undefined;

	let copied = false;

	const formatTokenCount = (value: number) => {
		if (value >= 1_000_000) return `${trimNumber(value / 1_000_000)}m`;
		if (value >= 1_000) return `${trimNumber(value / 1_000)}k`;
		return String(value ?? 0);
	};

	const trimNumber = (value: number) =>
		value >= 10 ? String(Math.round(value)) : value.toFixed(1).replace(/\.0$/, '');

	const copyChatId = async () => {
		if (!chatId) return;
		if (!(await copyToClipboard(chatId))) return;
		copied = true;
		setTimeout(() => {
			copied = false;
		}, 1600);
	};

	$: hasThreshold = Number(contextUsage?.threshold) > 0;
	$: percent = hasThreshold ? Math.max(0, Math.round(contextUsage?.percent ?? 0)) : 0;
	$: tokens = formatTokenCount(contextUsage?.estimated_tokens || contextUsage?.tokens || 0);
	$: contextValue = contextUsage
		? hasThreshold
			? `${tokens}/${formatTokenCount(contextUsage.threshold)}`
			: `${tokens} ${$i18n.t('tokens')}`
		: $i18n.t('unknown');
</script>

<div class="space-y-0.5 text-xs">
	<div class="rounded-xl py-0.5 text-base-600 dark:text-base-400">
		<div class="flex min-h-4 items-baseline gap-1.5">
			<span class="min-w-0 flex-1 truncate">
				{$i18n.t('Context')}
				{#if hasThreshold}
					<span class="text-base-500">{$i18n.t('{{percent}}% used', { percent })}</span>
				{/if}
			</span>
			{#if onCompact}
				<button
					type="button"
					class="shrink-0 text-[0.625rem] text-base-400 transition-colors duration-75 hover:text-base-500 dark:text-base-600 dark:hover:text-base-500"
					on:click={onCompact}
				>
					{$i18n.t('Compact')}
				</button>
			{/if}
			<span class="shrink-0 text-base-500">
				{contextValue}
			</span>
		</div>
		{#if hasThreshold}
			<div class="mt-1.5 h-0.5 overflow-hidden rounded-full bg-base-100 dark:bg-base-0/8">
				<div
					class="h-full rounded-full bg-base-300 dark:bg-base-0/20"
					style={`width: ${Math.min(percent, 100)}%`}
				></div>
			</div>
		{/if}
	</div>

	{#if queuedCount}
		<div class="flex min-h-5 items-center gap-3 text-base-600 dark:text-base-400">
			<span class="min-w-0 flex-1 truncate">{$i18n.t('Queued messages')}</span>
			<span class="font-mono text-[0.625rem] text-base-400 dark:text-base-600">
				{queuedCount}
			</span>
		</div>
	{/if}

	<div class="flex min-h-5 items-center gap-3 text-base-600 dark:text-base-400">
		<span class="min-w-0 flex-1 truncate">{$i18n.t('Chat ID')}</span>
		{#if chatId}
			<button
				type="button"
				class="min-w-0 max-w-[18rem] truncate font-mono text-[0.625rem] text-base-500 underline-offset-2 transition-colors duration-75 hover:text-base-700 hover:underline dark:hover:text-base-200"
				on:click={copyChatId}
			>
				{copied ? $i18n.t('Copied') : chatId}
			</button>
		{:else}
			<span class="font-mono text-[0.625rem] text-base-400 dark:text-base-600"> none </span>
		{/if}
	</div>

	{#if taskCount}
		<div class="flex min-h-5 items-center gap-3 text-base-600 dark:text-base-400">
			<span class="min-w-0 flex-1 truncate">{$i18n.t('Tasks')}</span>
			<span class="font-mono text-[0.625rem] text-base-400 dark:text-base-600">
				{taskCount}
			</span>
		</div>
	{/if}
</div>
