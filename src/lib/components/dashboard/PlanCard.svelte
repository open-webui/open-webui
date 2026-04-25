<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';

	export let planName = '';

	const plans = [
		{ id: 'free',     label: 'Free',     tokens: '50K',  price: '€0',       desc: 'Para empezar' },
		{ id: 'starter',  label: 'Starter',  tokens: '200K', price: '€49/mes',  desc: '3 agentes' },
		{ id: 'pro',      label: 'Pro',      tokens: '500K', price: '€99/mes',  desc: '5 agentes' },
		{ id: 'business', label: 'Business', tokens: '2M',   price: '€249/mes', desc: '15 agentes' }
	];

	$: currentIdx = plans.findIndex((p) => p.id === planName?.toLowerCase()) ?? 0;
	$: current = plans[currentIdx < 0 ? 0 : currentIdx];

	const tokenPacks = [
		{ id: 'pack_500k', label: '+500K Tokens', price: '€19', period: 'einmalig' },
		{ id: 'pack_2m',   label: '+2M Tokens',   price: '€59', period: 'einmalig' }
	];

	async function goToCheckout(planId: string) {
		if (planId === 'free' || planId === current.id) return;
		try {
			const res = await fetch(`${WEBUI_BASE_URL}/api/v1/clapnclaw/billing/checkout`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify({ plan: planId })
			});
			if (res.ok) {
				const data = await res.json();
				if (data.checkout_url) { window.location.href = data.checkout_url; return; }
			}
		} catch { /* fall through */ }
		window.location.href = `mailto:hola@clapnclaw.com?subject=Upgrade%20a%20${planId}`;
	}

	async function handleTokenPack(pack: typeof tokenPacks[0]) {
		try {
			const res = await fetch(`${WEBUI_BASE_URL}/api/v1/clapnclaw/billing/checkout`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify({ plan: pack.id })
			});
			if (res.ok) {
				const data = await res.json();
				if (data.checkout_url) { window.location.href = data.checkout_url; return; }
			}
		} catch { /* fall through */ }
		window.location.href = `mailto:hola@clapnclaw.com?subject=Token%20Pack%20${encodeURIComponent(pack.label)}`;
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

	<!-- Plan list — each row is a button if upgradeable -->
	<div class="flex-1 space-y-1 mb-4">
		{#each plans as p, i}
			{@const isActive = p.id === current.id}
			{@const isUpgrade = i > currentIdx && current.id !== 'enterprise'}
			{@const isFree = p.id === 'free'}
			<button
				class="w-full flex items-center justify-between px-2.5 py-2 rounded-xl transition-colors text-left
					{isUpgrade ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/40 group' : 'cursor-default'}
					{isActive ? '' : ''}"
				style={isActive ? 'background:rgba(13,92,63,.07)' : ''}
				disabled={isActive || isFree || i < currentIdx}
				on:click={() => isUpgrade && goToCheckout(p.id)}
			>
				<div class="flex items-center gap-2 min-w-0">
					<div
						class="size-1.5 rounded-full shrink-0"
						style={isActive ? 'background:#0D5C3F' : 'background:rgba(0,0,0,.15)'}
					/>
					<span
						class="text-xs truncate"
						class:font-semibold={isActive}
						class:text-gray-900={isActive}
						class:dark:text-white={isActive}
						class:text-gray-400={!isActive}
					>
						{p.label}
					</span>
					<span class="text-[10px] text-gray-300 dark:text-gray-600 font-mono shrink-0">{p.tokens}</span>
				</div>
				<div class="flex items-center gap-1.5">
					<span
						class="text-[10px] font-mono shrink-0"
						class:font-semibold={isActive}
						style={isActive ? 'color:#0D5C3F' : 'color:rgba(0,0,0,.25)'}
					>
						{p.price}
					</span>
					{#if isUpgrade}
						<span class="text-[9px] font-mono text-gray-300 group-hover:text-green-700 transition-colors">→</span>
					{/if}
				</div>
			</button>
		{/each}
	</div>

	<!-- Token packs -->
	<div class="pt-3 border-t border-black/[.05] dark:border-white/[.05]">
		<p class="text-[9px] font-semibold uppercase tracking-[.1em] text-gray-400 dark:text-white/30 mb-2">Recargas</p>
		<div class="flex flex-wrap gap-1.5">
			{#each tokenPacks as pack}
				<button
					class="flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-[11px] font-mono transition-all hover:border-gray-400 dark:hover:border-gray-500 hover:-translate-y-0.5 cursor-pointer"
					style="border-color:rgba(0,0,0,.12);color:rgba(0,0,0,.65)"
					on:click={() => handleTokenPack(pack)}
				>
					<span class="font-semibold dark:text-gray-200">{pack.label}</span>
					<span class="text-gray-500 dark:text-gray-400">{pack.price}</span>
					<span class="text-[9px] text-gray-400 dark:text-gray-500">{pack.period}</span>
				</button>
			{/each}
		</div>
	</div>
</div>
