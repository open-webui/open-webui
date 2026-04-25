<script lang="ts">
	export let used = 0;
	export let total = 0;
	export let resetDate = '';
	export let alert = false;
	export let blocked = false;

	$: pct = total > 0 ? Math.min(Math.round((used / total) * 100), 100) : 0;
	$: remaining = Math.max(0, total - used);
	$: daysLeft = resetDate
		? Math.max(0, Math.ceil((new Date(resetDate).getTime() - Date.now()) / (1000 * 60 * 60 * 24)))
		: 0;

	const R = 32;
	const C = 2 * Math.PI * R;
	$: offset = C * (1 - pct / 100);
	$: arcColor = blocked ? '#de3514' : alert ? '#E07020' : '#0D5C3F';

	function fmt(n: number) {
		if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
		if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K';
		return n.toString();
	}
</script>

<!-- Light mode -->
<div
	class="rounded-2xl px-5 py-4 border h-full dark:hidden"
	style="background:#F5F0E8;border-color:rgba(13,92,63,.12)"
>
	<div class="flex items-center justify-between mb-3">
		<p class="text-[10px] font-semibold uppercase tracking-[.12em]" style="color:rgba(13,92,63,.5)">
			Tokens este mes
		</p>
		{#if blocked}
			<span class="text-[10px] font-mono px-2 py-0.5 rounded-full font-semibold" style="background:#de3514;color:white">Límite alcanzado</span>
		{:else if alert}
			<span class="text-[10px] font-mono px-2 py-0.5 rounded-full font-semibold" style="background:#E07020;color:white">Uso alto</span>
		{:else if daysLeft > 0}
			<span class="text-[10px] font-mono px-2 py-0.5 rounded-full font-semibold" style="background:#0D5C3F;color:#F5F0E8">Renueva en {daysLeft}d</span>
		{/if}
	</div>

	<div class="flex items-center gap-5">
		<!-- Compact donut -->
		<div class="shrink-0">
			<svg width="80" height="80" viewBox="0 0 80 80">
				<circle cx="40" cy="40" r={R} fill="none" stroke="rgba(13,92,63,.1)" stroke-width="7" />
				<circle
					cx="40" cy="40" r={R} fill="none"
					stroke={arcColor} stroke-width="7" stroke-linecap="round"
					stroke-dasharray={C} stroke-dashoffset={offset}
					transform="rotate(-90 40 40)"
					style="transition:stroke-dashoffset 1s cubic-bezier(.4,0,.2,1),stroke .3s"
				/>
				<text x="40" y="36" text-anchor="middle"
					style="font-family:ui-monospace,monospace;font-size:14px;font-weight:700;fill:#0D5C3F"
				>{pct}%</text>
				<text x="40" y="48" text-anchor="middle"
					style="font-family:ui-monospace,monospace;font-size:8px;fill:rgba(13,92,63,.45)"
				>usado</text>
			</svg>
		</div>

		<div class="flex-1 min-w-0">
			<div class="flex items-baseline gap-1.5 mb-0.5">
				<p class="text-2xl font-mono font-bold tabular-nums leading-none" style="color:#1E1E1E;letter-spacing:-.03em">{fmt(used)}</p>
				<p class="text-xs" style="color:rgba(30,30,30,.4)">/ {fmt(total)}</p>
			</div>
			<p class="text-[10px] mb-3" style="color:rgba(30,30,30,.35)">tokens usados</p>
			<div class="flex items-baseline gap-1.5">
				<p class="text-base font-mono font-semibold tabular-nums" style="color:#0D5C3F">{fmt(remaining)}</p>
				<p class="text-[10px]" style="color:rgba(30,30,30,.4)">disponibles</p>
			</div>
			{#if total === 0}
				<p class="text-[10px] mt-2" style="color:rgba(30,30,30,.3)">Conecta el backend para ver tu uso</p>
			{/if}
		</div>
	</div>
</div>

<!-- Dark mode -->
<div class="rounded-2xl px-5 py-4 border h-full hidden dark:block dark:bg-gray-800 dark:border-white/[.07]">
	<div class="flex items-center justify-between mb-3">
		<p class="text-[10px] font-semibold uppercase tracking-[.12em] text-white/40">Tokens este mes</p>
		{#if blocked}
			<span class="text-[10px] font-mono px-2 py-0.5 rounded-full font-semibold" style="background:#de3514;color:white">Límite alcanzado</span>
		{:else if alert}
			<span class="text-[10px] font-mono px-2 py-0.5 rounded-full font-semibold" style="background:#E07020;color:white">Uso alto</span>
		{:else if daysLeft > 0}
			<span class="text-[10px] font-mono px-2 py-0.5 rounded-full font-semibold" style="background:#0D5C3F;color:#F5F0E8">Renueva en {daysLeft}d</span>
		{/if}
	</div>

	<div class="flex items-center gap-5">
		<div class="shrink-0">
			<svg width="80" height="80" viewBox="0 0 80 80">
				<circle cx="40" cy="40" r={R} fill="none" stroke="rgba(255,255,255,.08)" stroke-width="7" />
				<circle cx="40" cy="40" r={R} fill="none"
					stroke={arcColor} stroke-width="7" stroke-linecap="round"
					stroke-dasharray={C} stroke-dashoffset={offset}
					transform="rotate(-90 40 40)"
					style="transition:stroke-dashoffset 1s cubic-bezier(.4,0,.2,1),stroke .3s"
				/>
				<text x="40" y="36" text-anchor="middle"
					style="font-family:ui-monospace,monospace;font-size:14px;font-weight:700;fill:#7ecfaf"
				>{pct}%</text>
				<text x="40" y="48" text-anchor="middle"
					style="font-family:ui-monospace,monospace;font-size:8px;fill:rgba(255,255,255,.35)"
				>usado</text>
			</svg>
		</div>

		<div class="flex-1 min-w-0">
			<div class="flex items-baseline gap-1.5 mb-0.5">
				<p class="text-2xl font-mono font-bold tabular-nums leading-none text-white" style="letter-spacing:-.03em">{fmt(used)}</p>
				<p class="text-xs text-white/40">/ {fmt(total)}</p>
			</div>
			<p class="text-[10px] mb-3 text-white/35">tokens usados</p>
			<div class="flex items-baseline gap-1.5">
				<p class="text-base font-mono font-semibold tabular-nums" style="color:#7ecfaf">{fmt(remaining)}</p>
				<p class="text-[10px] text-white/40">disponibles</p>
			</div>
			{#if total === 0}
				<p class="text-[10px] mt-2 text-white/20">Conecta el backend para ver tu uso</p>
			{/if}
		</div>
	</div>
</div>
