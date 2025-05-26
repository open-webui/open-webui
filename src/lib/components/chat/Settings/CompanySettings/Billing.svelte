<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import StarterPlanIcon from '$lib/components/icons/StarterPlanIcon.svelte';
	import BusinessPlanIcon from '$lib/components/icons/BusinessPlanIcon.svelte';
	import GrowthPlanIcon from '$lib/components/icons/GrowthPlanIcon.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import UpdatePaymentDetails from './UpdatePaymentDetails.svelte';
	import { user, subscription } from '$lib/stores';
	import {
		getSubscriptionPlans,
		createSubscriptionSession,
		rechargeFlexCredits,
		updateAutoRecharge,
		getCurrentSubscription,
		deleteCurrentSubscription,
		redirectToCustomerPortal
	} from '$lib/apis/payments';
	import dayjs from 'dayjs';
	import { toast } from 'svelte-sonner';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { goto } from '$app/navigation';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	const i18n = getContext('i18n');
	export let autoRecharge = false;
	export let subscriptionLoading = false;
	let showUpdateDetails = false;
	let showBuyFlexCredits = false;

	$: console.log(showUpdateDetails)
	let mounted = false;
	export let plans = [];
	onMount(() => {
		mounted = true;
		const url = new URL(window.location.href);
		const plansParam = url.searchParams.get('plans');
		if(plansParam === 'open'){
			showUpdateDetails = true;
		}
		const rechargeParam = url.searchParams.get('recharge');
		if(rechargeParam === 'open'){
			showBuyFlexCredits = true;
		}
	})

	async function upgradeSubscription(plan_id) {
		const res = await createSubscriptionSession(localStorage.token, plan_id).catch((error) =>
			console.log(error)
		);
		if (res) {
			window.location.href = res.url;
		}
	}

	async function goToCustomerPortal() {
		const res = await redirectToCustomerPortal(localStorage.token).catch((error) => {
			console.log(error)
		});
		if (res) {
			window.location.href = res.url;
		}
	}

	async function fetchCurrentSubscription() {
		const sub = await getCurrentSubscription(localStorage.token)
		.catch(error => {
			console.log(error)
			
		});
		subscription.set(sub);	
	}
	async function pollForCreditChange(previous, interval = 2000, timeout = 20000) {
		const start = Date.now();

		return new Promise((resolve, reject) => {
			const check = async () => {
				try {
					const res = await getCurrentSubscription(localStorage.token);

					if (res.flex_credits_remaining !== previous) {
						subscription.set(res);
						resolve();
					} else if (Date.now() - start >= timeout) {
						reject(new Error('Timeout: Credit not updated'));
					} else {
						setTimeout(check, interval);
					}
				} catch (err) {
					reject(err);
				}
			};

			check();
		});
	}

	async function recharge () {
		const res = await rechargeFlexCredits(localStorage.token).catch((error) =>
			console.log(error)
		);
		if(res.payment_intent) {
			toast.success($i18n.t(res.message))
		}
		await pollForCreditChange($subscription?.flex_credits_remaining, 2000, 20000);
		
	}
	$: console.log($subscription);
	$: currentPlan = plans?.find((item) => item.id === $subscription?.plan);
	$: console.log(currentPlan, 'current plan');

	$: seatsWidth = $subscription?.seats ? $subscription?.seats_taken > $subscription?.seats ? '100%' : `${($subscription?.seats_taken/$subscription?.seats*100)}%` : '100%';
	$: creditsWidth = $subscription?.credits_remaining ? `${(((currentPlan?.credits_per_month - $subscription?.credits_remaining)/currentPlan?.credits_per_month) * 100)}%` : '100%';
	

	$: {
		if(showBuyFlexCredits === false && mounted){
			const url = new URL(window.location.href);
			url.searchParams.delete('recharge'); 
			window.history.replaceState({}, '', `${url.pathname}${url.search}`);
		}
	}
</script>


<ConfirmDialog
	bind:show={showBuyFlexCredits}
	title={$i18n.t('Buy credits?')}
	on:confirm={recharge}
	on:cancel={() => {
		const url = new URL(window.location.href);
		url.searchParams.delete('recharge'); 
		window.history.replaceState({}, '', `${url.pathname}${url.search}`);
	}}
>
	<div class=" text-sm text-gray-500 flex-1 line-clamp-3">
		{$i18n.t('You will be charged for')} <span class="  font-semibold">€{(20).toFixed(2)}</span>.
	</div>
</ConfirmDialog>

<UpdatePaymentDetails
	bind:show={showUpdateDetails}
