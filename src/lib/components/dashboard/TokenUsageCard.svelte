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

	const R = 46;
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
	class="rounded-2xl p-6 border h-full dark:hidden"
	style="background:#F5F0E8;border-color:rgba(13,92,63,.12)"
>
	<div class="flex items-start justify-between mb-5">
		<p class="text-[10px] font-semibold uppercase tracking-[.12em]" style="color:rgba(13,92,63,.5)">
			Tokens este mes
		</p>
		{#if blocked}
			<span class="text-[10px] font-mono px-2.5 py-0.5 rounded-full font-semibold" style="background:#de3514;color:white">
				Límite alcanzado
			</span>
		{:else if alert}
			<span class="text-[10px] font-mono px-2.5 py-0.5 rounded-full font-semibold" style="background:#E07020;color:white">
				Uso alto
			</span>
		{:else if daysLeft > 0}
			<span class="text-[10px] font-mono px-2.5 py-0.5 rounded-full font-semibold" style="background:#0D5C3F;color:#F5F0E8">
				Renueva en {daysLeft}d
			</span>
		{/if}
	</div>

	<div class="flex items-center gap-6">
		<div class="shrink-0">
			<svg width="124" height="124" viewBox="0 0 124 124">
				<circle cx="62" cy="62" r={R} fill="none" stroke="rgba(13,92,63,.1)" stroke-width="9" />
				<circle
					cx="62" cy="62" r={R} fill="none"
					stroke={arcColor} stroke-width="9" stroke-linecap="round"
					stroke-dasharray={C} stroke-dashoffset={offset}
					transform="rotate(-90 62 62)"
					style="transition:stroke-dashoffset 1s cubic-bezier(.4,0,.2,1),stroke .3s"
				/>
				<text x="62" y="57" text-anchor="middle"
					style="font-family:ui-monospace,monospace;font-size:19px;font-weight:700;fill:#0D5C3F"
				>{pct}%</text>
				<text x="62" y="72" text-anchor="middle"
					style="font-family:ui-monospace,monospace;font-size:9px;fill:rgba(13,92,63,.45)"
				>usado</text>
			</svg>
		</div>

		<div class="flex-1 space-y-4 min-w-0">
			<div>
				<p class="text-[2rem] font-mono font-bold tabular-nums leading-none" style="color:#1E1E1E;letter-spacing:-.03em">{fmt(used)}</p>
				<p class="text-xs mt-1" style="color:rgba(30,30,30,.4)">de {fmt(total)} tokens</p>
			</div>
			<div class="pt-3 border-t" style="border-color:rgba(13,92,63,.1)">
				<p class="text-base font-mono font-semibold tabular-nums" style="color:#0D5C3F">{fmt(remaining)}</p>
				<p class="text-xs mt-0.5" style="color:rgba(30,30,30,.4)">disponibles</p>
			</div>
			{#if total === 0}
				<p class="text-[10px]" style="color:rgba(30,30,30,.3)">Conecta el backend para ver tu uso</p>
			{/if}
		</div>
	</div>
</div>

<!-- Dark mode -->
<div class="rounded-2xl p-6 border h-full hidden dark:block dark:bg-gray-800 dark:border-white/[.07]">
	<div class="flex items-start justify-between mb-5">
		<p class="text-[10px] font-semibold uppercase tracking-[.12em] text-white/40">Tokens este mes</p>
		{#if blocked}
			<span class="text-[10px] font-mono px-2.5 py-0.5 rounded-full font-semibold" style="background:#de3514;color:white">Límite alcanzado</span>
		{:else if alert}
			<span class="text-[10px] font-mono px-2.5 py-0.5 rounded-full font-semibold" style="background:#E07020;color:white">Uso alto</span>
		{:else if daysLeft > 0}
			<span class="text-[10px] font-mono px-2.5 py-0.5 rounded-full font-semibold" style="background:#0D5C3F;color:#F5F0E8">Renueva en {daysLeft}d</span>
		{/if}
	</div>

	<div class="flex items-center gap-6">
		<div class="shrink-0">
			<svg width="124" height="124" viewBox="0 0 124 124">
				<circle cx="62" cy="62" r={R} fill="none" stroke="rgba(255,255,255,.08)" stroke-width="9" />
				<circle cx="62" cy="62" r={R} fill="none"
					stroke={arcColor} stroke-width="9" stroke-linecap="round"
					stroke-dasharray={C} stroke-dashoffset={offset}
					transform="rotate(-90 62 62)"
					style="transition:stroke-dashoffset 1s cubic-bezier(.4,0,.2,1),stroke .3s"
				/>
				<text x="62" y="57" text-anchor="middle"
					style="font-family:ui-monospace,monospace;font-size:19px;font-weight:700;fill:#7ecfaf"
				>{pct}%</text>
				<text x="62" y="72" text-anchor="middle"
					style="font-family:ui-monospace,monospace;font-size:9px;fill:rgba(255,255,255,.35)"
				>usado</text>
			</svg>
		</div>

		<div class="flex-1 space-y-4 min-w-0">
			<div>
				<p class="text-[2rem] font-mono font-bold tabular-nums leading-none text-white" style="letter-spacing:-.03em">{fmt(used)}</p>
				<p class="text-xs mt-1 text-white/40">de {fmt(total)} tokens</p>
			</div>
			<div class="pt-3 border-t border-white/[.07]">
				<p class="text-base font-mono font-semibold tabular-nums" style="color:#7ecfaf">{fmt(remaining)}</p>
				<p class="text-xs mt-0.5 text-white/40">disponibles</p>
			</div>
			{#if total === 0}
				<p class="text-[10px] text-white/20">Conecta el backend para ver tu uso</p>
			{/if}
		</div>
	</div>
</div>
