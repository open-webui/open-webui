<script lang="ts">
	import { formatCurrency } from '$lib/stores';
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let promptTokens: number = 0;
	export let completionTokens: number = 0;
	export let cost: number = 0;
	export let compact = false;
</script>

<div class="token-cost-badge" class:compact>
	{#if !compact}
		<div class="token-info">
			<span class="token-label">{$i18n.t('输入')}:</span>
			<span class="token-value">{promptTokens.toLocaleString()}</span>
		</div>
		<div class="token-info">
			<span class="token-label">{$i18n.t('输出')}:</span>
			<span class="token-value">{completionTokens.toLocaleString()}</span>
		</div>
	{/if}
	<div class="cost-info">
		<span class="cost-label">{$i18n.t('费用')}:</span>
		<span class="cost-value">{formatCurrency(cost, true)}</span>
	</div>
</div>

<style>
	.token-cost-badge {
		display: inline-flex;
		gap: 0.75rem;
		padding: 0.5rem 0.75rem;
		background: #f3f4f6;
		border-radius: 0.375rem;
		font-size: 0.875rem;
	}

	:global(.dark) .token-cost-badge {
		background: #374151;
	}

	.token-cost-badge.compact {
		padding: 0.25rem 0.5rem;
		font-size: 0.75rem;
	}

	.token-info,
	.cost-info {
		display: flex;
		gap: 0.25rem;
	}

	.token-label,
	.cost-label {
		color: #6b7280;
	}

	:global(.dark) .token-label,
	:global(.dark) .cost-label {
		color: #9ca3af;
	}

	.token-value,
	.cost-value {
		font-weight: 600;
		color: #111827;
	}

	:global(.dark) .token-value,
	:global(.dark) .cost-value {
		color: #f9fafb;
	}

	.cost-value {
		color: #dc2626;
	}

	:global(.dark) .cost-value {
		color: #ef4444;
	}
</style>
