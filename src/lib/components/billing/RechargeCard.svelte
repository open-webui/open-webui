<script lang="ts">
	import { onMount, onDestroy, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { balance } from '$lib/stores';
	import { createPaymentOrder, getPaymentStatus, getPaymentConfig, getBalance } from '$lib/apis/billing';
	import QRCode from 'qrcode';

	const i18n = getContext('i18n');

	// 预设金额选项
	const amountOptions = [10, 50, 100, 200, 500, 1000];

	let selectedAmount: number | null = null;
	let customAmount = '';
	let loading = false;
	let alipayEnabled = false;
	let orderInfo: { order_id: string; qr_code: string; expired_at: number; amount: number } | null = null;
	let qrCodeDataUrl = '';
	let pollTimer: ReturnType<typeof setInterval> | null = null;
	let countdown = 0;
	let countdownTimer: ReturnType<typeof setInterval> | null = null;

	// 计算最终金额
	$: finalAmount = selectedAmount || (customAmount ? parseFloat(customAmount) : 0);
	$: isValidAmount = finalAmount >= 1 && finalAmount <= 10000;

	// 检查支付配置
	onMount(async () => {
		try {
			const config = await getPaymentConfig();
			alipayEnabled = config.alipay_enabled;
		} catch (e) {
			console.error('获取支付配置失败', e);
		}
	});

	// 创建订单
	const createOrder = async () => {
		if (!isValidAmount) return;

		loading = true;
		try {
			const result = await createPaymentOrder(localStorage.token, finalAmount);
			orderInfo = {
				order_id: result.order_id,
				qr_code: result.qr_code,
				expired_at: result.expired_at,
				amount: result.amount
			};

			// 生成二维码图片
			qrCodeDataUrl = await QRCode.toDataURL(result.qr_code, { width: 200, margin: 2 });

			// 计算倒计时
			countdown = result.expired_at - Math.floor(Date.now() / 1000);

			// 开始轮询订单状态
			startPolling();
			// 开始倒计时
			startCountdown();
		} catch (error: any) {
			toast.error(error.detail || $i18n.t('创建订单失败'));
		} finally {
			loading = false;
		}
	};

	// 开始倒计时
	const startCountdown = () => {
		if (countdownTimer) clearInterval(countdownTimer);

		countdownTimer = setInterval(() => {
			if (!orderInfo) return;

			countdown = orderInfo.expired_at - Math.floor(Date.now() / 1000);
			if (countdown <= 0) {
				stopAll();
				orderInfo = null;
				toast.error($i18n.t('订单已过期，请重新创建'));
			}
		}, 1000);
	};

	// 轮询订单状态
	const startPolling = () => {
		if (pollTimer) clearInterval(pollTimer);

		pollTimer = setInterval(async () => {
			if (!orderInfo) return;

			try {
				const status = await getPaymentStatus(localStorage.token, orderInfo.order_id);
				if (status.status === 'paid') {
					stopAll();
					toast.success($i18n.t('充值成功！已到账') + ` ¥${status.amount}`);
					orderInfo = null;

					// 刷新余额
					try {
						const balanceInfo = await getBalance(localStorage.token);
						balance.set(balanceInfo);
					} catch (e) {
						console.error('刷新余额失败', e);
					}
				}
			} catch (e) {
				console.error('轮询订单状态失败', e);
			}
		}, 3000); // 每3秒轮询一次
	};

	const stopAll = () => {
		if (pollTimer) {
			clearInterval(pollTimer);
			pollTimer = null;
		}
		if (countdownTimer) {
			clearInterval(countdownTimer);
			countdownTimer = null;
		}
	};

	const cancelOrder = () => {
		stopAll();
		orderInfo = null;
	};

	const formatCountdown = (seconds: number) => {
		if (seconds <= 0) return '0:00';
		const mins = Math.floor(seconds / 60);
		const secs = seconds % 60;
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	};

	onDestroy(() => {
		stopAll();
	});
</script>

<div class="p-4 bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm">
	<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
		{$i18n.t('账户充值')}
	</h3>

	{#if !alipayEnabled}
		<!-- 支付未配置 -->
		<div class="text-center py-6 text-gray-500 dark:text-gray-400">
			<svg class="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
			</svg>
			<p class="text-sm">{$i18n.t('充值功能暂未开放')}</p>
			<p class="text-xs mt-1">{$i18n.t('请联系管理员')}</p>
		</div>
	{:else if !orderInfo}
		<!-- 金额选择 -->
		<div class="space-y-4">
			<div class="grid grid-cols-3 gap-2">
				{#each amountOptions as amount}
					<button
						class="py-2 px-3 rounded-lg border text-sm font-medium transition-colors
							{selectedAmount === amount
							? 'border-indigo-500 bg-indigo-50 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400'
							: 'border-gray-200 dark:border-gray-600 hover:border-indigo-300 dark:hover:border-indigo-500 text-gray-700 dark:text-gray-300'}"
						on:click={() => {
							selectedAmount = amount;
							customAmount = '';
						}}
					>
						¥{amount}
					</button>
				{/each}
			</div>

			<!-- 自定义金额 -->
			<div>
				<input
					type="number"
					bind:value={customAmount}
					on:input={() => (selectedAmount = null)}
					placeholder={$i18n.t('自定义金额 (1-10000)')}
					class="w-full px-3 py-2 border border-gray-200 dark:border-gray-600 rounded-lg
						bg-white dark:bg-gray-700 text-sm text-gray-900 dark:text-gray-100
						focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
				/>
			</div>

			<!-- 充值按钮 -->
			<button
				on:click={createOrder}
				disabled={!isValidAmount || loading}
				class="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 dark:disabled:bg-gray-600
					text-white font-medium rounded-lg transition-colors disabled:cursor-not-allowed"
			>
				{#if loading}
					<span class="flex items-center justify-center gap-2">
						<span class="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></span>
						{$i18n.t('创建订单中...')}
					</span>
				{:else}
					{$i18n.t('立即充值')} {isValidAmount ? `¥${finalAmount}` : ''}
				{/if}
			</button>

			<p class="text-xs text-gray-500 dark:text-gray-400 text-center">
				{$i18n.t('支持支付宝扫码支付')}
			</p>
		</div>
	{:else}
		<!-- 支付二维码 -->
		<div class="text-center space-y-4">
			<div class="inline-block p-3 bg-white rounded-lg shadow-sm">
				<img src={qrCodeDataUrl} alt="支付二维码" class="w-48 h-48" />
			</div>

			<div>
				<p class="text-lg font-semibold text-gray-900 dark:text-white">
					¥{orderInfo.amount}
				</p>
				<p class="text-sm text-gray-500 dark:text-gray-400">
					{$i18n.t('请使用支付宝扫码支付')}
				</p>
			</div>

			<div class="text-sm text-orange-500 dark:text-orange-400">
				{$i18n.t('剩余时间')}: {formatCountdown(countdown)}
			</div>

			<button
				on:click={cancelOrder}
				class="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
			>
				{$i18n.t('取消订单')}
			</button>
		</div>
	{/if}
</div>
