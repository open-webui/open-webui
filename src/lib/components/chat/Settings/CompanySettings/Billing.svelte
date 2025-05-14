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
		getCurrentSubscription
	} from '$lib/apis/payments';
	import dayjs from 'dayjs';

	const i18n = getContext('i18n');
	let autoRecharge = false;
	let showUpdateDetails = false;
	let current = null;

	let plans = [];
	onMount(async () => {
		const res = await getSubscriptionPlans(localStorage.token).catch((error) => console.log(error));
		if (res) {
			plans = res;
			console.log(plans);
		}
		// const sub = await getCurrentSubscription(localStorage.token);
		// console.log(sub, 'current sub');
	});

	async function upgradeSubscription(plan_id) {
		const res = await createSubscriptionSession(localStorage.token, plan_id).catch((error) =>
			console.log(error)
		);
		if (res) {
			window.location.href = res.url;
		}
	}
	$: console.log($subscription);
	$: currentPlan = plans?.find((item) => item.id === $subscription?.plan);
	$: console.log(currentPlan, 'current plan');
</script>

<UpdatePaymentDetails
	bind:show={showUpdateDetails}
	on:confirm={() => {
		// submitHandler();
	}}
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
							5 seats,
						</div>
						<div class="text-xs dark:text-customGray-590 text-center">
							150€ included,
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
		{/if}
	</div>
</UpdatePaymentDetails>

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
				{#if $subscription?.plan === 'starter'}
					<div
						class="mb-2.5 flex justify-center items-center w-[50px] h-[50px] bg-[#024D15] rounded-mdx text-[#0F8C18]"
					>
						<StarterPlanIcon className="size-6" />
					</div>
				{:else if $subscription?.plan === 'team'}
					<div
						class="mb-2.5 flex justify-center items-center w-[50px] h-[50px] bg-[#4621A5] rounded-mdx text-[#A588EF]"
					>
						<BusinessPlanIcon className="size-6" />
					</div>
				{:else if $subscription?.plan === 'growth'}
					<div
						class="mb-2.5 flex justify-center items-center w-[50px] h-[50px] bg-[#840E70] rounded-mdx text-[#F294E2]"
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
							Monthly
						</div>
					</div>
					<div class="text-xs dark:text-customGray-100/50 mt-2">
						€{currentPlan?.price_monthly ? currentPlan?.price_monthly / 100 : '0.00'}/mo
					</div>
				</div>
			</div>
			<button
				on:click={() => (showUpdateDetails = true)}
				class="flex items-center justify-center rounded-mdx dark:hover:bg-customGray-950 border dark:border-customGray-700 px-4 py-3 text-xs dark:text-customGray-200"
			>
				{$i18n.t('Explore Plans')}
			</button>
		</div>
		<div class="flex items-center justify-between pt-2.5 pb-3">
			<div class="text-xs dark:text-customGray-100">{$i18n.t('Billing details')}</div>
			<div class="text-xs dark:text-customGray-590">
				Monthly (renews ({dayjs($subscription?.next_billing_date * 1000)?.format('DD.MM.YYYY')}))
			</div>
		</div>
	</div>

	<div class="rounded-2xl dark:bg-customGray-900 pt-4 px-4 pb-4 mb-2.5">
		<div class="flex items-center justify-between pb-3">
			<div class="text-xs dark:text-customGray-300 font-medium">{$i18n.t('Seats')}</div>
			<div class="text-xs dark:text-customGray-590">
				<span class="text-xs dark:text-customGray-100">18 {$i18n.t('used')}</span><span
					class="dark:text-customGray-590">/ 25 {$i18n.t('included')}</span
				>
			</div>
		</div>
		<div class="relative w-full h-1 rounded-sm bg-customGray-800">
			<div class="absolute left-0 h-1 rounded-sm bg-[#024D15] w-[300px]"></div>
		</div>
	</div>
	<div class="rounded-2xl dark:bg-customGray-900 pt-4 px-4 pb-4 mb-2.5">
		<div class="flex items-center justify-between pb-2.5 border-b dark:border-customGray-700">
			<div class="text-xs dark:text-customGray-300 font-medium">{$i18n.t('Base credits')}</div>
			<div class="text-xs dark:text-customGray-590">
				<span class="text-xs dark:text-customGray-100">0 {$i18n.t('used')}</span><span
					class="dark:text-customGray-590">/ 5000 {$i18n.t('included')}</span
				>
			</div>
		</div>
		<div class="flex items-center justify-between pt-2.5">
			<div class="text-xs dark:text-customGray-590">
				{$i18n.t('Credits will reset on')} March 25, 2025
			</div>
			<button
				class="flex items-center justify-center rounded-[10px] dark:hover:bg-customGray-950 border dark:border-customGray-700 px-4 py-2 text-xs dark:text-customGray-200"
			>
				{$i18n.t('View usage details')}
			</button>
		</div>
	</div>

	<div class="rounded-2xl dark:bg-customGray-900 pt-4 px-4 pb-4">
		<div class="flex items-center justify-between pb-2.5 border-b dark:border-customGray-700">
			<div class="text-xs dark:text-customGray-300 font-medium">{$i18n.t('Flex credits')}</div>
			<div class="text-xs dark:text-customGray-590">
				<span class="text-xs dark:text-customGray-100">0 {$i18n.t('used')}</span><span
					class="dark:text-customGray-590">/ 0 {$i18n.t('included')}</span
				>
			</div>
		</div>
		<div class="flex items-center justify-between pt-2.5">
			<div class="flex items-center">
				<div class="text-xs dark:text-customGray-590 mr-2.5">{$i18n.t('Auto recharge')}</div>
				<Switch bind:state={autoRecharge} on:change={async (e) => {}} />
				<div class="text-xs dark:text-customGray-590 ml-2.5">
					{#if autoRecharge}
						{$i18n.t('On')}
					{:else}
						{$i18n.t('Off')}
					{/if}
				</div>
			</div>
			<button
				class="flex items-center justify-center rounded-[10px] dark:hover:bg-customGray-950 border dark:border-customGray-700 px-4 py-2 text-xs dark:text-customGray-200"
			>
				{$i18n.t('Buy credits')}
			</button>
		</div>
	</div>

	<div
		class="flex w-full justify-between items-center py-2.5 border-b border-customGray-700 mb-2.5 mt-2.5"
	>
		<div class="flex w-full justify-between items-center">
			<div class="text-xs dark:text-customGray-300">{$i18n.t('Billing details')}</div>
		</div>
	</div>
	<button
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
		class="flex items-center justify-center rounded-[10px] dark:bg-customGray-900 dark:hover:bg-customGray-950 border dark:border-customGray-700 px-4 py-2 text-xs dark:text-customGray-200"
	>
		{$i18n.t('View billing statement')}
	</button>
</div>
