<script lang="ts">
	// BATCHTECH: live server resources in the sidebar. Polls /api/v1/batchtech/stats every 2 s while the tab is visible.
	import { onMount, onDestroy } from 'svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	type Stats = {
		cpu: number;
		cores: number;
		mem: { used: number; total: number };
		gpu: { name: string; util: number; vram: { used: number; total: number } | null } | null;
		net: { down: number; up: number } | null;
	};

	let stats: Stats | null = null;
	let failed = false;
	let open = false;
	let timer: ReturnType<typeof setInterval> | null = null;

	const gb = (b: number) => (b / 1073741824).toFixed(1);
	const rate = (b: number) =>
		b > 1048576 ? `${(b / 1048576).toFixed(1)} MB/s` : `${Math.round(b / 1024)} KB/s`;
	const pct = (v: number) => `${Math.round(Math.min(1, Math.max(0, v)) * 100)}%`;

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
		poll();
		timer = setInterval(poll, 2000);
	});
	onDestroy(() => timer && clearInterval(timer));

	$: rows = stats
		? [
				{ label: 'CPU', v: stats.cpu, text: `${pct(stats.cpu)} · ${stats.cores} cores` },
				{
					label: 'Memory',
					v: stats.mem.used / stats.mem.total,
					text: `${gb(stats.mem.used)} / ${gb(stats.mem.total)} GB`
				},
				...(stats.gpu
					? [
							{
								label: 'GPU',
								v: stats.gpu.util,
								text: `${pct(stats.gpu.util)} · ${stats.gpu.name}`
							},
							...(stats.gpu.vram
								? [
										{
											label: 'VRAM',
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
			class="w-full flex items-center gap-2 rounded-lg px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-900 transition"
			aria-expanded={open}
			on:click={() => (open = !open)}
		>
			<span class="font-medium">Server</span>
			{#each rows.slice(0, 3) as row}
				<span class="flex-1 min-w-0" title="{row.label}: {row.text}">
					<span class="block h-1.5 rounded-full bg-gray-200 dark:bg-gray-800 overflow-hidden">
						<span
							class="block h-full rounded-full bg-emerald-500 transition-all duration-700"
							style="width: {pct(row.v)}"
						></span>
					</span>
				</span>
			{/each}
		</button>
		{#if open}
			<div class="px-2 pt-1 space-y-1.5">
				{#each rows as row}
					<div>
						<div class="flex justify-between"><span>{row.label}</span><span>{row.text}</span></div>
						<div class="h-1.5 rounded-full bg-gray-200 dark:bg-gray-800 overflow-hidden">
							<div
								class="h-full rounded-full bg-emerald-500 transition-all duration-700"
								style="width: {pct(row.v)}"
							></div>
						</div>
					</div>
				{/each}
				{#if stats?.net}
					<div class="flex justify-between">
						<span>Network</span><span>↓ {rate(stats.net.down)} · ↑ {rate(stats.net.up)}</span>
					</div>
				{/if}
			</div>
		{/if}
	</div>
{/if}
