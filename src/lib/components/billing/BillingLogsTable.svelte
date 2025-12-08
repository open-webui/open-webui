<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { billingLogs } from '$lib/stores';
	import { getBillingLogs } from '$lib/apis/billing';
	import { formatCurrency, formatDate } from '$lib/stores';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	let loading = false;
	let limit = 50;
	let offset = 0;
	let hasMore = true;
	let expandedLogIds = new Set<string>();

	const loadLogs = async () => {
		loading = true;
		try {
			const logs = await getBillingLogs(localStorage.token, limit, offset);

			if (logs.length < limit) {
				hasMore = false;
			}

			billingLogs.update((current) => [...current, ...logs]);
			offset += logs.length;
		} catch (error) {
			toast.error($i18n.t('加载消费记录失败: ') + error.message);
		} finally {
			loading = false;
		}
	};

	onMount(() => {
		// 清空之前的记录
		billingLogs.set([]);
		expandedLogIds = new Set(); // 清空展开状态
		offset = 0;
		hasMore = true;
		loadLogs();
	});

	// 合并流式请求的 precharge + settle 为一条记录
	$: mergedLogs = (() => {
		const result = [];
		const prechargeMap = new Map();
		const processedIds = new Set(); // 跟踪已处理的记录ID，避免重复

		// 第一遍：收集所有 precharge 记录
		$billingLogs.forEach((log) => {
			if (log.type === 'precharge' && log.precharge_id) {
				prechargeMap.set(log.precharge_id, log);
			}
		});

		// 第二遍：合并或直接添加
		$billingLogs.forEach((log) => {
			// 跳过已处理的记录
			if (processedIds.has(log.id)) {
				return;
			}

			if (log.type === 'settle' && log.precharge_id) {
				// 流式请求的 settle 记录，合并预扣费信息
				const precharge = prechargeMap.get(log.precharge_id);
				result.push({
					...log,
					displayType: 'streaming', // 标记为流式请求
					prechargeAmount: precharge?.cost || 0,
					refundAmount: precharge ? precharge.cost - log.cost : 0
				});
				processedIds.add(log.id);
				// 同时标记对应的 precharge 已处理
				if (precharge) {
					processedIds.add(precharge.id);
				}
			} else if (log.type === 'precharge') {
				// 检查是否已被 settle 处理过
				if (processedIds.has(log.id)) {
					return;
				}
				// 检查是否有对应的 settle（异常情况：孤立的 precharge）
				const hasSettle = $billingLogs.some(
					(l) => l.type === 'settle' && l.precharge_id === log.precharge_id
				);
				if (!hasSettle) {
					// 孤立的 precharge（可能是请求失败），保留显示
					result.push({ ...log, displayType: 'precharge-only' });
					processedIds.add(log.id);
				}
			} else {
				// deduct, refund 等其他类型，直接显示
				result.push({ ...log, displayType: log.type });
				processedIds.add(log.id);
			}
		});

		return result;
	})();

	const getLogTypeLabel = (displayType: string) => {
		const labels = {
			streaming: '流式请求',
			deduct: '直接扣费',
			refund: '退款',
			'precharge-only': '预扣费（未完成）'
		};
		return labels[displayType] || displayType;
	};

	const getLogTypeClass = (displayType: string) => {
		const classes = {
			streaming: 'text-blue-600 dark:text-blue-400',
			deduct: 'text-red-600 dark:text-red-400',
			refund: 'text-green-600 dark:text-green-400',
			'precharge-only': 'text-yellow-600 dark:text-yellow-400'
		};
		return classes[displayType] || '';
	};

	const toggleExpand = (logId: string) => {
		if (expandedLogIds.has(logId)) {
			expandedLogIds.delete(logId);
		} else {
			expandedLogIds.add(logId);
		}
		expandedLogIds = expandedLogIds; // 触发响应式更新
	};
</script>

