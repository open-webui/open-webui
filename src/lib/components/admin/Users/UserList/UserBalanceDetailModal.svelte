<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';

	import { getRechargeLogsByUserId, type RechargeLog } from '$lib/apis/billing';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let selectedUser: any;
	export let onRecharge: () => void;
	export let onDeduct: () => void;

	let logs: RechargeLog[] = [];
	let loading = true;

	const loadLogs = async () => {
		if (!selectedUser?.id) return;

		loading = true;
		try {
			logs = await getRechargeLogsByUserId(localStorage.token, selectedUser.id);
		} catch (error: any) {
			console.error('加载充值记录失败:', error);
			toast.error($i18n.t('加载充值记录失败') + ': ' + (error.detail || error));
		} finally {
			loading = false;
		}
	};

	$: if (show && selectedUser) {
		loadLogs();
	}

	const formatDate = (timestamp: number) => {
		// 纳秒级时间戳转换为毫秒
		const date = new Date(timestamp / 1000000);
		return date.toLocaleString('zh-CN', {
			year: 'numeric',
			month: '2-digit',
			day: '2-digit',
			hour: '2-digit',
			minute: '2-digit',
			second: '2-digit'
		});
	};
</script>

<Modal size="lg" bind:show>
	<div>
		<div class="flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
			<div class="text-lg font-medium self-center">
				{$i18n.t('余额详情')} - {selectedUser?.name}
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="px-5 pb-5">
			<!-- 余额信息卡片 -->
			<div class="mb-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
				<div class="flex justify-between items-center mb-3">
					<div>
						<div class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('当前余额')}</div>
						<div class="text-2xl font-bold">
							¥{(Number(selectedUser?.balance || 0) / 10000).toFixed(2)}
						</div>
					</div>
					<div class="text-right">
						<div class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('累计消费')}</div>
						<div class="text-lg">¥{(Number(selectedUser?.total_consumed || 0) / 10000).toFixed(2)}</div>
					</div>
				</div>

				<!-- 操作按钮 -->
				<div class="flex gap-2">
					<button
						class="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition"
						on:click={() => {
							show = false;
							onRecharge();
						}}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="w-4 h-4 inline-block mr-1"
						>
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 6v12m6-6H6" />
						</svg>
						{$i18n.t('充值')}
					</button>
					<button
						class="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition"
						on:click={() => {
							show = false;
							onDeduct();
						}}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="w-4 h-4 inline-block mr-1"
						>
							<path stroke-linecap="round" stroke-linejoin="round" d="M20 12H4" />
						</svg>
						{$i18n.t('扣费')}
					</button>
				</div>
			</div>

			<!-- 充值记录 -->
			<div>
				<h3 class="text-md font-medium mb-3 dark:text-gray-300">
					{$i18n.t('充值记录')} / {$i18n.t('余额修改记录')}
				</h3>

				{#if loading}
					<div class="text-center py-8 dark:text-gray-400">
						{$i18n.t('加载中')}...
					</div>
				{:else if logs.length === 0}
					<div class="text-center py-8 text-gray-500 dark:text-gray-400">
						{$i18n.t('暂无充值记录')}
					</div>
				{:else}
					<div class="overflow-x-auto">
						<table class="w-full">
							<thead>
								<tr class="border-b dark:border-gray-700">
									<th class="text-left py-2 px-2 text-sm font-medium dark:text-gray-300">
										{$i18n.t('时间')}
									</th>
									<th class="text-right py-2 px-2 text-sm font-medium dark:text-gray-300">
										{$i18n.t('金额')}
									</th>
									<th class="text-left py-2 px-2 text-sm font-medium dark:text-gray-300">
										{$i18n.t('操作员')}
									</th>
									<th class="text-left py-2 px-2 text-sm font-medium dark:text-gray-300">
										{$i18n.t('备注')}
									</th>
								</tr>
							</thead>
							<tbody>
								{#each logs as log}
									<tr
										class="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
									>
										<td class="py-2 px-2 text-sm dark:text-gray-300">
											{formatDate(log.created_at)}
										</td>
										<td
											class="text-right py-2 px-2 text-sm font-medium"
											class:text-green-600={log.amount > 0}
											class:text-red-600={log.amount < 0}
										>
											{log.amount > 0 ? '+' : ''}{(log.amount / 10000).toFixed(2)}
											{$i18n.t('元')}
										</td>
										<td class="py-2 px-2 text-sm dark:text-gray-300">
											{log.operator_name}
										</td>
										<td class="py-2 px-2 text-sm text-gray-600 dark:text-gray-400">
											{log.remark || '-'}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}
			</div>
		</div>
	</div>
</Modal>
