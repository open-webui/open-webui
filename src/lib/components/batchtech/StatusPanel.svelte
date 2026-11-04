<script lang="ts">
	// BATCHTECH: live server resources in the sidebar. Every metric has a label. Polls every 2 s while the tab is visible.
	import { onMount, onDestroy } from 'svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	type Stats = {
		cpu: number;
		cores: number;
		mem: { used: number; total: number };
		gpu: { name: string; util: number; vram: { used: number; total: number } | null } | null;
		net: { down: number; up: number } | null;
		models?: { name: string; size: number | null; size_vram: number | null }[];
	};

	let stats: Stats | null = null;
	let failed = false;
	let open = true;
	let timer: ReturnType<typeof setInterval> | null = null;

	const gb = (b: number) => (b / 1073741824).toFixed(1);
	const rate = (b: number) =>
		b > 1048576 ? `${(b / 1048576).toFixed(1)} MB/s` : `${Math.round(b / 1024)} KB/s`;
	const pct = (v: number) => `${Math.round(Math.min(1, Math.max(0, v)) * 100)}%`;
	// green under 60 %, amber under 85 %, red above
	const color = (v: number) =>
		v < 0.6 ? 'bg-emerald-500' : v < 0.85 ? 'bg-amber-500' : 'bg-red-500';

	const poll = async () => {
		if (document.hidden) return;
		try {
			const r = await fetch(`${WEBUI_API_BASE_URL}/batchtech/stats`, {
				headers: { authorization: `Bearer ${localStorage.token}` },
				cache: 'no-store'
			});
			if (!r.ok) throw new Error(String(r.status));
			stats = await r.json();
			failed = false;
		} catch {
			failed = true;
		}
	};

	onMount(() => {
		try {
			open = localStorage.getItem('bt.status.open') !== '0';
		} catch {
			/* storage blocked */
		}
		poll();
		timer = setInterval(poll, 2000);
	});
	onDestroy(() => timer && clearInterval(timer));

	const toggle = () => {
		open = !open;
		try {
			localStorage.setItem('bt.status.open', open ? '1' : '0');
		} catch {
			/* storage blocked */
		}
	};

	$: rows = stats
		? [
				{
					label: 'CPU',
					hint: `Processor use across ${stats.cores} cores`,
					v: stats.cpu,
					text: pct(stats.cpu)
				},
				{
					label: 'RAM',
					hint: 'System memory in use',
					v: stats.mem.used / stats.mem.total,
					text: `${gb(stats.mem.used)} / ${gb(stats.mem.total)} GB`
				},
				...(stats.gpu
					? [
							{
								label: 'GPU',
								hint: `${stats.gpu.name} load`,
								v: stats.gpu.util,
								text: pct(stats.gpu.util)
							},
							...(stats.gpu.vram
								? [
										{
											label: 'VRAM',
											hint: 'Graphics memory in use',
											v: stats.gpu.vram.used / stats.gpu.vram.total,
											text: `${gb(stats.gpu.vram.used)} / ${gb(stats.gpu.vram.total)} GB`
										}
									]
								: [])
						]
					: [])
			]
		: [];
</script>

{#if !failed || stats}
	<div class="px-2.5 pb-1.5 text-xs text-gray-600 dark:text-gray-400" aria-label="Server status">
		<button
			type="button"
			class="w-full flex items-center justify-between rounded-lg px-2 py-1 font-medium hover:bg-gray-100 dark:hover:bg-gray-900 transition"
			aria-expanded={open}
			on:click={toggle}
		>
			<span>Server status</span>
			<span aria-hidden="true">{open ? '−' : '+'}</span>
		</button>
		{#if open}
			<div class="px-2 pt-1 space-y-1.5">
				{#each rows as row}
					<div title={row.hint}>
						<div class="flex justify-between">
							<span class="font-medium">{row.label}</span><span>{row.text}</span>
						</div>
						<div class="h-1.5 rounded-full bg-gray-200 dark:bg-gray-800 overflow-hidden">
							<div
								class="h-full rounded-full {color(row.v)} transition-all duration-700"
								style="width: {pct(row.v)}"
							></div>
						</div>
					</div>
				{/each}
				{#if stats?.net}
					<div class="flex justify-between" title="Network traffic of this machine">
						<span class="font-medium">Network</span>
						<span>↓ {rate(stats.net.down)} · ↑ {rate(stats.net.up)}</span>
					</div>
				{/if}
				<div title="Models Ollama currently holds in memory">
					<div class="font-medium">Models loaded</div>
					{#if stats?.models?.length}
						{#each stats.models as m}
							<div class="flex justify-between gap-2">
								<span class="truncate">{m.name}</span>
								<span class="shrink-0">
									{m.size_vram != null ? `${gb(m.size_vram)} GB` : ''}
									{m.size && m.size_vram != null
										? m.size_vram >= m.size * 0.98
											? '· GPU'
											: m.size_vram > 0
												? '· GPU+CPU'
												: '· CPU'
										: ''}
								</span>
							</div>
						{/each}
					{:else}
						<div class="text-gray-400">none</div>
					{/if}
				</div>
			</div>
		{/if}
	</div>
{/if}
