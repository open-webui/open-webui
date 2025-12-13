<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	import {
		createCreditsCheckout,
		getCreditsStatus,
		type CreditsDomain,
		type CreditsStatus,
		type DomainCreditsStatus
	} from '$lib/apis/credits';
	import { user } from '$lib/stores';

	const i18n = getContext('i18n');

	export let show = false;

	let loading = false;
	let checkoutLoading = false;

	let status: CreditsStatus | null = null;
	let error: string | null = null;

	let activeDomain: CreditsDomain = 'audio';

	const DOMAIN_ORDER: CreditsDomain[] = ['audio', 'photo', 'video', 'music'];
	const DOMAIN_LABELS: Record<CreditsDomain, string> = {
		audio: 'აუდიო კრედიტები',
		video: 'ვიდეო კრედიტები',
		photo: 'ფოტო კრედიტები',
		music: 'მუსიკის კრედიტები'
	};

	const unitLabel = (unit: string) => {
		const u = (unit || '').toLowerCase();
		if (u === 'credits') return 'კრედიტები';
		if (u === 'generations') return 'გენერაციები';
		return unit;
	};

	const getDomain = (domain: CreditsDomain): DomainCreditsStatus | null => {
		if (!status?.domains) return null;
		return (status.domains[domain] as DomainCreditsStatus) ?? null;
	};

	const load = async () => {
		loading = true;
		error = null;

		const token = localStorage.token;
		if (!token) {
			status = null;
			error = 'გთხოვთ შეხვიდეთ სისტემაში კრედიტების სანახავად.';
			loading = false;
			return;
		}

		try {
			status = await getCreditsStatus(token);
		} catch (e) {
			status = null;
			error = `${e}`;
		} finally {
			loading = false;
		}
	};

	const openCheckout = async (packageCode: string) => {
		const token = localStorage.token;
		if (!token) {
			toast.error('გთხოვთ შეხვიდეთ სისტემაში.');
			return;
		}

		checkoutLoading = true;
		try {
			const res = await createCreditsCheckout(token, packageCode, 'audio');
			if (res?.url) {
				window.open(res.url, '_blank');
			}
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			checkoutLoading = false;
		}
	};

	$: if (show) {
		void load();
	}

	$: if (show && status) {
		const current = getDomain(activeDomain);
		if (!current) {
			activeDomain = DOMAIN_ORDER.find((d) => Boolean(getDomain(d))) ?? 'audio';
		}
	}
</script>

