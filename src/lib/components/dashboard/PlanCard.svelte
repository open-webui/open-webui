<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';

	export let planName = '';

	// Plans aligned with backend Plan enum: free | starter | pro | enterprise
	const plans = [
		{ id: 'free',       label: 'Free',       tokens: '50K',  price: '€0',      desc: 'Para empezar' },
		{ id: 'starter',    label: 'Starter',    tokens: '1M',   price: '€20/mes', desc: 'Uso diario' },
		{ id: 'pro',        label: 'Pro',        tokens: '3M',   price: '€79/mes', desc: 'Usuarios intensivos' },
		{ id: 'enterprise', label: 'Enterprise', tokens: '5M',   price: '€99/mes', desc: 'Equipos y firmas' }
	];

	$: current = plans.find((p) => p.id === planName?.toLowerCase()) ?? plans[0];
	$: nextPlan = plans[plans.indexOf(current) + 1];

	async function handleUpgrade() {
		if (!nextPlan || nextPlan.id === 'free') return;
		try {
			const res = await fetch(`${WEBUI_BASE_URL}/api/v1/clapnclaw/billing/checkout`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify({ plan: nextPlan.id })
			});
			if (res.ok) {
				const data = await res.json();
				if (data.checkout_url) {
					window.location.href = data.checkout_url;
					return;
				}
			}
		} catch {
			// network error — fall through to mailto
		}
		window.location.href = `mailto:hola@clapnclaw.com?subject=Upgrade%20a%20${nextPlan.label}`;
	}
</script>

<div class="rounded-2xl p-5 border h-full flex flex-col bg-white dark:bg-gray-800 border-black/[.07] dark:border-white/[.07]">
	<!-- Header -->
	<div class="flex items-center justify-between mb-4">
		<p class="text-[10px] font-semibold uppercase tracking-[.12em] text-gray-400 dark:text-white/40">Plan</p>
		<span
			class="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full"
			style="background:#0D5C3F;color:#F5F0E8"
		>
			{current.label}
		</span>
	</div>

	<!-- Plan list -->
	<div class="flex-1 space-y-0.5 mb-4">
		{#each plans as p}
			<div
				class="flex items-center justify-between px-2.5 py-2 rounded-xl transition-colors
				{p.id !== current.id ? 'hover:bg-gray-50 dark:hover:bg-gray-700/40' : ''}"
				style={p.id === current.id ? 'background:rgba(13,92,63,.07)' : ''}
			>
				<div class="flex items-center gap-2 min-w-0">
					<div
						class="size-1.5 rounded-full shrink-0"
						style={p.id === current.id ? 'background:#0D5C3F' : 'background:rgba(0,0,0,.15)'}
					/>
					<span
						class="text-xs truncate"
						class:font-semibold={p.id === current.id}
						class:text-gray-900={p.id === current.id}
						class:dark:text-white={p.id === current.id}
						class:text-gray-400={p.id !== current.id}
					>
						{p.label}
					</span>
					<span class="text-[10px] text-gray-300 dark:text-gray-600 font-mono shrink-0">{p.tokens}</span>
				</div>
				<span
					class="text-[10px] font-mono shrink-0 ml-1"
					class:font-semibold={p.id === current.id}
					style={p.id === current.id ? 'color:#0D5C3F' : 'color:rgba(0,0,0,.25)'}
				>
					{p.price}
				</span>
			</div>
		{/each}
	</div>

	<!-- CTA -->
	{#if nextPlan}
		<button
			class="w-full py-2 rounded-xl text-xs font-semibold font-mono transition-all hover:opacity-90 hover:-translate-y-0.5 cursor-pointer"
			style="background:#0D5C3F;color:#F5F0E8"
			on:click={handleUpgrade}
		>
			Mejorar → {nextPlan.label} ({nextPlan.price})
		</button>
	{:else}
		<div class="w-full py-2 rounded-xl text-xs font-mono text-center" style="background:rgba(13,92,63,.07);color:#0D5C3F">
			Plan máximo activo
		</div>
	{/if}
</div>
