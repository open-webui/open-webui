<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import BillingPlanIcon from '$lib/components/icons/BillingPlanIcon.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
    import UpdatePaymentDetails from './UpdatePaymentDetails.svelte';

	const i18n = getContext('i18n');
	let autoRecharge = false;
    let showUpdateDetails = false;
</script>


<UpdatePaymentDetails
	bind:show={showUpdateDetails}
	on:confirm={() => {
		// submitHandler();
	}}
>
<div>payment info</div>
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
				<div
					class="flex justify-center items-center w-[50px] h-[50px] bg-[#024D15] rounded-mdx text-[#0F8C18]"
				>
					<BillingPlanIcon className="size-6" />
				</div>
				<div>
					<div class="flex items-center gap-2.5">
						<div class="text-sm dark:text-customGray-100">{$i18n.t('Free')}</div>
						<div
							class="flex justify-center items-center text-xs dark:text-customGray-590 dark:bg-customGray-800 px-2 py-1 rounded-mdx"
						>
							Monthly
						</div>
					</div>
					<div class="text-xs dark:text-customGray-100/50 mt-2">€0.00/mo</div>
				</div>
			</div>
			<button
				class="flex items-center justify-center rounded-mdx dark:hover:bg-customGray-950 border dark:border-customGray-700 px-4 py-3 text-xs dark:text-customGray-200"
			>
				{$i18n.t('Explore plan')}
			</button>
		</div>
		<div class="flex items-center justify-between pt-2.5 pb-3">
			<div class="text-xs dark:text-customGray-100">{$i18n.t('Billing details')}</div>
			<div class="text-xs dark:text-customGray-590">Monthly (renews (March 25th, 2025))</div>
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
        on:click={() => showUpdateDetails = true}
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
