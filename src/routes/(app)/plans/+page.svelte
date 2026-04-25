<script lang="ts">
	import { onMount, getContext, tick } from 'svelte';
	import { WEBUI_BASE_URL, WEBUI_API_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, showSidebar, user, mobile } from '$lib/stores';
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';

	const i18n = getContext('i18n');

	let currentPlan = '';
	let loading = true;

	const plans = [
		{
			id: 'free',
			label: 'Free',
			price: '€0',
			period: '',
			tokens: '50K',
			users: '1 usuario',
			desc: 'Para empezar sin compromiso',
			features: ['50.000 tokens/mes', '1 usuario', 'Claude Haiku', 'Acceso a integraciones básicas'],
			cta: 'Plan actual',
			highlight: false
		},
		{
			id: 'starter',
			label: 'Starter',
			price: '€82',
			period: '/mes',
			tokens: '500K',
			users: 'Hasta 5 usuarios',
			desc: 'Ideal para equipos pequeños',
			features: ['500.000 tokens/mes', 'Hasta 5 usuarios', 'Claude Haiku + Sonnet', 'Soporte por email', 'Integraciones Google/Microsoft'],
			cta: 'Upgrade a Starter',
			highlight: false
		},
		{
			id: 'pro',
			label: 'Pro',
			price: '€164',
			period: '/mes',
			tokens: '2M',
			users: 'Hasta 15 usuarios',
			desc: 'Para equipos en crecimiento',
			features: ['2.000.000 tokens/mes', 'Hasta 15 usuarios', 'Todos los modelos', 'Soporte prioritario', 'Integraciones avanzadas', 'Analytics de uso'],
			cta: 'Upgrade a Pro',
			highlight: true
		},
		{
			id: 'business',
			label: 'Business',
			price: '€328',
			period: '/mes',
			tokens: '5M',
			users: 'Hasta 30 usuarios',
			desc: 'Para firmas y equipos grandes',
			features: ['5.000.000 tokens/mes', 'Hasta 30 usuarios', 'Todos los modelos', 'Account manager dedicado', 'SLA garantizado', 'Onboarding personalizado', 'Factura alemana (UStG)'],
			cta: 'Upgrade a Business',
			highlight: false
		}
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
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify({ plan: planId })
			});
			if (res.ok) {
				const data = await res.json();
				if (data.checkout_url) {
					window.location.href = data.checkout_url;
					return;
				}
			}
		} catch { /* fall through */ }
		window.location.href = `mailto:hola@clapnclaw.com?subject=Upgrade%20a%20${planId}`;
	}

	function ctaAction(plan: typeof plans[0], i: number) {
		if (i === effectiveIdx) return; // current plan
		if (i < effectiveIdx) return;  // downgrade — do nothing
		if (plan.id === 'free') return;
		goToCheckout(plan.id);
	}

	onMount(fetchCurrentPlan);
</script>

<svelte:head>
	<title>Planes | {$WEBUI_NAME}</title>
</svelte:head>

<div
	class="flex-1 w-full flex flex-col min-h-screen max-w-5xl
	{$showSidebar ? 'md:max-w-[calc(100%-var(--sidebar-width))] ml-auto mr-0' : 'mx-auto'}"
