<script lang="ts">
	import { onMount, getContext, tick } from 'svelte';
	import { WEBUI_BASE_URL, WEBUI_API_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, showSidebar, user, mobile } from '$lib/stores';
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';

	const i18n = getContext('i18n');

	let currentPlan = '';
	let loading = true;
	let portalLoading = false;

	$: plans = [
		{
			id: 'free',
			label: 'Free',
			sublabel: $i18n.t('For testing'),
			price: '€0',
			period: '',
			features: [
				`50.000 ${$i18n.t('tokens/month')}`,
				`≈ 50 ${$i18n.t('document analyses')}`,
				'AVV Art. 28 DSGVO'
			],
			highlight: false,
			contact: false
		},
		{
			id: 'starter',
			label: 'Starter',
			sublabel: $i18n.t('Daily use'),
			price: '€20',
			period: $i18n.t('/mo'),
			features: [
				`1.000.000 ${$i18n.t('tokens/month')}`,
				`≈ 1.000 ${$i18n.t('document analyses')}`,
				'AVV Art. 28 DSGVO'
			],
			highlight: false,
			contact: false
		},
		{
			id: 'pro',
			label: 'Pro',
			sublabel: $i18n.t('Popular · Intensive use'),
			price: '€79',
			period: $i18n.t('/mo'),
			features: [
				`3.000.000 ${$i18n.t('tokens/month')}`,
				`≈ 3.000 ${$i18n.t('document analyses')}`,
				$i18n.t('Priority support'),
				'AVV Art. 28 DSGVO'
			],
			highlight: true,
			contact: false
		},
		{
			id: 'enterprise',
			label: 'Enterprise',
			sublabel: $i18n.t('For offices and teams'),
			price: '€99',
			period: $i18n.t('/mo'),
			features: [
				`5.000.000 ${$i18n.t('tokens/month')}`,
				`≈ 5.000 ${$i18n.t('document analyses')}`,
				$i18n.t('Priority support'),
				'AVV Art. 28 DSGVO'
			],
			highlight: false,
			contact: true
		}
	];

	$: addonPacks = [
		{ id: 'small', label: '+500K Tokens', price: '€19', desc: $i18n.t('One-time payment') },
		{ id: 'large', label: '+2M Tokens', price: '€59', desc: $i18n.t('One-time payment') }
	];

	$: currentIdx = plans.findIndex((p) => p.id === currentPlan?.toLowerCase());
	$: effectiveIdx = currentIdx < 0 ? 0 : currentIdx;

	async function fetchCurrentPlan() {
		try {
			const res = await fetch(`${WEBUI_BASE_URL}/api/v1/clapnclaw/billing/plan`, {
				headers: { Authorization: `Bearer ${localStorage.token}` }
			});
			if (res.ok) {
				const data = await res.json();
				currentPlan = data.plan || 'free';
			}
		} catch {
			currentPlan = 'free';
		}
		loading = false;
	}

	async function goToCheckout(planId: string) {
		try {
			const res = await fetch(`${WEBUI_BASE_URL}/api/v1/clapnclaw/billing/checkout`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.token}` },
				body: JSON.stringify({ plan: planId })
			});
			if (res.ok) {
				const data = await res.json();
				if (data.checkout_url) { window.location.href = data.checkout_url; return; }
			}
		} catch {}
		window.location.href = `mailto:hola@clapnclaw.com?subject=Upgrade%20${planId}`;
	}

	async function buyAddon(packId: string) {
		try {
			const res = await fetch(`${WEBUI_BASE_URL}/api/v1/clapnclaw/billing/token-addon`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.token}` },
				body: JSON.stringify({ pack: packId })
			});
			if (res.ok) {
				const data = await res.json();
				if (data.checkout_url) { window.location.href = data.checkout_url; return; }
			}
		} catch {}
		window.location.href = `mailto:hola@clapnclaw.com?subject=Token%20addon%20${packId}`;
	}

	async function openPortal() {
		portalLoading = true;
		try {
			const res = await fetch(`${WEBUI_BASE_URL}/api/v1/clapnclaw/billing/portal`, {
				method: 'POST',
				headers: { Authorization: `Bearer ${localStorage.token}` }
			});
			if (res.ok) {
				const data = await res.json();
				if (data.portal_url) { window.open(data.portal_url, '_blank'); portalLoading = false; return; }
			}
		} catch {}
		portalLoading = false;
		window.location.href = 'mailto:hola@clapnclaw.com?subject=Facturas';
	}

	function ctaAction(plan: any, i: number) {
		if (i === effectiveIdx || i < effectiveIdx) return;
		if (plan.contact) { window.location.href = 'mailto:hola@clapnclaw.com?subject=Enterprise'; return; }
		goToCheckout(plan.id);
	}

	onMount(fetchCurrentPlan);
