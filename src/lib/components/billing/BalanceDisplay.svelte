<script lang="ts">
	import { balance, isLowBalance, isFrozen, formatCurrency } from '$lib/stores';
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let compact = false; // 紧凑模式（用于侧边栏）
</script>

{#if $balance}
	<div class="balance-display" class:compact>
		<div class="balance-info">
			<div class="balance-label text-xs opacity-80">{$i18n.t('当前余额')}</div>
			<div
				class="balance-amount font-bold mt-1"
				class:low={$isLowBalance}
				class:frozen={$isFrozen}
			>
				{formatCurrency($balance.balance)}
			</div>
		</div>

		{#if !compact}
			<div class="consumed-info mt-3 pt-3 border-t border-white/20">
				<div class="consumed-label text-xs opacity-80">{$i18n.t('累计消费')}</div>
				<div class="consumed-amount text-sm font-semibold mt-1">
					{formatCurrency($balance.total_consumed)}
				</div>
			</div>
		{/if}

		{#if $isFrozen}
			<div class="status-badge frozen mt-2">
				{$i18n.t('账户已冻结')}
			</div>
		{:else if $isLowBalance}
			<div class="status-badge warning mt-2">
				{$i18n.t('余额不足')}
			</div>
		{/if}
	</div>
{/if}

<style>
	.balance-display {
		padding: 0.75rem;
		border-radius: 0.5rem;
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
	}

	.balance-display.compact {
		padding: 0.5rem 0.75rem;
		font-size: 0.875rem;
	}

	.balance-amount {
		font-size: 1.5rem;
	}

	.balance-display.compact .balance-amount {
		font-size: 1.125rem;
	}

	.balance-amount.low {
		color: #fbbf24;
	}

	.balance-amount.frozen {
		color: #ef4444;
	}

	.status-badge {
		padding: 0.25rem 0.5rem;
		border-radius: 0.25rem;
		font-size: 0.75rem;
		font-weight: 600;
		text-align: center;
	}

	.status-badge.warning {
		background: #fbbf24;
		color: #78350f;
	}

	.status-badge.frozen {
		background: #ef4444;
		color: white;
	}
</style>