>
	<!-- Mobile top bar -->
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
						aria-label="Abrir menú"
					>
						<Sidebar />
					</button>
					<span class="text-sm font-semibold" style="color:#0D5C3F">Planes</span>
				</div>
				{#if $user}
					<UserMenu role={$user?.role} className="max-w-[220px]">
						<button class="rounded-full cursor-pointer hover:opacity-80 transition">
							<img
								src="{WEBUI_API_BASE_URL}/users/{$user?.id}/profile/image"
								class="size-7 rounded-full object-cover"
								alt="Perfil"
							/>
						</button>
					</UserMenu>
				{/if}
			</div>
		</nav>
	{/if}

	<!-- Content -->
	<div class="flex-1 px-4 md:px-6 py-8 md:py-12">
		<!-- Header -->
		<div class="mb-8 md:mb-10">
			<h1 class="text-lg font-semibold text-gray-900 dark:text-white">Planes y precios</h1>
			<p class="text-sm text-gray-400 dark:text-gray-500 mt-1">
				IA privada para empresas europeas — datos siempre en la UE
			</p>
		</div>

		{#if loading}
			<div class="flex justify-center py-20">
				<div
					class="size-7 border-[3px] rounded-full animate-spin"
					style="border-color:#0D5C3F transparent transparent transparent"
				/>
			</div>
		{:else}
			<!-- Plan cards grid -->
			<div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
				{#each plans as plan, i}
					{@const isCurrent = i === effectiveIdx}
					{@const isUpgrade = i > effectiveIdx}
					{@const isHighlight = plan.highlight}
					<div
						class="relative flex flex-col rounded-2xl border transition-shadow
							{isHighlight ? 'shadow-lg' : ''}
							{isCurrent ? 'border-[#0D5C3F]/30' : 'border-black/[.07] dark:border-white/[.07]'}
							bg-white dark:bg-gray-800"
						style={isHighlight ? 'border-color:#0D5C3F' : ''}
					>
						<!-- Popular badge -->
						{#if isHighlight}
							<div
								class="absolute -top-3 left-1/2 -translate-x-1/2 text-[10px] font-bold px-3 py-1 rounded-full whitespace-nowrap"
								style="background:#0D5C3F;color:#F5F0E8"
							>
								Más popular
							</div>
						{/if}

						<div class="p-5 flex flex-col flex-1">
							<!-- Plan name + current badge -->
							<div class="flex items-start justify-between mb-3">
								<div>
									<span class="text-xs font-semibold uppercase tracking-[.1em] text-gray-400 dark:text-white/40">
										{plan.label}
									</span>
									{#if isCurrent}
										<div class="mt-1">
											<span
												class="text-[9px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded"
												style="background:rgba(13,92,63,.1);color:#0D5C3F"
											>Plan actual</span>
										</div>
									{/if}
								</div>
							</div>

							<!-- Price -->
							<div class="mb-4">
								<span class="text-3xl font-bold text-gray-900 dark:text-white">{plan.price}</span>
								{#if plan.period}
									<span class="text-sm text-gray-400">{plan.period}</span>
								{/if}
							</div>

							<!-- Desc -->
							<p class="text-xs text-gray-500 dark:text-gray-400 mb-4">{plan.desc}</p>

							<!-- Key stats -->
							<div
								class="flex gap-3 mb-4 px-3 py-2.5 rounded-xl"
								style="background:rgba(13,92,63,.04)"
							>
								<div class="text-center flex-1">
									<div class="text-sm font-bold" style="color:#0D5C3F">{plan.tokens}</div>
									<div class="text-[9px] text-gray-400 uppercase tracking-wide">tokens/mes</div>
								</div>
								<div class="w-px bg-black/[.06]" />
								<div class="text-center flex-1">
									<div class="text-sm font-bold text-gray-700 dark:text-gray-300">{plan.users}</div>
									<div class="text-[9px] text-gray-400 uppercase tracking-wide">usuarios</div>
								</div>
							</div>

							<!-- Features -->
							<ul class="space-y-2 mb-6 flex-1">
								{#each plan.features as feat}
									<li class="flex items-start gap-2">
										<svg class="size-3.5 mt-0.5 shrink-0" viewBox="0 0 16 16" fill="none">
											<circle cx="8" cy="8" r="7" fill="rgba(13,92,63,.1)"/>
											<path d="M5 8l2 2 4-4" stroke="#0D5C3F" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
										</svg>
										<span class="text-xs text-gray-600 dark:text-gray-300">{feat}</span>
									</li>
								{/each}
							</ul>

							<!-- CTA -->
							{#if isCurrent}
								<button
									disabled
									class="w-full py-2.5 rounded-xl text-xs font-semibold border border-black/[.08] text-gray-400 dark:text-gray-500 cursor-default"
								>
									Plan actual
								</button>
							{:else if isUpgrade && plan.id !== 'free'}
								<button
									class="w-full py-2.5 rounded-xl text-xs font-semibold transition-all cursor-pointer hover:opacity-90 active:scale-[.98]"
									style={isHighlight
										? 'background:#0D5C3F;color:#F5F0E8'
										: 'background:rgba(13,92,63,.1);color:#0D5C3F'}
									on:click={() => ctaAction(plan, i)}
								>
									{plan.cta}
								</button>
							{:else}
								<button
									disabled
									class="w-full py-2.5 rounded-xl text-xs font-semibold border border-black/[.08] text-gray-300 dark:text-gray-600 cursor-default"
								>
									{i < effectiveIdx ? 'Plan inferior' : plan.cta}
								</button>
							{/if}
						</div>
					</div>
				{/each}
			</div>

			<!-- Footer note -->
			<div class="mt-8 text-center">
				<p class="text-xs text-gray-400 dark:text-gray-500">
					¿Necesitas un plan Enterprise personalizado?
					<a
						href="mailto:hola@clapnclaw.com?subject=Plan%20Enterprise"
						class="underline hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
					>
						Contáctanos
					</a>
				</p>
				<p class="text-[11px] text-gray-300 dark:text-gray-600 mt-1">
					Todos los datos procesados en servidores EU (Frankfurt) · Conforme con RGPD
				</p>
			</div>
		{/if}
	</div>
</div>