</script>

<svelte:head>
	<title>{$i18n.t('Plans')} | {$WEBUI_NAME}</title>
</svelte:head>

<div
	class="flex-1 w-full flex flex-col min-h-screen max-w-5xl
	{$showSidebar ? 'md:max-w-[calc(100%-var(--sidebar-width))] ml-auto mr-0' : 'mx-auto'}"
>
	{#if $mobile}
		<nav class="sticky top-0 z-30 w-full backdrop-blur-xl drag-region">
			<div
				class="flex items-center justify-between px-3 py-2 border-b border-black/[.06] dark:border-white/[.06] dark:bg-gray-900/90"
				style="background:rgba(245,240,232,.92)"
			>
				<div class="flex items-center gap-2">
					<button
						class="p-1.5 rounded-lg hover:bg-black/[.06] dark:hover:bg-white/[.06] transition cursor-pointer"
						on:click={async () => { showSidebar.set(true); await tick(); }}
						aria-label={$i18n.t('Open menu')}
					>
						<Sidebar />
					</button>
					<span class="text-sm font-semibold" style="color:#0D5C3F">{$i18n.t('Plans')}</span>
				</div>
				{#if $user}
					<UserMenu role={$user?.role} className="max-w-[220px]">
						<button class="rounded-full cursor-pointer hover:opacity-80 transition">
							<img src="{WEBUI_API_BASE_URL}/users/{$user?.id}/profile/image" class="size-7 rounded-full object-cover" alt="Profile" />
						</button>
					</UserMenu>
				{/if}
			</div>
		</nav>
	{/if}

	<div class="flex-1 px-4 md:px-6 py-8 md:py-12">
		<!-- Header -->
		<div class="mb-7 flex items-start justify-between">
			<div>
				<h1 class="text-sm font-medium text-gray-900 dark:text-white">{$i18n.t('Plans & Pricing')}</h1>
				<p class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{$i18n.t('Private AI for European businesses · data always in the EU')}</p>
			</div>
			{#if currentPlan && currentPlan !== 'free'}
				<button
					class="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors cursor-pointer"
					on:click={openPortal}
					disabled={portalLoading}
				>
					<svg class="size-3.5" viewBox="0 0 16 16" fill="none">
						<rect x="2" y="3" width="12" height="10" rx="1.5" stroke="currentColor" stroke-width="1.2"/>
						<path d="M5 7h6M5 9.5h4" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
					</svg>
					{portalLoading ? $i18n.t('Opening...') : $i18n.t('My invoices')}
				</button>
			{/if}
		</div>

		{#if loading}
			<div class="flex justify-center py-20">
				<div class="size-7 border-[3px] rounded-full animate-spin" style="border-color:#0D5C3F transparent transparent transparent" />
			</div>
		{:else}
			<!-- Plan cards -->
			<div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
				{#each plans as plan, i}
					{@const isCurrent = i === effectiveIdx}
					{@const isUpgrade = i > effectiveIdx}
					<div
						class="relative flex flex-col rounded-2xl border transition-shadow
							{plan.highlight ? 'shadow-lg' : ''}
							bg-white dark:bg-gray-800"
						style={plan.highlight
							? 'border-color:#0D5C3F'
							: isCurrent
							? 'border-color:rgba(13,92,63,.3)'
							: 'border-color:rgba(0,0,0,.07)'}
					>
						{#if plan.highlight}
							<div class="absolute -top-3 left-1/2 -translate-x-1/2 text-[10px] font-bold px-3 py-1 rounded-full whitespace-nowrap" style="background:#0D5C3F;color:#F5F0E8">
								{$i18n.t('Most popular')}
							</div>
						{/if}

						<div class="p-5 flex flex-col flex-1">
							<p class="text-[9px] font-semibold uppercase tracking-[.12em] text-gray-400 dark:text-white/30 mb-1">{plan.sublabel}</p>

							<div class="flex items-start justify-between mb-3">
								<span class="text-sm font-bold text-gray-800 dark:text-white">{plan.label}</span>
								{#if isCurrent}
									<span class="text-[9px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded" style="background:rgba(13,92,63,.1);color:#0D5C3F">{$i18n.t('Current')}</span>
								{/if}
							</div>

							<div class="mb-4">
								<span class="text-3xl font-bold text-gray-900 dark:text-white">{plan.price}</span>
								{#if plan.period}
									<span class="text-sm text-gray-400">{plan.period}</span>
								{/if}
							</div>

							<div class="h-px mb-4" style="background:rgba(0,0,0,.06)" />

							<ul class="space-y-2 mb-6 flex-1">
								{#each plan.features as feat}
									<li class="flex items-start gap-2">
										<svg class="size-3.5 mt-0.5 shrink-0" viewBox="0 0 16 16" fill="none">
											<path d="M4 8l3 3 5-5" stroke="#0D5C3F" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
										</svg>
										<span class="text-xs text-gray-600 dark:text-gray-300">{feat}</span>
									</li>
								{/each}
							</ul>

							{#if isCurrent}
								<button disabled class="w-full py-2.5 rounded-xl text-xs font-semibold border border-black/[.08] text-gray-400 dark:text-gray-500 cursor-default">
									{$i18n.t('Current plan')}
								</button>
							{:else if isUpgrade}
								<button
									class="w-full py-2.5 rounded-xl text-xs font-semibold transition-all cursor-pointer hover:opacity-90 active:scale-[.98]"
									style={plan.highlight
										? 'background:#0D5C3F;color:#F5F0E8'
										: 'background:rgba(13,92,63,.1);color:#0D5C3F'}
									on:click={() => ctaAction(plan, i)}
								>
									{plan.contact
										? $i18n.t('Request demo')
										: $i18n.t('Upgrade to {{plan}}', { plan: plan.label })}
								</button>
							{:else}
								<button disabled class="w-full py-2.5 rounded-xl text-xs font-semibold border border-black/[.08] text-gray-300 dark:text-gray-600 cursor-default">
									{$i18n.t('Lower plan')}
								</button>
							{/if}
						</div>
					</div>
				{/each}
			</div>

			<!-- Token addon packs -->
			<div class="rounded-2xl border border-black/[.07] dark:border-white/[.07] bg-white dark:bg-gray-800 px-5 py-4 mb-6">
				<p class="text-[10px] font-semibold uppercase tracking-[.12em] text-gray-400 dark:text-white/40 mb-3">{$i18n.t('Extra token packs')}</p>
				<div class="flex flex-wrap gap-3">
					{#each addonPacks as pack}
						<div class="flex items-center gap-4 px-4 py-3 rounded-xl border border-black/[.06] dark:border-white/[.06]">
							<div>
								<p class="text-xs font-semibold text-gray-700 dark:text-gray-200">{pack.label}</p>
								<p class="text-[10px] text-gray-400">{pack.desc}</p>
							</div>
							<span class="text-sm font-bold text-gray-900 dark:text-white">{pack.price}</span>
							<button
								class="text-[10px] font-semibold px-3 py-1.5 rounded-lg cursor-pointer hover:opacity-90 active:scale-[.97] transition-all"
								style="background:rgba(13,92,63,.1);color:#0D5C3F"
								on:click={() => buyAddon(pack.id)}
							>
								{$i18n.t('Buy')}
							</button>
						</div>
					{/each}
				</div>
			</div>

			<!-- Footer -->
			<div class="flex items-center justify-between flex-wrap gap-3">
				<p class="text-xs text-gray-400 dark:text-gray-500">
					{$i18n.t('Custom plan?')}
					<a href="mailto:hola@clapnclaw.com?subject=Enterprise" class="underline hover:text-gray-600 dark:hover:text-gray-300 transition-colors">{$i18n.t('Contact us')}</a>
				</p>
				{#if currentPlan && currentPlan !== 'free'}
					<button
						class="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 underline transition-colors cursor-pointer"
						on:click={openPortal}
						disabled={portalLoading}
					>
						{portalLoading ? $i18n.t('Opening...') : $i18n.t('View invoices and manage subscription')}
					</button>
				{/if}
			</div>
			<p class="text-[11px] text-gray-300 dark:text-gray-600 mt-3">
				{$i18n.t('All data processed on EU servers (Frankfurt) · GDPR compliant')}
			</p>
		{/if}
	</div>
</div>
