<script>
	import { getContext, onDestroy, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	import { showSidebar } from '$lib/stores';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	import {
		getSubscriptionTiers,
		getSubscriptionChains,
		getMySubscription,
		subscribe,
		getSubscriptionOrder
	} from '$lib/apis/subscriptions';

	let loaded = false;
	let tiers = [];
	let chains = [];
	let me = null;

	// checkout state
	let checkoutTier = null;
	let selectedChainId = '';
	let order = null;
	let orderStatus = '';
	let creating = false;
	let paid = false;

	let pollTimer = null;
	let tickTimer = null;
	let now = Math.floor(Date.now() / 1000);

	const loadState = async () => {
		me = await getMySubscription(localStorage.token).catch(() => null);
	};

	const reload = async () => {
		[tiers, chains] = await Promise.all([
			getSubscriptionTiers(localStorage.token).catch(() => []),
			getSubscriptionChains(localStorage.token).catch(() => [])
		]);
		await loadState();
	};

	const priceLabel = (tier) =>
		tier.price_usd > 0 ? `${tier.price_usd} USDT` : $i18n.t('Free');

	const limitLabel = (limit) =>
		limit === null || limit === undefined
			? $i18n.t('Unlimited messages')
			: $i18n.t('{{count}} messages / day', { count: limit });

	const stopPolling = () => {
		if (pollTimer) {
			clearInterval(pollTimer);
			pollTimer = null;
		}
	};

	const closeCheckout = () => {
		stopPolling();
		checkoutTier = null;
		order = null;
		orderStatus = '';
		creating = false;
		paid = false;
	};

	const openCheckout = (tier) => {
		closeCheckout();
		checkoutTier = tier;
		selectedChainId = chains[0]?.id ?? '';
	};

	const poll = async () => {
		if (!order) return;
		try {
			const res = await getSubscriptionOrder(localStorage.token, order.order_id);
			orderStatus = res.status;
			if (res.activated || res.status === 'PAID') {
				paid = true;
				stopPolling();
				toast.success($i18n.t('Payment received — your plan is active!'));
				await loadState();
			} else if (res.status === 'EXPIRED' || res.status === 'FAILED') {
				stopPolling();
				toast.error($i18n.t('Payment {{status}}', { status: res.status }));
			}
		} catch (e) {
			// transient — keep polling
		}
	};

	const createOrder = async () => {
		if (!checkoutTier || !selectedChainId) return;
		creating = true;
		try {
			order = await subscribe(localStorage.token, checkoutTier.id, selectedChainId);
			orderStatus = order.status ?? 'PENDING';
			stopPolling();
			pollTimer = setInterval(poll, 6000);
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			creating = false;
		}
	};

	const copyAddress = async () => {
		if (!order?.address) return;
		try {
			await navigator.clipboard.writeText(order.address);
			toast.success($i18n.t('Address copied'));
		} catch (e) {
			toast.error($i18n.t('Failed to copy'));
		}
	};

	$: remaining = order?.expires_at ? Math.max(0, order.expires_at - now) : 0;
	const fmtRemaining = (secs) => {
		const h = Math.floor(secs / 3600);
		const m = Math.floor((secs % 3600) / 60);
		const s = secs % 60;
		return h > 0 ? `${h}h ${m}m` : `${m}m ${s}s`;
	};

	onMount(async () => {
		await reload();
		tickTimer = setInterval(() => (now = Math.floor(Date.now() / 1000)), 1000);
		loaded = true;
	});

	onDestroy(() => {
		stopPolling();
		if (tickTimer) clearInterval(tickTimer);
	});
</script>

<svelte:head>
	<title>{$i18n.t('Subscription')}</title>
</svelte:head>

{#if loaded}
	<div
		class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
			? 'md:max-w-[calc(100%-var(--sidebar-width))]'
			: ''} max-w-full"
	>
		<!-- header -->
		<div class="flex items-center gap-2 px-4 py-2 border-b border-gray-50 dark:border-gray-850">
			{#if !$showSidebar}
				<Tooltip content={$i18n.t('Open Sidebar')}>
					<button
						class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850"
						on:click={() => showSidebar.set(true)}
					>
						<Sidebar />
					</button>
				</Tooltip>
			{/if}
			<div class="text-lg font-medium">{$i18n.t('Subscription')}</div>
		</div>

		<div class="flex-1 overflow-y-auto px-4 md:px-8 py-6">
			<div class="max-w-4xl mx-auto w-full">
				<!-- current plan + usage -->
				{#if me?.tier}
					<div class="mb-6 rounded-2xl border border-gray-100 dark:border-gray-800 p-4">
						<div class="flex items-center justify-between flex-wrap gap-2">
							<div>
								<div class="text-xs text-gray-500">{$i18n.t('Your plan')}</div>
								<div class="text-xl font-semibold">{me.tier.name}</div>
							</div>
							{#if me.expires_at}
								<div class="text-right">
									<div class="text-xs text-gray-500">{$i18n.t('Renews / expires')}</div>
									<div class="text-sm font-medium">
										{new Date(me.expires_at * 1000).toLocaleDateString()}
									</div>
								</div>
							{/if}
						</div>

						<div class="mt-3">
							{#if me.usage?.limit === null || me.usage?.limit === undefined}
								<div class="text-sm text-gray-600 dark:text-gray-300">
									{$i18n.t('Unlimited messages')}
								</div>
							{:else}
								<div class="flex items-center justify-between text-xs text-gray-500 mb-1">
									<span>{$i18n.t('Daily messages')}</span>
									<span>{me.usage.used} / {me.usage.limit}</span>
								</div>
								<div class="w-full h-2 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
									<div
										class="h-full bg-black dark:bg-white transition-all"
										style="width: {Math.min(100, (me.usage.used / Math.max(1, me.usage.limit)) * 100)}%"
									></div>
								</div>
							{/if}
						</div>
					</div>
				{/if}

				<!-- tiers -->
				<div class="text-sm font-medium text-gray-500 mb-3">{$i18n.t('Available plans')}</div>
				<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
					{#each tiers as tier (tier.id)}
						{@const isCurrent = me?.tier?.id === tier.id}
						<div
							class="flex flex-col rounded-2xl border p-4 {isCurrent
								? 'border-black dark:border-white'
								: 'border-gray-100 dark:border-gray-800'}"
						>
							<div class="text-lg font-semibold">{tier.name}</div>
							<div class="mt-1 text-2xl font-bold">{priceLabel(tier)}</div>
							{#if tier.price_usd > 0}
								<div class="text-xs text-gray-500">{$i18n.t('per {{days}} days', { days: tier.duration_days })}</div>
							{/if}
							{#if tier.description}
								<div class="mt-2 text-xs text-gray-500">{tier.description}</div>
							{/if}
							<div class="mt-3 text-sm text-gray-600 dark:text-gray-300">
								{limitLabel(tier.daily_message_limit)}
							</div>

							<div class="mt-auto pt-4">
								{#if isCurrent}
									<button
										class="w-full py-2 rounded-lg bg-gray-100 dark:bg-gray-800 text-sm font-medium cursor-default"
										disabled
									>
										{$i18n.t('Current plan')}
									</button>
								{:else if tier.price_usd > 0}
									<button
										class="w-full py-2 rounded-lg bg-black text-white dark:bg-white dark:text-black text-sm font-medium hover:opacity-90"
										on:click={() => openCheckout(tier)}
									>
										{$i18n.t('Subscribe')}
									</button>
								{:else}
									<div class="text-center text-xs text-gray-400 py-2">{$i18n.t('Default')}</div>
								{/if}
							</div>
						</div>
					{/each}
				</div>

				{#if tiers.length === 0}
					<div class="text-center text-sm text-gray-500 py-10">
						{$i18n.t('No subscription plans are available right now.')}
					</div>
				{/if}
			</div>
		</div>
	</div>

	<!-- checkout overlay -->
	{#if checkoutTier}
		<div
			class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
			on:click|self={closeCheckout}
		>
			<div class="w-full max-w-md rounded-2xl bg-white dark:bg-gray-900 p-5 max-h-[90dvh] overflow-y-auto">
				<div class="flex items-center justify-between mb-3">
					<div class="text-lg font-semibold">
						{$i18n.t('Subscribe to {{name}}', { name: checkoutTier.name })}
					</div>
					<button class="text-gray-400 hover:text-gray-700 dark:hover:text-white" on:click={closeCheckout}>✕</button>
				</div>

				{#if !order}
					<!-- chain selection -->
					<div class="text-sm text-gray-500 mb-1">{$i18n.t('Pay with USDT on')}</div>
					<select
						class="w-full mb-4 px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 border border-gray-100 dark:border-gray-800 text-sm outline-none"
						bind:value={selectedChainId}
					>
						{#each chains as c}
							<option value={c.id}>{c.name}</option>
						{/each}
					</select>

					<div class="flex items-center justify-between text-sm mb-4">
						<span class="text-gray-500">{$i18n.t('Amount')}</span>
						<span class="font-semibold">{checkoutTier.price_usd} USDT</span>
					</div>

					<button
						class="w-full py-2.5 rounded-lg bg-black text-white dark:bg-white dark:text-black text-sm font-medium hover:opacity-90 disabled:opacity-50"
						on:click={createOrder}
						disabled={creating || !selectedChainId}
					>
						{creating ? $i18n.t('Generating…') : $i18n.t('Generate payment address')}
					</button>
				{:else if paid}
					<div class="text-center py-6">
						<div class="text-3xl mb-2">✓</div>
						<div class="text-lg font-semibold mb-1">{$i18n.t('Payment received')}</div>
						<div class="text-sm text-gray-500 mb-4">{$i18n.t('Your {{name}} plan is now active.', { name: checkoutTier.name })}</div>
						<button
							class="px-4 py-2 rounded-lg bg-black text-white dark:bg-white dark:text-black text-sm font-medium"
							on:click={closeCheckout}
						>
							{$i18n.t('Done')}
						</button>
					</div>
				{:else}
					<!-- payment instructions -->
					<div class="text-center">
						{#if order.qr_code_image}
							<img src={order.qr_code_image} alt="QR" class="mx-auto w-44 h-44 rounded-lg bg-white p-1" />
						{/if}
						<div class="mt-3 text-xs text-gray-500">
							{$i18n.t('Send exactly')}
						</div>
						<div class="text-lg font-semibold">{order.amount} USDT</div>

						<button
							class="mt-3 w-full px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 border border-gray-100 dark:border-gray-800 text-xs font-mono break-all hover:bg-gray-100 dark:hover:bg-gray-800"
							on:click={copyAddress}
							title={$i18n.t('Click to copy')}
						>
							{order.address}
						</button>

						<div class="mt-3 flex items-center justify-center gap-2 text-sm">
							<span class="inline-block w-2 h-2 rounded-full {orderStatus === 'PAID' ? 'bg-green-500' : 'bg-yellow-500 animate-pulse'}"></span>
							<span class="text-gray-600 dark:text-gray-300">
								{orderStatus === 'PAID' ? $i18n.t('Confirmed') : $i18n.t('Waiting for payment…')}
							</span>
						</div>

						{#if remaining > 0}
							<div class="mt-1 text-xs text-gray-400">
								{$i18n.t('Expires in {{time}}', { time: fmtRemaining(remaining) })}
							</div>
						{:else}
							<div class="mt-1 text-xs text-red-500">{$i18n.t('This payment request has expired.')}</div>
						{/if}

						<div class="mt-2 text-[11px] text-gray-400">
							{$i18n.t('Only send USDT on the selected network. This page updates automatically.')}
						</div>
					</div>
				{/if}
			</div>
		</div>
	{/if}
{/if}
