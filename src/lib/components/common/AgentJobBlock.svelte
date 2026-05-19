<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';

	// Emitted by the seeded `background_agent` Tool as:
	// <details type="agent_job" job="<id>" tok="<signed>">
	//   <summary><ai task summary></summary></details>
	export let attributes: Record<string, string> = {};
	export let summary: string = '';

	// Debug display starts COLLAPSED — the user expands it on demand.
	let open = false;

	// Header stopwatch: live runtime, ticks every second. The block is
	// emitted right when the job starts, so time-since-mount ≈ job runtime.
	let started = Date.now();
	let elapsed = 0;
	let timer: ReturnType<typeof setInterval> | undefined;
	const fmt = (s: number) =>
		`${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`;
	onMount(() => {
		started = Date.now();
		timer = setInterval(() => {
			elapsed = Math.floor((Date.now() - started) / 1000);
		}, 1000);
	});
	onDestroy(() => timer && clearInterval(timer));

	// Persona — deterministic from job id (MUST match agent.py
	// _persona_*: hash = sum of char codepoints; name = h%2;
	// phrase = floor(h/2) % 5). 0 = girl Miluška, 1 = man Jindřich.
	const PERSONAS = ['Miluška', 'Jindřich'];
	const PHRASES = [
		'{n} na tom dělá',
		'{n} konečně má práci',
		'{n} se činí',
		'{n} na tom maká',
		'{n} to právě řeší'
	];
	$: jobId = attributes?.job ?? '';
	$: token = attributes?.tok ?? '';
	$: hash = (jobId || 'x')
		.split('')
		.reduce((a, ch) => a + ch.charCodeAt(0), 0);
	$: personaIdx = hash % 2;
	$: agentName = PERSONAS[personaIdx];
	$: phrase = PHRASES[Math.floor(hash / 2) % PHRASES.length].replace(
		'{n}',
		agentName
	);
	$: task = (summary || '').replace(/^\s*(Spouštím|Pracuji)\s*:?\s*/i, '').trim();
	$: title = task ? `${phrase}: ${task}` : phrase;
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
			<!-- Robot persona icon: pink antenna/bow = Miluška, blue = Jindřich -->
			<svg
				class="w-5 h-5 shrink-0 {personaIdx === 0
					? 'text-pink-500'
					: 'text-sky-500'}"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="1.7"
				stroke-linecap="round"
				stroke-linejoin="round"
				aria-label={agentName}
			>
				{#if personaIdx === 0}
					<!-- bow on top (girl) -->
					<path d="M10 4.2c-1.6-1-3 .2-2.4 1.6.5 1 2.4 1.2 2.4 1.2s1.9-.2 2.4-1.2c.6-1.4-.8-2.6-2.4-1.6z" fill="currentColor" stroke="none"/>
					<line x1="12" y1="6.6" x2="12" y2="8" />
				{:else}
					<!-- antenna (man) -->
					<line x1="12" y1="3.5" x2="12" y2="8" />
					<circle cx="12" cy="3" r="1.2" fill="currentColor" stroke="none" />
				{/if}
				<rect x="4.5" y="8" width="15" height="11" rx="2.5" />
				<circle cx="9" cy="13" r="1.3" fill="currentColor" stroke="none" />
				<circle cx="15" cy="13" r="1.3" fill="currentColor" stroke="none" />
				<line x1="9.5" y1="16.3" x2="14.5" y2="16.3" />
			</svg>

			<span
				class="shrink-0 font-mono text-xs tabular-nums text-gray-500 dark:text-gray-400"
				title="Doba běhu agenta (tiká po sekundách)"
			>
				⏱ {fmt(elapsed)}
			</span>

			<span class="text-xs font-medium text-gray-700 dark:text-gray-300 truncate"
				>{title}</span
			>
		</button>
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
