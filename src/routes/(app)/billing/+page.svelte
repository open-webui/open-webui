<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { balance, showSidebar } from '$lib/stores';
	import { getBalance } from '$lib/apis/billing';
	import BalanceDisplay from '$lib/components/billing/BalanceDisplay.svelte';
	import BillingLogsTable from '$lib/components/billing/BillingLogsTable.svelte';
	import BillingStatsChart from '$lib/components/billing/BillingStatsChart.svelte';
	import LowBalanceAlert from '$lib/components/billing/LowBalanceAlert.svelte';
	import RechargeCard from '$lib/components/billing/RechargeCard.svelte';
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
		<div class="billing-page max-w-7xl mx-auto px-4 py-6 pb-16">
			<!-- 页面标题 -->
			<div class="page-header mb-6">
				<h1 class="text-2xl font-bold text-gray-900 dark:text-white">{$i18n.t('计费中心')}</h1>
				<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
					{$i18n.t('查看您的余额、消费记录和统计信息')}
				</p>
			</div>

			<!-- 余额不足警告 -->
			<LowBalanceAlert />

			<!-- 两栏布局：左侧自适应，右侧固定宽度 -->
			<div class="flex flex-col lg:flex-row gap-6 mt-6">
				<!-- 左侧主内容区（自适应宽度） -->
				<div class="flex-1 min-w-0 space-y-6 order-2 lg:order-1">
					<!-- 余额卡片 -->
					<BalanceDisplay />

					<!-- 统计图表 -->
					<BillingStatsChart />

					<!-- 消费记录 -->
					<BillingLogsTable />
				</div>

				<!-- 右侧充值卡片（固定宽度，移动端显示在上方） -->
				<div class="lg:w-[360px] lg:flex-shrink-0 order-1 lg:order-2">
					<div class="lg:sticky lg:top-6">
						<RechargeCard />
					</div>
				</div>
			</div>
		</div>
	</div>
</div>
