<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { balance, showSidebar } from '$lib/stores';
	import { getBalance } from '$lib/apis/billing';
	import BalanceDisplay from '$lib/components/billing/BalanceDisplay.svelte';
	import BillingLogsTable from '$lib/components/billing/BillingLogsTable.svelte';
	import BillingStatsChart from '$lib/components/billing/BillingStatsChart.svelte';
	import LowBalanceAlert from '$lib/components/billing/LowBalanceAlert.svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	onMount(async () => {
		try {
			const balanceInfo = await getBalance(localStorage.token);
			balance.set(balanceInfo);
		} catch (error) {
			toast.error($i18n.t('加载余额失败: ') + error.message);
		}
	});
</script>

<svelte:head>
	<title>{$i18n.t('计费中心')} | Cakumi</title>
</svelte:head>

<div
	class="flex flex-col h-screen max-h-[100dvh] flex-1 transition-width duration-200 ease-in-out w-full max-w-full {$showSidebar
		? 'md:max-w-[calc(100%-260px)]'
		: 'md:max-w-[calc(100%-49px)]'}"
>
	<div class="flex-1 overflow-y-auto min-w-[320px]">
		<div class="billing-page max-w-4xl mx-auto px-4 py-6 space-y-6 pb-16">
			<!-- 页面标题 -->
			<div class="page-header">
				<h1 class="text-2xl font-bold text-gray-900 dark:text-white">{$i18n.t('计费中心')}</h1>
				<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
					{$i18n.t('查看您的余额、消费记录和统计信息')}
				</p>
			</div>

			<!-- 余额不足警告 -->
			<LowBalanceAlert />

			<!-- 余额卡片 -->
			<div class="balance-section">
				<BalanceDisplay />
			</div>

			<!-- 统计图表 -->
			<div class="stats-section">
				<BillingStatsChart />
			</div>

			<!-- 消费记录 -->
			<div class="logs-section">
				<BillingLogsTable />
			</div>
		</div>
	</div>
</div>
