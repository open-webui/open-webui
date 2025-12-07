<script lang="ts">
	import { getContext } from 'svelte';
	import { rechargeUser, setModelPricing, listModelPricing } from '$lib/apis/billing';
	import { toast } from 'svelte-sonner';
	import type { ModelPricing } from '$lib/apis/billing';

	const i18n = getContext('i18n');

	// 充值表单
	let userId = '';
	let amount = 0;
	let remark = '';
	let rechargeLoading = false;

	// 定价管理
	let modelId = '';
	let inputPrice = 0;
	let outputPrice = 0;
	let pricingLoading = false;
	let pricings: ModelPricing[] = [];

	const handleRecharge = async () => {
		if (!userId || amount <= 0) {
			toast.error($i18n.t('请填写正确的用户ID和充值金额'));
			return;
		}

		rechargeLoading = true;
		try {
			const result = await rechargeUser(localStorage.token, {
				user_id: userId,
				amount,
				remark
			});

			toast.success($i18n.t('充值成功！余额: ') + result.balance);

			// 重置表单
			userId = '';
			amount = 0;
			remark = '';
		} catch (error) {
			toast.error($i18n.t('充值失败: ') + error.message);
		} finally {
			rechargeLoading = false;
		}
	};

	const handleSetPricing = async () => {
		if (!modelId || inputPrice < 0 || outputPrice < 0) {
			toast.error('请填写正确的模型ID和价格');
			return;
		}

		pricingLoading = true;
		try {
			await setModelPricing(localStorage.token, {
				model_id: modelId,
				input_price: inputPrice,
				output_price: outputPrice
			});

			toast.success('定价设置成功');

			// 重置表单并刷新列表
			modelId = '';
			inputPrice = 0;
			outputPrice = 0;
			loadPricings();
		} catch (error) {
			toast.error('设置定价失败: ' + error.message);
		} finally {
			pricingLoading = false;
		}
	};

	const loadPricings = async () => {
		try {
			pricings = await listModelPricing();
		} catch (error) {
			console.error('加载定价列表失败:', error);
		}
	};

	// 页面加载时获取定价列表
	loadPricings();
</script>

<svelte:head>
	<title>{$i18n.t('充值管理')} | Cakumi Admin</title>
</svelte:head>

<div class="admin-billing-page max-w-6xl mx-auto px-4 py-6 space-y-6">
	<!-- 页面标题 -->
	<div class="page-header">
		<h1 class="text-2xl font-bold text-gray-900 dark:text-white">{$i18n.t('充值管理')}</h1>
		<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">管理用户充值和模型定价</p>
	</div>

	<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
		<!-- 用户充值表单 -->
		<div class="recharge-form bg-white dark:bg-gray-850 rounded-xl shadow-sm p-6">
			<h2 class="text-lg font-semibold mb-4">{$i18n.t('用户充值')}</h2>

			<div class="space-y-4">
				<div class="form-group">
					<label for="userId" class="block text-sm font-medium mb-2">
						{$i18n.t('用户ID')}
					</label>
					<input
						id="userId"
						type="text"
						bind:value={userId}
						placeholder="请输入用户ID"
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
					/>
				</div>

				<div class="form-group">
					<label for="amount" class="block text-sm font-medium mb-2">
						{$i18n.t('充值金额（元）')}
					</label>
					<input
						id="amount"
						type="number"
						step="0.01"
						min="0"
						bind:value={amount}
						placeholder="请输入充值金额"
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
					/>
				</div>

				<div class="form-group">
					<label for="remark" class="block text-sm font-medium mb-2">
						{$i18n.t('备注')}
					</label>
					<textarea
						id="remark"
						bind:value={remark}
						placeholder="充值备注（可选）"
						rows="3"
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
					/>
				</div>

				<button
					class="w-full px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-400 text-white rounded-lg font-medium transition"
					on:click={handleRecharge}
					disabled={rechargeLoading}
				>
					{rechargeLoading ? $i18n.t('充值中...') : $i18n.t('确认充值')}
				</button>
			</div>
		</div>

		<!-- 模型定价设置 -->
		<div class="pricing-form bg-white dark:bg-gray-850 rounded-xl shadow-sm p-6">
			<h2 class="text-lg font-semibold mb-4">模型定价设置</h2>

			<div class="space-y-4">
				<div class="form-group">
					<label for="modelId" class="block text-sm font-medium mb-2">模型ID</label>
					<input
						id="modelId"
						type="text"
						bind:value={modelId}
						placeholder="例如: gpt-4o"
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
					/>
				</div>

				<div class="form-group">
					<label for="inputPrice" class="block text-sm font-medium mb-2">
						输入价格（元/百万token）
					</label>
					<input
						id="inputPrice"
						type="number"
						step="0.01"
						min="0"
						bind:value={inputPrice}
						placeholder="例如: 2.5"
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
					/>
				</div>

				<div class="form-group">
					<label for="outputPrice" class="block text-sm font-medium mb-2">
						输出价格（元/百万token）
					</label>
					<input
						id="outputPrice"
						type="number"
						step="0.01"
						min="0"
						bind:value={outputPrice}
						placeholder="例如: 10.0"
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
					/>
				</div>

				<button
					class="w-full px-4 py-2 bg-green-500 hover:bg-green-600 disabled:bg-gray-400 text-white rounded-lg font-medium transition"
					on:click={handleSetPricing}
					disabled={pricingLoading}
				>
					{pricingLoading ? '设置中...' : '设置定价'}
				</button>
			</div>
		</div>
	</div>

	<!-- 已配置的定价列表 -->
	{#if pricings.length > 0}
		<div class="pricing-list bg-white dark:bg-gray-850 rounded-xl shadow-sm p-6">
			<h2 class="text-lg font-semibold mb-4">已配置的模型定价</h2>

			<div class="overflow-x-auto">
				<table class="w-full">
					<thead>
						<tr class="border-b border-gray-200 dark:border-gray-700">
							<th class="px-4 py-3 text-left text-sm font-semibold">模型ID</th>
							<th class="px-4 py-3 text-right text-sm font-semibold">输入价格</th>
							<th class="px-4 py-3 text-right text-sm font-semibold">输出价格</th>
							<th class="px-4 py-3 text-center text-sm font-semibold">来源</th>
						</tr>
					</thead>
					<tbody>
						{#each pricings as pricing}
							<tr class="border-b border-gray-100 dark:border-gray-800">
								<td class="px-4 py-3">
									<code class="px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded text-xs">
										{pricing.model_id}
									</code>
								</td>
								<td class="px-4 py-3 text-right">¥{pricing.input_price.toFixed(2)}</td>
								<td class="px-4 py-3 text-right">¥{pricing.output_price.toFixed(2)}</td>
								<td class="px-4 py-3 text-center">
									<span
										class="px-2 py-1 text-xs rounded"
										class:bg-blue-100={pricing.source === 'database'}
										class:text-blue-800={pricing.source === 'database'}
										class:bg-gray-100={pricing.source === 'default'}
										class:text-gray-800={pricing.source === 'default'}
									>
										{pricing.source === 'database' ? '数据库' : '默认'}
									</span>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{/if}
</div>
