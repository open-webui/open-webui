<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import ProfilingIcon from './ProfilingIcon.svelte';
	const i18n: any = getContext('i18n');
	$: locale = $i18n.resolvedLanguage ?? $i18n.language;
	import { format, metrics, type Sample } from './metrics';
	export let history: any;
	export let samples: Record<string, Sample> = {};
	let open = false;
	let now = 0;
	let selected = '';
	$: responses = Object.values(history?.messages ?? {})
		.filter((m: any) => m.role === 'assistant')
		.sort((a: any, b: any) => (b.timestamp ?? 0) - (a.timestamp ?? 0)) as any[];
	$: message =
		responses.find((m) => m.id === selected) ??
		responses.find((m) => m.id === history?.currentId) ??
		responses[0];
	$: sample = samples[message?.id];
	$: values = metrics(message?.usage);
	$: running = !!sample && sample.end === undefined && !message?.done && !message?.error;
	$: elapsed = sample ? Math.max(0, ((sample.end ?? now) - sample.start) / 1000) : undefined;
	onMount(() => {
		now = performance.now();
		const timer = setInterval(() => {
			if (open) now = performance.now();
		}, 100);
		return () => clearInterval(timer);
	});
</script>

<svelte:window
	on:keydown={(event) => {
		if (event.key === 'Escape') open = false;
	}}
/>
<button
	type="button"
	class="profiling-trigger rounded-lg px-2 py-1 text-xs text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
	title={$i18n.t('Profiling')}
	aria-label={$i18n.t('Profiling')}
	aria-expanded={open}
	on:click={() => {
		now = performance.now();
		open = !open;
	}}><ProfilingIcon className="size-4 shrink-0" /><span>{$i18n.t('Profiling')}</span></button