<Modal bind:show size="lg">
	<div class="px-6 pt-5 text-gray-700 dark:text-gray-100">
		<div class="flex justify-between items-start">
			<div class="text-xl font-medium">კრედიტები</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
				aria-label={$i18n.t('Close')}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		{#if status && !status.redis_available}
			<div class="mt-3 text-xs rounded-lg border border-gray-200 dark:border-gray-800 p-2 text-gray-600 dark:text-gray-300">
				{#if $user?.role === 'admin'}
					Redis გამორთულია — Admin: შეუზღუდავი (არ იკავება)
				{:else}
					კრედიტების სისტემა დროებით მიუწვდომელია.
				{/if}
			</div>
		{/if}
	</div>

	<div class="px-6 pb-6 pt-4 text-gray-700 dark:text-gray-100">
		{#if loading}
			<div class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
				<Spinner className="size-4" />{$i18n.t('Loading...')}
			</div>
		{:else if error}
			<div class="text-sm text-amber-700 dark:text-amber-400">{error}</div>
		{:else if status}
			<div class="flex flex-wrap gap-2 mb-4">
				{#each DOMAIN_ORDER as domain}
					{#if getDomain(domain)}
						<button
							type="button"
							on:click={() => {
								activeDomain = domain;
							}}
							class="px-3 py-1.5 text-sm rounded-xl border transition {activeDomain === domain
								? 'bg-blue-500/15 border-blue-500/30 text-blue-700 dark:text-blue-200'
								: 'bg-transparent border-gray-200 dark:border-gray-800 text-gray-700 dark:text-gray-200 hover:bg-black/5 dark:hover:bg-white/5'}"
						>
							{DOMAIN_LABELS[domain]}
						</button>
					{/if}
				{/each}
			</div>

			{#if getDomain(activeDomain) as domainStatus}
				<div class="rounded-xl border border-gray-100 dark:border-gray-800 p-4">
					<div class="text-sm text-gray-600 dark:text-gray-300 mb-3">
						ერთეული: {unitLabel(domainStatus.unit)}
					</div>

					{#if !domainStatus.enforced}
						<div class="text-sm font-medium">შეუზღუდავი (არ იკავება)</div>
					{:else}
						<div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
							<div class="rounded-xl bg-gray-50 dark:bg-gray-900/40 p-3">
								<div class="text-xs text-gray-500 dark:text-gray-400">უფასო</div>
								<div class="text-lg font-semibold">{domainStatus.free_remaining}</div>
								<div class="text-xs text-gray-500 dark:text-gray-400">
									{domainStatus.free_used} / {domainStatus.free_limit}
								</div>
							</div>

							<div class="rounded-xl bg-gray-50 dark:bg-gray-900/40 p-3">
								<div class="text-xs text-gray-500 dark:text-gray-400">შეძენილი</div>
								<div class="text-lg font-semibold">{domainStatus.paid_remaining}</div>
								<div class="text-xs text-gray-500 dark:text-gray-400">
									ბალანსი: {domainStatus.paid_balance}
								</div>
							</div>

							<div class="rounded-xl bg-gray-50 dark:bg-gray-900/40 p-3">
								<div class="text-xs text-gray-500 dark:text-gray-400">ჯამში</div>
								<div class="text-lg font-semibold">{domainStatus.total_remaining}</div>
								<div class="text-xs text-gray-500 dark:text-gray-400">&nbsp;</div>
							</div>
						</div>

						{#if domainStatus.cost}
							<div class="mt-3 text-xs text-gray-500 dark:text-gray-400">
								ღირებულება: 1 გენერაცია = {domainStatus.cost} კრედიტი
							</div>
						{/if}
					{/if}
				</div>

				{#if domainStatus.packages?.length}
					<div class="mt-5">
						<div class="text-sm font-medium">პაკეტები</div>
						<div class="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-2">
							{#each domainStatus.packages as pkg}
								<div class="flex items-center justify-between gap-3 rounded-xl border border-gray-100 dark:border-gray-800 p-3">
									<div class="min-w-0">
										<div class="text-sm font-medium truncate">{pkg.label}</div>
										<div class="text-xs text-gray-500 dark:text-gray-400 truncate">
											{pkg.price_label}
										</div>
									</div>

									{#if activeDomain === 'audio'}
										<button
											type="button"
											disabled={!pkg.enabled || checkoutLoading}
											on:click={() => void openCheckout(pkg.package_code)}
											class="shrink-0 px-3 py-1.5 rounded-xl text-xs font-medium transition disabled:opacity-60 disabled:cursor-not-allowed {pkg.enabled
												? 'bg-gray-900 hover:bg-gray-800 text-white dark:bg-white dark:hover:bg-gray-100 dark:text-gray-900'
												: 'bg-gray-200 dark:bg-gray-800 text-gray-500 dark:text-gray-400'}"
										>
											{#if checkoutLoading}
												<Spinner className="size-3" />
											{:else}
												ყიდვა
											{/if}
										</button>
									{/if}
								</div>
							{/each}
						</div>

						{#if activeDomain !== 'audio'}
							<div class="mt-2 text-xs text-gray-500 dark:text-gray-400">
								ამ დომენისთვის გადახდა ჯერ არ არის ჩართული.
							</div>
						{/if}
					</div>
				{/if}
			{/if}
		{/if}
	</div>
</Modal>
