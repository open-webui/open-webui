<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';

	// Emitted by the seeded `background_agent` Tool as:
	// <details type="agent_job" job="<id>" tok="<signed>">
	//   <summary>Spouštím: <ai summary></summary></details>
	export let attributes: Record<string, string> = {};
	export let summary: string = '';

	// Debug display starts COLLAPSED — the user expands it on demand.
	let open = false;

	// Header stopwatch: live runtime, ticks every second. The block is
	// emitted right when the job starts, so time-since-mount ≈ job runtime.
	let started = Date.now();
	let elapsed = 0;
	let timer: ReturnType<typeof setInterval> | undefined;

	const fmt = (s: number) => {
		const m = Math.floor(s / 60);
		const r = s % 60;
		return `${m}:${r.toString().padStart(2, '0')}`;
	};

	onMount(() => {
		started = Date.now();
		timer = setInterval(() => {
			elapsed = Math.floor((Date.now() - started) / 1000);
		}, 1000);
	});
	onDestroy(() => timer && clearInterval(timer));

	$: jobId = attributes?.job ?? '';
	$: token = attributes?.tok ?? '';
	$: title = 'Pracuji: ' + ((summary && summary.trim()) || '…');
	$: src =
		jobId && token
			? `${WEBUI_BASE_URL}/api/v1/agent/jobs/${jobId}/view?token=${encodeURIComponent(token)}`
			: '';
</script>

<div
	class="my-1.5 w-full rounded-lg border border-gray-100 dark:border-gray-850 overflow-hidden"
>
	<div
		class="flex w-full items-center gap-2 px-3 py-2 bg-gray-50 dark:bg-gray-900"
	>
		<button
			type="button"
			class="flex flex-1 min-w-0 items-center gap-2 text-left hover:opacity-80 transition"
			on:click={() => (open = !open)}
		>
			<svg
				class="w-3 h-3 shrink-0 text-gray-400 transition-transform {open ? 'rotate-90' : ''}"
				viewBox="0 0 20 20"
				fill="currentColor"
			>
				<path
					fill-rule="evenodd"
					d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
					clip-rule="evenodd"
				/>
			</svg>
			<span class="text-xs font-medium text-gray-700 dark:text-gray-300 truncate"
				>{title}</span
			>
		</button>
		<span
			class="shrink-0 font-mono text-xs tabular-nums px-2 py-0.5 rounded-md bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300"
			title="Doba běhu agenta (tiká po sekundách)"
		>
			⏱ {fmt(elapsed)}
		</span>
		{#if src}
			<a
				href={src}
				target="_blank"
				rel="noopener noreferrer"
				class="shrink-0 text-xs font-medium px-2 py-0.5 rounded-md border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
				title="Otevřít živý log agenta v novém okně"
			>
				Log&nbsp;↗
			</a>
		{/if}
	</div>

	{#if open}
		{#if src}
			<iframe
				{src}
				title={title}
				class="w-full block bg-[#0d1117]"
				style="height: 240px; border: 0;"
				sandbox="allow-scripts allow-same-origin"
				loading="lazy"
			></iframe>
		{:else}
			<div class="px-3 py-3 text-xs text-gray-500">Agent job není dostupný.</div>
		{/if}
	{/if}
</div>
