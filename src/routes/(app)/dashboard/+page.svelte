<script lang="ts">
	import { onMount, getContext, tick } from 'svelte';
	import { WEBUI_BASE_URL, WEBUI_API_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, showSidebar, user, mobile } from '$lib/stores';
	import { getLanguages, changeLanguage } from '$lib/i18n';

	import TokenUsageCard from '$lib/components/dashboard/TokenUsageCard.svelte';
	import PlanCard from '$lib/components/dashboard/PlanCard.svelte';
	import ModelUsageCard from '$lib/components/dashboard/ModelUsageCard.svelte';
	import IntegrationsCard from '$lib/components/dashboard/IntegrationsCard.svelte';
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';

	const i18n = getContext('i18n');

	// Billing plan response shape (from backend /billing/plan)
	let billing = {
		plan: '',
		tokens_used: 0,
		tokens_limit: 0,
		tokens_effective: 0,
		tokens_pct: 0,
		alert: false,
		blocked: false
	};
	let modelStats: { model: string; tokens: number; requests: number }[] = [];
	let loading = true;

	// Preferences
	let languages: { code: string; title: string }[] = [];
	let currentLang = '';
	let currentTheme = '';

	const PRIORITY_LANGS = ['de', 'en', 'es'];
	$: priorityLangs = languages.filter((l) => PRIORITY_LANGS.includes(l.code))
		.sort((a, b) => PRIORITY_LANGS.indexOf(a.code) - PRIORITY_LANGS.indexOf(b.code));
	$: otherLangs = languages.filter((l) => !PRIORITY_LANGS.includes(l.code));

	// Reset date = first day of next month
	function nextResetDate() {
		const d = new Date();
		return new Date(d.getFullYear(), d.getMonth() + 1, 1).toISOString();
	}

	function greeting() {
		const h = new Date().getHours();
		if (h < 12) return 'Buenos días';
		if (h < 19) return 'Buenas tardes';
		return 'Buenas noches';
	}

	function firstName(name: string) {
		return name?.split(' ')[0] ?? '';
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
		} catch {
			// API not available — show empty state
		}
		loading = false;
	}

	async function loadPreferences() {
		languages = await getLanguages();
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

	async function handleLangChange(e: Event) {
		const code = (e.target as HTMLSelectElement).value;
		await changeLanguage(code);
		currentLang = code;
	}

	onMount(async () => {
		await Promise.all([fetchData(), loadPreferences()]);
	});

	$: today = new Date().toLocaleDateString('es-ES', {
		weekday: 'long',
		day: 'numeric',
		month: 'long'
	});
</script>

<svelte:head>
	<title>Dashboard | {$WEBUI_NAME}</title>
</svelte:head>

<div
	class="flex-1 w-full flex flex-col min-h-screen max-w-4xl
	{$showSidebar ? 'md:max-w-[calc(100%-var(--sidebar-width))] ml-auto mr-0' : 'mx-auto'}"
>
	<!-- Mobile top bar — matches chat navbar style -->
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
					<span class="text-sm font-semibold" style="color:#0D5C3F">Dashboard</span>
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
	<div class="flex-1 px-4 md:px-6 py-6 md:py-10">
		<!-- Header -->
		<div class="mb-6 md:mb-8">
			<h1 class="text-sm font-medium text-gray-900 dark:text-white">Dashboard</h1>
			<p class="text-xs text-gray-400 dark:text-gray-500 capitalize mt-0.5">{today}</p>
		</div>

		{#if loading}
			<div class="flex justify-center py-20">
				<div
					class="size-7 border-[3px] rounded-full animate-spin"
					style="border-color:#0D5C3F transparent transparent transparent"
				/>
			</div>
		{:else}
			<div class="flex flex-col gap-4">
				<!-- Row 1: token usage (2/3) + plan (1/3) -->
				<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
					<div class="md:col-span-2">
						<TokenUsageCard
							used={billing.tokens_used}
							total={billing.tokens_effective || billing.tokens_limit}
							resetDate={nextResetDate()}
							alert={billing.alert}
							blocked={billing.blocked}
						/>
					</div>
					<PlanCard planName={billing.plan} />
				</div>

				<!-- Model usage -->
				<ModelUsageCard {modelStats} totalUsed={billing.tokens_used} />

				<!-- Integrations -->
				<IntegrationsCard />

				<!-- Preferences row -->
				<div class="rounded-2xl px-5 py-4 border bg-white dark:bg-gray-800 border-black/[.07] dark:border-white/[.07]">
					<p class="text-[10px] font-semibold uppercase tracking-[.12em] text-gray-400 dark:text-white/40 mb-3">
						Preferencias
					</p>
					<div class="flex flex-wrap gap-4 items-center">
						<div class="flex items-center gap-2">
							<label for="lang-select" class="text-xs text-gray-500 dark:text-gray-400 shrink-0">Idioma</label>
							<select
								id="lang-select"
								class="text-xs rounded-lg border border-black/[.07] dark:border-white/[.1] bg-transparent text-gray-700 dark:text-gray-300 px-2 py-1.5 cursor-pointer focus:outline-none"
								bind:value={currentLang}
								on:change={handleLangChange}
							>
								{#each priorityLangs as lang}
									<option value={lang.code}>{lang.title}</option>
								{/each}
								<option disabled>──────────</option>
								{#each otherLangs as lang}
									<option value={lang.code}>{lang.title}</option>
								{/each}
							</select>
						</div>

						<div class="flex items-center gap-2">
							<span class="text-xs text-gray-500 dark:text-gray-400 shrink-0">Tema</span>
							<div class="flex gap-1">
								{#each [['light','☀️ Claro'],['dark','🌑 Oscuro'],['system','⚙️ Sistema']] as [val, label]}
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