>
{#if open}
	<section
		aria-label={$i18n.t('Profiling')}
		class="profiling-panel fixed right-3 top-16 z-50 rounded-2xl border border-gray-200 bg-white text-sm text-gray-800 shadow-xl dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100 no-drag"
	>
		<header class="panel-header">
			<h2 class="font-semibold">
				<ProfilingIcon className="size-4 shrink-0" /><span>{$i18n.t('Profiling')} · llama.cpp</span>
			</h2>
			<button
				type="button"
				aria-label={$i18n.t('Profiling: close')}
				class="rounded px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-800"
				on:click={() => (open = false)}>✕</button
			>
		</header>
		<div class="panel-body">
			{#if message}
				<label class="block text-xs text-gray-500" for="profiling-response-{message.id}"
					>{$i18n.t('Profiling: response')}</label
				>
				<select
					id="profiling-response-{message.id}"
					class="response-select rounded-lg border border-gray-200 bg-transparent dark:border-gray-700"
					bind:value={selected}
				>
					<option value="">{$i18n.t('Profiling: current or latest')}</option>
					{#each responses as response}<option value={response.id}
							>{response.modelName ?? response.model} · {new Date(
								response.timestamp * 1000
							).toLocaleTimeString(locale)}</option
						>{/each}
				</select>
				<p class="model-name font-medium">
					{message.selectedModelId ?? message.modelName ?? message.model}
				</p>
				<p class="status text-xs text-gray-500" role="status">
					{message.error || sample?.status === 'error'
						? $i18n.t('Profiling: error')
						: sample?.status === 'cancelled'
							? $i18n.t('Profiling: stopped')
							: message.done || sample?.status === 'done'
								? $i18n.t('Profiling: completed')
								: sample?.first !== undefined
									? $i18n.t('Profiling: streaming')
									: $i18n.t('Profiling: waiting')}
				</p>
				<dl class="metrics-grid">
					<dt>
						{$i18n.t('Profiling: response time')}
						{running ? '· ' + $i18n.t('Profiling: live') : ''}
					</dt>
					<dd>{format(elapsed, ' ' + $i18n.t('Profiling: seconds'), locale)}</dd>
					<dt>{$i18n.t('Profiling: browser TTFT')}</dt>
					<dd>
						{format(
							sample?.first === undefined ? undefined : (sample.first - sample.start) / 1000,
							' ' + $i18n.t('Profiling: seconds'),
							locale
						)}
					</dd>
					<dt>{$i18n.t('Profiling: generation speed')}</dt>
					<dd>{format(values.speed, ' ' + $i18n.t('Profiling: tokens per second'), locale)}</dd>
					<dt>{$i18n.t('Profiling: prompt processing speed')}</dt>
					<dd>
						{format(values.promptSpeed, ' ' + $i18n.t('Profiling: tokens per second'), locale)}
					</dd>
					<dt>{$i18n.t('Profiling: input tokens')}</dt>
					<dd>{format(values.input, '', locale)}</dd>
					<dt>{$i18n.t('Profiling: output tokens')}</dt>
					<dd>{format(values.output, '', locale)}</dd>
					<dt>{$i18n.t('Profiling: prompt time')}</dt>
					<dd>
						{format(
							values.promptMs === undefined ? undefined : values.promptMs / 1000,
							' ' + $i18n.t('Profiling: seconds'),
							locale
						)}
					</dd>
					<dt>{$i18n.t('Profiling: generation time')}</dt>
					<dd>
						{format(
							values.generationMs === undefined ? undefined : values.generationMs / 1000,
							' ' + $i18n.t('Profiling: seconds'),
							locale
						)}
					</dd>
				</dl>
				{#if running}<p class="live-note text-xs text-gray-500">
						{$i18n.t('Profiling: live explanation')}
					</p>{/if}
				<details class="notes text-xs text-gray-500">
					<summary
						><svg aria-hidden="true" viewBox="0 0 20 20" fill="none"
							><circle cx="10" cy="10" r="8" stroke="currentColor" stroke-width="1.5" /><path
								d="M10 9v5"
								stroke="currentColor"
								stroke-width="1.5"
								stroke-linecap="round"
							/><circle cx="10" cy="6" r="1" fill="currentColor" /></svg
						><span>{$i18n.t('Profiling: about metrics')}</span></summary
					>
					<p>{$i18n.t('Profiling: metrics explanation')}</p>
				</details>
			{:else}<p class="text-gray-500">{$i18n.t('Profiling: empty state')}</p>{/if}
		</div>
	</section>
{/if}

<style>
	.profiling-trigger {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.35rem;
	}
	.profiling-panel {
		box-sizing: border-box;
		width: min(24rem, calc(100vw - 1.5rem));
		max-height: calc(100dvh - 5rem);
		min-width: 0;
		display: flex;
		flex-direction: column;
		overflow: hidden;
		white-space: normal;
		text-align: left;
	}
	.panel-header {
		flex: none;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		padding: 0.75rem 1rem 0.5rem;
	}
	.panel-header h2 {
		min-width: 0;
		margin: 0;
		display: flex;
		align-items: center;
		gap: 0.45rem;
	}
	.panel-header button {
		flex: none;
	}
	.panel-body {
		min-height: 0;
		min-width: 0;
		overflow-y: auto;
		overflow-x: hidden;
		padding: 0.25rem 1rem 1rem;
	}
	.response-select {
		display: block;
		box-sizing: border-box;
		width: 100%;
		min-width: 0;
		max-width: 100%;
		margin: 0.25rem 0 0.6rem;
		padding: 0.45rem;
		text-overflow: ellipsis;
	}
	.model-name {
		overflow-wrap: anywhere;
		margin: 0 0 0.2rem;
	}
	.status {
		margin: 0 0 0.75rem;
		white-space: normal;
	}
	.metrics-grid {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, auto);
		align-items: baseline;
		gap: 0.5rem 0.75rem;
		margin: 0;
	}
	.metrics-grid dt,
	.metrics-grid dd {
		min-width: 0;
		margin: 0;
		overflow-wrap: anywhere;
		white-space: normal;
	}
	.metrics-grid dd {
		text-align: right;
		font-family: ui-monospace, monospace;
		font-variant-numeric: tabular-nums;
	}
	.live-note {
		margin: 0.8rem 0 0;
		line-height: 1.5;
		overflow-wrap: anywhere;
	}
	.notes {
		margin-top: 0.8rem;
		white-space: normal;
		overflow-wrap: anywhere;
		line-height: 1.5;
	}
	.notes summary {
		cursor: pointer;
		display: flex;
		align-items: center;
		gap: 0.4rem;
		list-style: none;
	}
	.notes summary::-webkit-details-marker {
		display: none;
	}
	.notes summary svg {
		width: 1rem;
		height: 1rem;
		flex: none;
	}
	.notes p {
		margin: 0.5rem 0 0;
	}
</style>