>
	<div>
		{#if plans?.length > 0}
			<div class="grid grid-cols-3 gap-2">
				{#each plans as plan}
					<div class="dark:bg-customGray-900 rounded-lg p-5 flex flex-col items-center">
						{#if plan.id === 'starter'}
							<div
								class="mb-2.5 flex justify-center items-center w-[50px] h-[50px] bg-[#024D15] rounded-mdx text-[#0F8C18]"
							>
								<StarterPlanIcon className="size-6" />
							</div>
						{:else if plan.id === 'team'}
							<div
								class="mb-2.5 flex justify-center items-center w-[50px] h-[50px] bg-[#4621A5] rounded-mdx text-[#A588EF]"
							>
								<BusinessPlanIcon className="size-6" />
							</div>
						{:else if plan.id === 'growth'}
							<div
								class="mb-2.5 flex justify-center items-center w-[50px] h-[50px] bg-[#840E70] rounded-mdx text-[#F294E2]"
							>
								<GrowthPlanIcon className="size-6" />
							</div>
						{/if}
						<div class="text-base dark:text-customGray-100 mb-5">
							{plan?.name}
							{$i18n.t('Plan')}
						</div>
						<div class="dark:text-customGray-100 mb-5 text-2xl">
							€{plan?.price_monthly / 100}/<span class="text-xs dark:text-customGray-100/50"
								>month</span
							>
						</div>
						<div class="text-xs dark:text-customGray-590 text-center">
							{plan?.seats} {$i18n.t('seats')},
						</div>
						<div class="text-xs dark:text-customGray-590 text-center">
							€{plan?.credits_per_month} {$i18n.t('included')},
						</div>
						<div class="text-xs dark:text-customGray-590 text-center mb-5">
							all features
						</div>
						<button
							on:click={() => upgradeSubscription(plan.id)}
							type="button"
							disabled={plan?.id === $subscription?.plan}
							class="w-full mt-auto flex h-10 items-center justify-center rounded-[10px] dark:bg-customGray-900 {plan?.id !== $subscription?.plan ? 'dark:hover:bg-customGray-950' : ''} border dark:border-customGray-700 px-4 py-2 text-xs dark:text-customGray-200"
						>
							{#if plan?.id === $subscription?.plan}
								{$i18n.t('Current Plan')}
							{:else}
								{$i18n.t('Select')}
							{/if}
						</button>
					</div>
				{/each}
			</div>
		{:else}
			<Spinner/>
		{/if}
	</div>
</UpdatePaymentDetails>

{#if !subscriptionLoading}
	<div class="pb-20">
		<div
			class="flex w-full justify-between items-center py-2.5 border-b border-customGray-700 mb-2.5"
		>
			<div class="flex w-full justify-between items-center">
				<div class="text-xs dark:text-customGray-300">{$i18n.t('Current plan')}</div>
			</div>
		</div>
		<div class="rounded-2xl dark:bg-customGray-900 pt-4 px-4 mb-2.5">
			<div class="flex items-center justify-between pb-2.5 border-b dark:border-customGray-700">
				<div class="flex items-center gap-2.5">
					{#if $subscription?.plan === 'starter' || $subscription?.plan === 'free'}
						<div
							class="flex justify-center items-center w-[50px] h-[50px] bg-[#024D15] rounded-mdx text-[#0F8C18]"
						>
							<StarterPlanIcon className="size-6" />
						</div>
					{:else if $subscription?.plan === 'team'}
						<div
							class="flex justify-center items-center w-[50px] h-[50px] bg-[#4621A5] rounded-mdx text-[#A588EF]"
						>
							<BusinessPlanIcon className="size-6" />
						</div>
					{:else if $subscription?.plan === 'growth'}
						<div
							class="flex justify-center items-center w-[50px] h-[50px] bg-[#840E70] rounded-mdx text-[#F294E2]"
						>
							<GrowthPlanIcon className="size-6" />
						</div>
					{/if}
					<div>
						<div class="flex items-center gap-2.5">
							<div class="text-sm dark:text-customGray-100 capitalize">
								{$i18n.t($subscription?.plan)}
							</div>
							<div
								class="flex justify-center items-center text-xs dark:text-customGray-590 dark:bg-customGray-800 px-2 py-1 rounded-mdx"
							>
								{$i18n.t('Monthly')}
							</div>
						</div>
						<div class="text-xs dark:text-customGray-100/50">
							€{currentPlan?.price_monthly ? (currentPlan?.price_monthly / 100).toFixed(2) : '0.00'}/mo
						</div>
					</div>
				</div>
				<button
					on:click={() => {
						showUpdateDetails = true
						const url = new URL(window.location.href);
						url.searchParams.set('plans', 'open'); 
						window.history.replaceState({}, '', `${url.pathname}${url.search}`);
					}}
					class="flex items-center justify-center rounded-mdx dark:hover:bg-customGray-950 border dark:border-customGray-700 px-4 py-3 text-xs dark:text-customGray-200"
				>
					{$i18n.t('Explore Plans')}
				</button>
			</div>
			<div class="flex items-center justify-between pt-2.5 pb-3">
				<div class="text-xs dark:text-customGray-100">{$i18n.t('Billing details')}</div>
				{#if $subscription?.cancel_at_period_end}
					<div class="text-xs dark:text-customGray-590">
						Canceled at {dayjs($subscription?.canceled_at * 1000)?.format('DD.MM.YYYY')}
					</div>
				{:else if $subscription?.plan !== 'free'}
					<div class="text-xs dark:text-customGray-590">
						Monthly (renews ({dayjs($subscription?.next_billing_date * 1000)?.format('DD.MM.YYYY')}))
					</div>
				{:else if $subscription?.plan === 'free'}
					<div class="text-xs dark:text-customGray-590">
						Trial ends {dayjs($subscription?.trial_end * 1000)?.format('DD.MM.YYYY')}
					</div>
				{/if}
			</div>
		</div>

		<div class="rounded-2xl dark:bg-customGray-900 pt-4 px-4 pb-4 mb-2.5">
			<div class="flex items-center justify-between pb-3">
				<div class="text-xs dark:text-customGray-300 font-medium">{$i18n.t('Seats')}</div>
				<div class="text-xs dark:text-customGray-590">
					{#if $subscription?.plan !== "free"}
					<span class="text-xs dark:text-customGray-100">{$subscription?.seats_taken} {$i18n.t('used')}</span><span
						class="dark:text-customGray-590">/ {$subscription?.seats} {$i18n.t('included')}</span
					>
					{:else}
					<span class="text-xs dark:text-customGray-100">1 {$i18n.t('used')}</span><span
						class="dark:text-customGray-590">/ 1 {$i18n.t('included')}</span
					>
					{/if}
				</div>
			</div>
			<div class="relative w-full h-1 rounded-sm bg-customGray-800">
				<div style={`width: ${seatsWidth};`} class="absolute left-0 h-1 rounded-sm bg-[#024D15]"></div>
			</div>
		</div>
		<div class="rounded-2xl dark:bg-customGray-900 pt-4 px-4 pb-4 mb-2.5">
			<div class="flex items-center justify-between pb-2.5 border-b dark:border-customGray-700 mb-5">
				<div class="text-xs dark:text-customGray-300 font-medium">{$i18n.t('Base credits')}</div>
				<div class="text-xs dark:text-customGray-590">
					{#if $subscription?.plan !== 'free'}
					<span class="text-xs dark:text-customGray-100">€{(currentPlan?.credits_per_month - $subscription?.credits_remaining)?.toFixed(2)} {$i18n.t('used')}</span><span
						class="dark:text-customGray-590">/ €{(currentPlan?.credits_per_month).toFixed(2)} {$i18n.t('included')}</span
					>
					{:else}
					<span class="text-xs dark:text-customGray-100">€{(5 - $subscription?.credits_remaining)?.toFixed(2)} {$i18n.t('used')}</span><span
						class="dark:text-customGray-590">/ €{(5).toFixed(2)} {$i18n.t('included')}</span
					>
					{/if}
				</div>
			</div>
			<div class="relative w-full h-1 rounded-sm bg-customGray-800 mb-2.5">
				<div style={`width: ${creditsWidth};`} class="absolute left-0 h-1 rounded-sm bg-[#024D15]"></div>
			</div>
			<div class="flex items-center justify-between pt-2.5">
				{#if $subscription?.plan !== 'free' && $subscription?.cancel_at_period_end !== true}
					<div class="text-xs dark:text-customGray-590">
						{$i18n.t('Credits will reset on')} {dayjs($subscription?.next_billing_date * 1000)?.format('DD.MM.YYYY')}
					</div>
				{:else}
					<div></div>
				{/if}
				<button
					on:click={() => {
						const url = new URL(window.location.href);
						url.searchParams.set('modal', 'company-settings');
						url.searchParams.set('tab', 'analytics');
						goto(`${url.pathname}${url.search}`, { replaceState: false });
					}}
					class="flex items-center justify-center rounded-[10px] dark:hover:bg-customGray-950 border dark:border-customGray-700 px-4 py-2 text-xs dark:text-customGray-200"
				>
					{$i18n.t('View usage details')}
				</button>
			</div>
		</div>

		{#if $subscription?.plan !== "free"}
			<div class="rounded-2xl dark:bg-customGray-900 pt-4 px-4 pb-4">
				<div class="flex items-center justify-between pb-2.5 border-b dark:border-customGray-700">
					<div class="text-xs dark:text-customGray-300 font-medium">{$i18n.t('Flex credits')}</div>
					<div class="text-xs dark:text-customGray-590">
						<!-- <span class="text-xs dark:text-customGray-100">0 {$i18n.t('used')}</span> -->
						<span
							class="dark:text-customGray-100">€{($subscription?.flex_credits_remaining ? $subscription?.flex_credits_remaining : 0).toFixed(2)} {$i18n.t('remaining')}</span
						>
					</div>
				</div>
				<div class="flex items-center justify-between pt-2.5">
					<div class="flex items-center">
						<div class="text-xs dark:text-customGray-590 mr-2.5">{$i18n.t('Auto recharge')}</div>
						<Switch bind:state={autoRecharge} on:change={async (e) => {
							const res = await updateAutoRecharge(localStorage.token, e.detail).catch(error => console.log(error))
							toast.success($i18n.t(res.message))
							fetchCurrentSubscription()
						}} />
						<div class="text-xs dark:text-customGray-590 ml-2.5">
							{#if autoRecharge}
								{$i18n.t('On')}
							{:else}
								{$i18n.t('Off')}
							{/if}
						</div>
					</div>
					<button
						on:click={() => {
							showBuyFlexCredits = true;
							const url = new URL(window.location.href);
							url.searchParams.set('recharge', 'open'); 
							window.history.replaceState({}, '', `${url.pathname}${url.search}`);
						}}
						class="flex items-center justify-center rounded-[10px] dark:hover:bg-customGray-950 border dark:border-customGray-700 px-8 py-2 text-xs dark:text-customGray-200"
					>
						{$i18n.t('Buy credits')}
					</button>
				</div>
			</div>
		{/if}

		{#if $subscription?.plan !== "free"}
			<div
				class="flex w-full justify-between items-center py-2.5 border-b border-customGray-700 mb-2.5 mt-2.5"
			>
				<div class="flex w-full justify-between items-center">
					<div class="text-xs dark:text-customGray-300">{$i18n.t('Billing details')}</div>
				</div>
			</div>
			<button
				on:click={goToCustomerPortal}
				class="flex items-center justify-center rounded-[10px] dark:bg-customGray-900 dark:hover:bg-customGray-950 border dark:border-customGray-700 px-4 py-2 text-xs dark:text-customGray-200"
			>
				{$i18n.t('Update billing details')}
			</button>
			<div
				class="flex w-full justify-between items-center py-2.5 border-b border-customGray-700 mb-2.5 mt-2.5"
			>
				<div class="flex w-full justify-between items-center">
					<div class="text-xs dark:text-customGray-300">{$i18n.t('History')}</div>
				</div>
			</div>
			<button
				on:click={goToCustomerPortal}
				class="flex items-center justify-center rounded-[10px] dark:bg-customGray-900 dark:hover:bg-customGray-950 border dark:border-customGray-700 px-4 py-2 text-xs dark:text-customGray-200"
			>
				{$i18n.t('View billing statement')}
			</button>
		{/if}
		<!-- {#if $subscription?.plan !== "free"}
			<div
				class="flex w-full justify-between items-center py-2.5 border-b border-customGray-700 mb-2.5 mt-2.5"
			>
				<div class="flex w-full justify-between items-center">
					<div class="text-xs dark:text-customGray-300">{$i18n.t('Cancel Subscription')}</div>
				</div>
			</div>
			<button
				on:click={async () => {
					await deleteCurrentSubscription(localStorage.token)
					.then(res => toast.success($i18n.t(res?.message)))
					.catch(error => toast.error(error));
					fetchCurrentSubscription();	
				}}
				class="flex items-center justify-center rounded-[10px] dark:bg-customGray-900 dark:hover:bg-customGray-950 border dark:border-customGray-700 px-4 py-2 text-xs dark:text-customGray-200"
			>
				{$i18n.t('Cancel Subscription')}
			</button>
		{/if} -->
	</div>
{:else}
	<div class="h-[20rem] w-full flex justify-center items-center">
		<Spinner />
	</div>
{/if}
