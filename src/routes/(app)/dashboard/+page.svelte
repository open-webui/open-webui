<script lang="ts">
	import { onMount, getContext, tick } from 'svelte';
	import { WEBUI_BASE_URL, WEBUI_API_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, showSidebar, user, mobile } from '$lib/stores';
	import { changeLanguage } from '$lib/i18n';
	import IntegrationsCard from '$lib/components/dashboard/IntegrationsCard.svelte';
	import ModelUsageCard from '$lib/components/dashboard/ModelUsageCard.svelte';
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';

	const i18n = getContext('i18n');

	let billing: any = null;
	let modelStats: { model: string; tokens: number; requests: number }[] = [];
	let loading = true;
	let currentLang = '';
	let currentTheme = '';

	const plans = [
		{ id: 'free',       label: 'Free',       tokens: '50K', price: '€0'  },
		{ id: 'starter',    label: 'Starter',    tokens: '1M',  price: '€20' },
		{ id: 'pro',        label: 'Pro',        tokens: '3M',  price: '€79' },
		{ id: 'enterprise', label: 'Enterprise', tokens: '5M',  price: '€99' },
	];

	$: currentPlan = billing?.plan?.toLowerCase() ?? 'free';
	$: currentIdx = plans.findIndex((p) => p.id === currentPlan);
	$: effectiveIdx = currentIdx < 0 ? 0 : currentIdx;
	$: tokensUsed = billing?.tokens_used ?? 0;
	$: tokensTotal = billing?.tokens_effective ?? billing?.tokens_limit ?? 0;
	$: tokensPct = tokensTotal > 0 ? Math.min(100, Math.round((tokensUsed / tokensTotal) * 100)) : 0;
	$: connected = billing !== null && tokensTotal > 0;

	function daysLeft() {
		const d = new Date();
		const next = new Date(d.getFullYear(), d.getMonth() + 1, 1);
		return Math.max(0, Math.ceil((next.getTime() - Date.now()) / 86400000));
	}

	function fmt(n: number) {
		if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
		if (n >= 1_000) return (n / 1_000).toFixed(0) + 'K';
		return n.toString();
	}

	async function fetchData() {
		loading = true;
		try {
			const res = await fetch(`${WEBUI_BASE_URL}/api/v1/clapnclaw/billing/plan`, {
				headers: { Authorization: `Bearer ${localStorage.token}` }
			});
			if (res.ok) {
				const data = await res.json();
				billing = data;
				modelStats = data.by_model || [];
			}
		} catch { /* show empty state */ }
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
		} catch { /* fall through */ }
		window.location.href = `mailto:hola@clapnclaw.com?subject=Upgrade%20a%20${planId}`;
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

	$: addonPacks = [
		{ id: 'small', label: '+500K Tokens', price: '€19', desc: $i18n.t('One-time payment') },
		{ id: 'large', label: '+2M Tokens', price: '€59', desc: $i18n.t('One-time payment') }
	];

	function loadPreferences() {
		currentLang = $i18n.language;
		currentTheme = localStorage.theme ?? 'system';
	}

	function applyTheme(theme: string) {
		currentTheme = theme;
		localStorage.theme = theme;
		const root = document.documentElement;
		root.classList.remove('dark', 'oled-dark');
		if (theme === 'dark' || theme === 'oled-dark') {
			root.classList.add('dark');
			if (theme === 'oled-dark') root.classList.add('oled-dark');
		} else if (theme === 'system') {
			if (window.matchMedia('(prefers-color-scheme: dark)').matches) root.classList.add('dark');
		}
	}

	async function handleLangChange(code: string) {
		await changeLanguage(code);
		currentLang = code;
	}

	onMount(async () => {
		loadPreferences();
		await fetchData();
	});

	$: today = new Date().toLocaleDateString($i18n.language || 'en', { weekday: 'long', day: 'numeric', month: 'long' });
</script>

<svelte:head>
	<title>{$i18n.t('My Account')} | {$WEBUI_NAME}</title>
</svelte:head>

