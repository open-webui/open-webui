<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import {
		formatGenerationDuration,
		formatTokensPerSecond,
		getGenerationStatsView,
		type GenerationStats
	} from '$lib/utils/generationStats';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let stats: GenerationStats | null = null;
	export let streaming = false;

	// good balance
	const TICK_MS = 100;

	let now = Date.now();
	let timer: ReturnType<typeof setInterval> | null = null;

	const stopTicking = () => {
		if (timer) {
			clearInterval(timer);
			timer = null;
		}
	};

	const syncTicker = (isStreaming: boolean) => {
		if (isStreaming && !timer) {
			now = Date.now();
			timer = setInterval(() => {
				now = Date.now();
			}, TICK_MS);
		} else if (!isStreaming && timer) {
			stopTicking();
			// Settle on the final numbers once the stream ends
			now = Date.now();
		}
	};

	$: syncTicker(streaming);
	$: view = getGenerationStatsView(stats, now, streaming);

	// Each figure explains itself, so hovering a number never describes a
	// different one
	$: tokensTooltip = view?.exact
		? $i18n.t('Token counts reported by the model provider.')
		: $i18n.t('Token counts are estimated until the response completes.');

	$: timeTooltip = [
		$i18n.t('Total generation time.'),
		view?.timeToFirstTokenMs != null
			? $i18n.t('Time to first token: {{duration}}', {
					duration: formatGenerationDuration(view.timeToFirstTokenMs)
				})
			: null
	]
		.filter(Boolean)
		.join('\n');

	$: rateTooltip = $i18n.t('Tokens per second, measured from the first token onward.');

	$: prefillTooltip = $i18n.t(
		'The model is processing the prompt. Generation has not started yet.'
	);

	onDestroy(stopTicking);
</script>

{#if view && (view.tokens > 0 || streaming)}
	<div
		class="flex items-center gap-2.5 mt-1.5 text-xs tabular-nums text-gray-400 dark:text-gray-600 select-none"
		aria-live="off"
	>
		{#if view.prefilling}
			<Tooltip content={prefillTooltip} placement="top-start" className="flex items-center gap-1">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="2"
					stroke="currentColor"
					aria-hidden="true"
					class="size-3 animate-pulse"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M6.75 3h10.5M6.75 21h10.5M7.5 3v4.5L12 12l-4.5 4.5V21M16.5 3v4.5L12 12l4.5 4.5V21"
					/>
				</svg>
				<span>{$i18n.t('Processing prompt')}</span>
			</Tooltip>
		{:else}
			<Tooltip content={tokensTooltip} placement="top-start" className="flex items-center gap-1">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="2"
					stroke="currentColor"
					aria-hidden="true"
					class="size-3"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M6.75 7.5h10.5M6.75 12h10.5M6.75 16.5h6"
					/>
				</svg>
				<span aria-label={$i18n.t('Generated tokens')}>
					{#if !view.exact && view.tokens > 0}<span class="mr-0.5">~</span
						>{/if}{view.tokens.toLocaleString()}
				</span>
			</Tooltip>
		{/if}

		<Tooltip content={timeTooltip} placement="top-start" className="flex items-center gap-1">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				stroke-width="2"
				stroke="currentColor"
				aria-hidden="true"
				class="size-3"
			>
				<path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6l3.75 2.25" />
				<circle cx="12" cy="12" r="8.25" />
			</svg>
			<span aria-label={$i18n.t('Generation time')}>
				{formatGenerationDuration(view.elapsedMs)}
			</span>
		</Tooltip>

		{#if view.tokensPerSecond !== null}
			<Tooltip content={rateTooltip} placement="top-start" className="flex items-center gap-1">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="2"
					stroke="currentColor"
					aria-hidden="true"
					class="size-3"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M13 3 5.25 13.5H12l-1 7.5 7.75-10.5H12l1-7.5Z"
					/>
				</svg>
				<span aria-label={$i18n.t('Tokens per second')}>
					{formatTokensPerSecond(view.tokensPerSecond)} t/s
				</span>
			</Tooltip>
		{/if}
	</div>
{/if}
