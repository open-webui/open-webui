<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';

	import { getRechargeLogsByUserId, type RechargeLog } from '$lib/apis/billing';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let selectedUser: any;

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
				{$i18n.t('充值记录')} - {selectedUser?.name}
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
								<tr class="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800">
									<td class="py-2 px-2 text-sm dark:text-gray-300">
										{formatDate(log.created_at)}
									</td>
									<td
										class="text-right py-2 px-2 text-sm font-medium"
										class:text-green-600={log.amount > 0}
										class:text-red-600={log.amount < 0}
									>
										{log.amount > 0 ? '+' : ''}{log.amount.toFixed(2)} {$i18n.t('元')}
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
</Modal>