<div
	class="flex-1 w-full flex flex-col min-h-screen max-w-4xl
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
						aria-label="Abrir menú"
					>
						<Sidebar />
					</button>
					<span class="text-sm font-semibold" style="color:#0D5C3F">{$i18n.t('My Account')}</span>
				</div>
				{#if $user}
					<UserMenu role={$user?.role} className="max-w-[220px]">
						<button class="rounded-full cursor-pointer hover:opacity-80 transition">
							<img src="{WEBUI_API_BASE_URL}/users/{$user?.id}/profile/image" class="size-7 rounded-full object-cover" alt="Perfil" />
						</button>
					</UserMenu>
				{/if}
			</div>
		</nav>
	{/if}

	<div class="flex-1 px-4 md:px-6 py-6 md:py-10">
		<!-- Header -->
		<div class="mb-7">
			<h1 class="text-sm font-medium text-gray-900 dark:text-white">{$i18n.t('My Account')}</h1>
			<p class="text-xs text-gray-400 dark:text-gray-500 capitalize mt-0.5">{today}</p>
		</div>

		{#if loading}
			<div class="flex justify-center py-20">
				<div class="size-6 border-[2.5px] rounded-full animate-spin" style="border-color:#0D5C3F transparent transparent transparent" />
			</div>
		{:else}
			<div class="flex flex-col gap-4">

				<!-- ── PLAN + TOKENS ROW ── -->
				<div class="rounded-2xl border bg-white dark:bg-gray-800 border-black/[.07] dark:border-white/[.07] overflow-hidden">

					<!-- Plan rail -->
					<div class="px-5 pt-5 pb-4 border-b border-black/[.05] dark:border-white/[.05]">
						<div class="flex items-center justify-between mb-3">
							<p class="text-[10px] font-semibold uppercase tracking-[.12em] text-gray-400 dark:text-white/40">Plan</p>
							<span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full" style="background:#0D5C3F;color:#F5F0E8">
								{plans[effectiveIdx]?.label ?? 'Free'}
							</span>
						</div>
						<div class="grid grid-cols-4 gap-2">
							{#each plans as plan, i}
								{@const isCurrent = i === effectiveIdx}
								{@const isUpgrade = i > effectiveIdx}
								<button
									class="flex flex-col items-start px-3 py-2.5 rounded-xl border transition-all text-left
										{isCurrent ? 'cursor-default' : isUpgrade ? 'cursor-pointer hover:-translate-y-0.5 hover:shadow-sm' : 'cursor-default opacity-40'}"
									style={isCurrent
										? 'border-color:#0D5C3F;background:rgba(13,92,63,.06)'
										: 'border-color:rgba(0,0,0,.07)'}
									disabled={!isUpgrade}
									on:click={() => isUpgrade && (plan.id === 'enterprise' ? window.location.href = 'mailto:hola@clapnclaw.com?subject=Enterprise' : goToCheckout(plan.id))}
								>
									<div class="flex items-center justify-between w-full mb-1">
										<span class="text-[10px] font-semibold uppercase tracking-wide" style={isCurrent ? 'color:#0D5C3F' : 'color:rgba(0,0,0,.4)'}>
											{plan.label}
										</span>
										{#if isCurrent}
											<span class="text-[8px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded" style="background:rgba(13,92,63,.12);color:#0D5C3F">{$i18n.t('Current')}</span>
										{:else if isUpgrade}
											<span class="text-[9px] text-gray-300 dark:text-gray-600">→</span>
										{/if}
									</div>
									<span class="text-sm font-bold text-gray-800 dark:text-white">{plan.price}</span>
									<span class="text-[9px] text-gray-400 dark:text-gray-500 mt-0.5">{plan.tokens} {$i18n.t('tokens/month')}</span>
								</button>
							{/each}
						</div>
					</div>

					<!-- Token strip -->
					<div class="px-5 py-4">
						{#if connected}
							<div class="flex items-center gap-6">
								<!-- Usage bar -->
								<div class="flex-1">
									<div class="flex items-center justify-between mb-1.5">
										<p class="text-[10px] font-semibold uppercase tracking-[.1em] text-gray-400 dark:text-white/40">{$i18n.t('Tokens this month')}</p>
										<span class="text-[10px] font-mono font-semibold" style="color:#0D5C3F">{tokensPct}%</span>
									</div>
									<div class="h-1.5 rounded-full overflow-hidden" style="background:rgba(13,92,63,.1)">
										<div
											class="h-full rounded-full transition-all duration-1000"
											style="width:{tokensPct}%;background:{billing?.blocked ? '#de3514' : billing?.alert ? '#E07020' : '#0D5C3F'}"
										/>
									</div>
									<div class="flex items-center justify-between mt-1.5">
										<span class="text-[10px] font-mono text-gray-400">{fmt(tokensUsed)} {$i18n.t('used')}</span>
										<span class="text-[10px] font-mono text-gray-400">{fmt(tokensTotal)} {$i18n.t('total')}</span>
									</div>
								</div>
								<!-- Days left chip -->
								<div class="shrink-0 text-center px-4 py-2.5 rounded-xl" style="background:rgba(13,92,63,.06)">
									<p class="text-lg font-mono font-bold leading-none" style="color:#0D5C3F">{daysLeft()}</p>
									<p class="text-[9px] text-gray-400 mt-0.5 uppercase tracking-wide">{$i18n.t('days')}</p>
								</div>
							</div>
						{:else}
							<div class="flex items-center gap-3">
								<div class="size-1.5 rounded-full" style="background:rgba(13,92,63,.2)" />
								<p class="text-xs text-gray-400 dark:text-gray-500">
									Configura <code class="font-mono text-[10px] px-1 py-0.5 rounded" style="background:rgba(0,0,0,.05)">CLAPNCLAW_WORKSPACE_SECRET</code> en <code class="font-mono text-[10px] px-1 py-0.5 rounded" style="background:rgba(0,0,0,.05)">.env.dev</code> para ver el uso en tiempo real
								</p>
							</div>
						{/if}
					</div>
				</div>

				<!-- ── MODEL USAGE ── -->
				<ModelUsageCard {modelStats} totalUsed={tokensUsed} />

				<!-- ── INTEGRATIONS ── -->
				<IntegrationsCard />

				<!-- ── ADDON PACKS ── -->
				<div class="rounded-2xl px-5 py-4 border bg-white dark:bg-gray-800 border-black/[.07] dark:border-white/[.07]">
					<p class="text-[10px] font-semibold uppercase tracking-[.12em] text-gray-400 dark:text-white/40 mb-3">{$i18n.t('Extra Token Packs')}</p>
					<div class="flex flex-wrap gap-3">
						{#each addonPacks as pack}
							<div class="flex items-center justify-between gap-4 px-4 py-3 rounded-xl border border-black/[.07] dark:border-white/[.07] flex-1 min-w-[180px]">
								<div>
									<p class="text-sm font-bold text-gray-800 dark:text-white">{pack.label}</p>
									<p class="text-[10px] text-gray-400 dark:text-gray-500 mt-0.5">{pack.desc}</p>
								</div>
								<div class="flex items-center gap-2 shrink-0">
									<span class="text-base font-bold" style="color:#0D5C3F">{pack.price}</span>
									<button
										class="text-[10px] font-semibold px-2.5 py-1 rounded-full border border-black/[.12] dark:border-white/[.12] text-gray-600 dark:text-gray-300 hover:bg-black/[.05] dark:hover:bg-white/[.05] transition cursor-pointer"
										on:click={() => buyAddon(pack.id)}
									>
										{$i18n.t('Buy')}
									</button>
								</div>
							</div>
						{/each}
					</div>
				</div>

				<!-- ── PREFERENCES ── -->
				<div class="rounded-2xl px-5 py-4 border bg-white dark:bg-gray-800 border-black/[.07] dark:border-white/[.07]">
					<p class="text-[10px] font-semibold uppercase tracking-[.12em] text-gray-400 dark:text-white/40 mb-3">{$i18n.t('Preferences')}</p>
					<div class="flex flex-wrap gap-4 items-center">
						<div class="flex items-center gap-2">
							<span class="text-xs text-gray-500 dark:text-gray-400 shrink-0">{$i18n.t('Language')}</span>
							<div class="flex gap-1">
								{#each [['en-US','🇺🇸 EN'],['de-DE','🇩🇪 DE'],['es-ES','🇪🇸 ES']] as [code, label]}
									<button
										class="text-xs px-2.5 py-1.5 rounded-lg border transition-all cursor-pointer"
										class:font-semibold={currentLang === code || currentLang.startsWith(code.split('-')[0])}
										style={currentLang === code || currentLang.startsWith(code.split('-')[0])
											? 'background:#0D5C3F;color:#F5F0E8;border-color:#0D5C3F'
											: 'border-color:rgba(0,0,0,.08);color:rgba(0,0,0,.5)'}
										on:click={() => handleLangChange(code)}
									>
										{label}
									</button>
								{/each}
							</div>
						</div>
						<div class="flex items-center gap-2">
							<span class="text-xs text-gray-500 dark:text-gray-400 shrink-0">{$i18n.t('Theme')}</span>
							<div class="flex gap-1">
								{#each [['light','☀️ ' + $i18n.t('Light')],['dark','🌑 ' + $i18n.t('Dark')],['system','⚙️ ' + $i18n.t('System')]] as [val, label]}
									<button
										class="text-xs px-2.5 py-1.5 rounded-lg border transition-all cursor-pointer"
										class:font-semibold={currentTheme === val}
										style={currentTheme === val
											? 'background:#0D5C3F;color:#F5F0E8;border-color:#0D5C3F'
											: 'border-color:rgba(0,0,0,.08);color:rgba(0,0,0,.5)'}
										on:click={() => applyTheme(val)}
									>
										{label}
									</button>
								{/each}
							</div>
						</div>
					</div>
				</div>

			</div>
		{/if}
	</div>
</div>
