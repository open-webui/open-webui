<script lang="ts">
	import { getContext } from 'svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let billing: {
		type: 'free' | 'per_use' | 'per_token';
		currency: 'USD' | 'CNY';
		per_use_price?: number;
		per_use_multiplier?: number;
		input_price?: number;
		output_price?: number;
		price_unit?: 'K' | 'M';
		token_multiplier?: number;
	} = {
		type: 'free',
		currency: 'CNY',
		per_use_price: 0,
		per_use_multiplier: 1,
		input_price: 0,
		output_price: 0,
		price_unit: 'M',
		token_multiplier: 1
	};

	const billingTypes = [
		{ value: 'free', label: $i18n.t('Free') },
		{ value: 'per_use', label: $i18n.t('Per-Use') },
		{ value: 'per_token', label: $i18n.t('Per-Token') }
	];

	const currencies = [
		{ value: 'CNY', label: '¥ ' + $i18n.t('CNY') },
		{ value: 'USD', label: '$ ' + $i18n.t('USD') }
	];

	const priceUnits = [
		{ value: 'K', label: 'K (1,000)' },
		{ value: 'M', label: 'M (1,000,000)' }
	];
</script>

<div>
	<div class="flex w-full justify-between mb-1">
		<div class="self-center text-xs font-medium text-gray-500">{$i18n.t('Billing Settings')}</div>
	</div>

	<div class="flex flex-col gap-3 mt-2">
		<!-- Billing Type and Currency Row -->
		<div class="flex gap-4">
			<div class="flex-1">
				<div class="text-xs text-gray-500 mb-1">{$i18n.t('Billing Type')}</div>
				<select
					class="w-full text-sm bg-transparent dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5 outline-none"
					bind:value={billing.type}
				>
					{#each billingTypes as type}
						<option value={type.value}>{type.label}</option>
					{/each}
				</select>
			</div>

			{#if billing.type !== 'free'}
				<div class="flex-1">
					<div class="text-xs text-gray-500 mb-1">{$i18n.t('Currency')}</div>
					<select
						class="w-full text-sm bg-transparent dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5 outline-none"
						bind:value={billing.currency}
					>
						{#each currencies as currency}
							<option value={currency.value}>{currency.label}</option>
						{/each}
					</select>
				</div>
			{/if}
		</div>

		<!-- Per-Use Billing Fields -->
		{#if billing.type === 'per_use'}
			<div class="flex gap-4">
				<div class="flex-1">
					<div class="text-xs text-gray-500 mb-1">
						<Tooltip content={$i18n.t('Price per request')}>
							{$i18n.t('Price')}
						</Tooltip>
					</div>
					<div class="flex items-center gap-1">
						<span class="text-sm text-gray-500">{billing.currency === 'CNY' ? '¥' : '$'}</span>
						<input
							type="number"
							step="0.0001"
							min="0"
							class="w-full text-sm bg-transparent dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5 outline-none"
							bind:value={billing.per_use_price}
							placeholder="0.00"
						/>
					</div>
				</div>

				<div class="flex-1">
					<div class="text-xs text-gray-500 mb-1">
						<Tooltip content={$i18n.t('Multiplier applied to the price for this user group')}>
							{$i18n.t('Multiplier')}
						</Tooltip>
					</div>
					<input
						type="number"
						step="0.01"
						min="0"
						class="w-full text-sm bg-transparent dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5 outline-none"
						bind:value={billing.per_use_multiplier}
						placeholder="1.0"
					/>
				</div>
			</div>
		{/if}

		<!-- Per-Token Billing Fields -->
		{#if billing.type === 'per_token'}
			<div class="flex gap-4">
				<div class="flex-1">
					<div class="text-xs text-gray-500 mb-1">
						<Tooltip content={$i18n.t('Price per input token')}>
							{$i18n.t('Input Price')}
						</Tooltip>
					</div>
					<div class="flex items-center gap-1">
						<span class="text-sm text-gray-500">{billing.currency === 'CNY' ? '¥' : '$'}</span>
						<input
							type="number"
							step="0.0001"
							min="0"
							class="w-full text-sm bg-transparent dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5 outline-none"
							bind:value={billing.input_price}
							placeholder="0.00"
						/>
					</div>
				</div>

				<div class="flex-1">
					<div class="text-xs text-gray-500 mb-1">
						<Tooltip content={$i18n.t('Price per output token')}>
							{$i18n.t('Output Price')}
						</Tooltip>
					</div>
					<div class="flex items-center gap-1">
						<span class="text-sm text-gray-500">{billing.currency === 'CNY' ? '¥' : '$'}</span>
						<input
							type="number"
							step="0.0001"
							min="0"
							class="w-full text-sm bg-transparent dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5 outline-none"
							bind:value={billing.output_price}
							placeholder="0.00"
						/>
					</div>
				</div>
			</div>

			<div class="flex gap-4">
				<div class="flex-1">
					<div class="text-xs text-gray-500 mb-1">
						<Tooltip content={$i18n.t('Price is per K (1,000) or M (1,000,000) tokens')}>
							{$i18n.t('Price Unit')}
						</Tooltip>
					</div>
					<select
						class="w-full text-sm bg-transparent dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5 outline-none"
						bind:value={billing.price_unit}
					>
						{#each priceUnits as unit}
							<option value={unit.value}>{unit.label}</option>
						{/each}
					</select>
				</div>

				<div class="flex-1">
					<div class="text-xs text-gray-500 mb-1">
						<Tooltip content={$i18n.t('Multiplier applied to the price for this user group')}>
							{$i18n.t('Multiplier')}
						</Tooltip>
					</div>
					<input
						type="number"
						step="0.01"
						min="0"
						class="w-full text-sm bg-transparent dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5 outline-none"
						bind:value={billing.token_multiplier}
						placeholder="1.0"
					/>
				</div>
			</div>
		{/if}
	</div>
</div>
