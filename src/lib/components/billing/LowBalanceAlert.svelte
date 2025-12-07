<script lang="ts">
	import { isLowBalance, isFrozen, balance, formatCurrency } from '$lib/stores';
	import { getContext } from 'svelte';
	import { slide } from 'svelte/transition';

	const i18n = getContext('i18n');

	let dismissed = false;

	const dismiss = () => {
		dismissed = true;
	};
</script>

{#if ($isLowBalance || $isFrozen) && !dismissed}
	<div class="alert" class:frozen={$isFrozen} transition:slide>
		<div class="alert-icon">
			{#if $isFrozen}
				⛔
			{:else}
				⚠️
			{/if}
		</div>
		<div class="alert-content">
			<div class="alert-title">
				{#if $isFrozen}
					{$i18n.t('账户已冻结')}
				{:else}
					{$i18n.t('余额不足')}
				{/if}
			</div>
			<div class="alert-message">
				{#if $isFrozen}
					{$i18n.t('您的账户余额不足，已被冻结。请联系管理员充值。')}
				{:else}
					{$i18n.t('当前余额')}: {formatCurrency($balance?.balance || 0)}，{$i18n.t(
						'请及时充值以免影响使用。'
					)}
				{/if}
			</div>
		</div>
		<button class="alert-close" on:click={dismiss}>×</button>
	</div>
{/if}

<style>
	.alert {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 1rem;
		background: #fef3c7;
		border: 1px solid #fbbf24;
		border-radius: 0.5rem;
		margin-bottom: 1rem;
	}

	.alert.frozen {
		background: #fee2e2;
		border-color: #ef4444;
	}

	.alert-icon {
		font-size: 1.5rem;
		flex-shrink: 0;
	}

	.alert-content {
		flex: 1;
	}

	.alert-title {
		font-weight: 600;
		margin-bottom: 0.25rem;
		color: #78350f;
	}

	.alert.frozen .alert-title {
		color: #7f1d1d;
	}

	.alert-message {
		font-size: 0.875rem;
		color: #78350f;
	}

	.alert.frozen .alert-message {
		color: #7f1d1d;
	}

	.alert-close {
		font-size: 1.5rem;
		color: #6b7280;
		cursor: pointer;
		background: none;
		border: none;
		padding: 0;
		width: 1.5rem;
		height: 1.5rem;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}

	.alert-close:hover {
		color: #111827;
	}
</style>