<div class="billing-logs-table bg-white dark:bg-gray-850 rounded-xl shadow-sm">
	<div class="table-header px-4 py-3 border-b border-gray-100 dark:border-gray-800">
		<h2 class="text-lg font-semibold">{$i18n.t('消费记录')}</h2>
	</div>

	<div class="table-container overflow-x-auto">
		<table class="w-full">
			<thead>
				<tr class="bg-gray-50 dark:bg-gray-800">
					<th class="px-4 py-3 text-left text-xs font-semibold whitespace-nowrap">{$i18n.t('时间')}</th>
					<th class="px-4 py-3 text-left text-xs font-semibold whitespace-nowrap">{$i18n.t('模型')}</th>
					<th class="px-4 py-3 text-left text-xs font-semibold whitespace-nowrap">{$i18n.t('类型')}</th>
					<th class="px-4 py-3 text-right text-xs font-semibold whitespace-nowrap">{$i18n.t('输入Token')}</th>
					<th class="px-4 py-3 text-right text-xs font-semibold whitespace-nowrap">{$i18n.t('输出Token')}</th>
					<th class="px-4 py-3 text-right text-xs font-semibold whitespace-nowrap">{$i18n.t('费用')}</th>
					<th class="px-4 py-3 text-right text-xs font-semibold whitespace-nowrap">{$i18n.t('余额')}</th>
				</tr>
			</thead>
			<tbody>
				{#each mergedLogs as log (log.id)}
					<tr class="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50">
						<td class="px-4 py-3 text-sm whitespace-nowrap">{formatDate(log.created_at)}</td>
						<td class="px-4 py-3 whitespace-nowrap">
							<code
								class="px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded text-xs font-mono max-w-[160px] truncate inline-block align-middle"
								title={log.model_id}
							>
								{log.model_id}
							</code>
						</td>
						<td class="px-4 py-3 whitespace-nowrap">
							<div class="flex items-center gap-2">
								<span class="text-sm font-semibold {getLogTypeClass(log.displayType)}">
									{getLogTypeLabel(log.displayType)}
								</span>
								{#if log.displayType === 'streaming'}
									<button
										class="text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
										on:click={() => toggleExpand(log.id)}
										title={expandedLogIds.has(log.id) ? '收起详情' : '展开详情'}
									>
										{#if expandedLogIds.has(log.id)}
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
											</svg>
										{:else}
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
											</svg>
										{/if}
									</button>
								{/if}
							</div>
						</td>
						<td class="px-4 py-3 text-right text-sm whitespace-nowrap">{log.prompt_tokens.toLocaleString()}</td>
						<td class="px-4 py-3 text-right text-sm whitespace-nowrap">
							{log.completion_tokens.toLocaleString()}
						</td>
						<td class="px-4 py-3 text-right text-sm font-semibold whitespace-nowrap" class:text-green-600={log.cost < 0} class:text-red-600={log.cost >= 0}>
							{formatCurrency(log.cost, true)}
						</td>
						<td class="px-4 py-3 text-right text-sm whitespace-nowrap">
							{log.balance_after !== null ? formatCurrency(log.balance_after, false) : '-'}
						</td>
					</tr>

					<!-- 流式请求的展开详情 -->
					{#if log.displayType === 'streaming' && expandedLogIds.has(log.id)}
						<tr class="bg-blue-50 dark:bg-blue-900/10 border-b border-gray-100 dark:border-gray-800">
							<td colspan="7" class="px-4 py-3">
								<div class="text-xs space-y-1 text-gray-600 dark:text-gray-400">
									<div class="flex justify-between">
										<span>预扣金额:</span>
										<span class="font-mono">{formatCurrency(log.prechargeAmount, true)}</span>
									</div>
									<div class="flex justify-between">
										<span>实际消费:</span>
										<span class="font-mono">{formatCurrency(log.cost, true)}</span>
									</div>
									<div class="flex justify-between" class:text-green-600={log.refundAmount > 0} class:text-red-600={log.refundAmount < 0} class:dark:text-green-400={log.refundAmount > 0} class:dark:text-red-400={log.refundAmount < 0}>
										<span>{log.refundAmount >= 0 ? '退款金额' : '补扣金额'}:</span>
										<span class="font-mono">
											{#if log.refundAmount > 0}
												+{formatCurrency(log.refundAmount, true)}
											{:else if log.refundAmount < 0}
												{formatCurrency(log.refundAmount, true)}
											{:else}
												{formatCurrency(0, true)}
											{/if}
										</span>
									</div>
									{#if log.precharge_id}
										<div class="flex justify-between pt-1 mt-1 border-t border-gray-200 dark:border-gray-700">
											<span>事务ID:</span>
											<code class="font-mono text-xs">{log.precharge_id.slice(0, 8)}...</code>
										</div>
									{/if}
								</div>
							</td>
						</tr>
					{/if}
				{/each}
			</tbody>
		</table>

		{#if loading}
			<div class="flex justify-center items-center py-8">
				<Spinner />
			</div>
		{/if}

		{#if !loading && hasMore}
			<div class="flex justify-center py-4">
				<button
					class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium transition"
					on:click={loadLogs}
				>
					{$i18n.t('加载更多')}
				</button>
			</div>
		{/if}

		{#if !loading && mergedLogs.length === 0}
			<div class="flex flex-col items-center justify-center py-12 text-gray-500">
				<svg
					class="w-16 h-16 mb-4 opacity-50"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="1.5"
						d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
					/>
				</svg>
				<p class="text-sm">{$i18n.t('暂无消费记录')}</p>
			</div>
		{/if}
	</div>
</div>
