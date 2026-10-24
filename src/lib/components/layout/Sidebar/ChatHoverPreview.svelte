<script lang="ts">
	import { getContext } from 'svelte';
	import { LinkPreview } from 'bits-ui';
	import ChatPreview from './ChatPreview.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n: any = getContext('i18n');
	export let chatId = '';
	export let title = '';
	export let openPreview = false;
	export let side: 'left' | 'right' | 'bottom' | 'top' = 'right';
	export let align: 'start' | 'end' | 'center' = 'start';
	export let sideOffset = 12;
	let turnCount: number | null = null;
</script>

{#if openPreview}
	<LinkPreview.Portal>
		<LinkPreview.Content
			class="z-[9999] hidden max-h-[min(17.5rem,calc(100vh-1.5rem))] w-[20rem] max-w-[calc(100vw-1.5rem)] overflow-hidden rounded-2xl bg-white shadow-[0_16px_40px_-28px_rgba(0,0,0,0.55)] ring-1 ring-black/5 transition md:block dark:bg-gray-850 dark:text-white dark:ring-white/10"
			{side}
			{align}
			{sideOffset}
		>
			<div
				class="flex items-center gap-2 border-b border-gray-50/60 px-3 py-2 dark:border-gray-800/25"
			>
				<div
					class="min-w-0 flex-1 truncate text-[0.8125rem] font-normal leading-5 text-gray-900 dark:text-gray-100"
				>
					{title || $i18n.t('Chat')}
				</div>
				{#if turnCount !== null}
					<Tooltip
						className="shrink-0 text-xs text-gray-500 dark:text-gray-400"
						content={$i18n.t('User and assistant turns in this branch')}
						tippyOptions={{ zIndex: 10000 }}
					>
						{$i18n.t('{{count}} turns', { count: turnCount })}
					</Tooltip>
				{/if}
			</div>
			<ChatPreview
				{chatId}
				bind:turnCount
				className="max-h-[min(15rem,calc(100vh-4rem))] bg-white dark:bg-gray-850"
			/>
		</LinkPreview.Content>
	</LinkPreview.Portal>
{/if}
