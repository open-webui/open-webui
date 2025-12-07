<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, getContext } from 'svelte';

	import { rechargeUser } from '$lib/apis/billing';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let selectedUser: any;
	export let operation: 'recharge' | 'deduct' = 'recharge';

	let amount = 0;
	let remark = '';
	let showConfirmDialog = false;
	let loading = false;

	$: operationText = operation === 'recharge' ? $i18n.t('充值') : $i18n.t('扣费');
	$: finalAmount = operation === 'deduct' ? -amount : amount;
	// 余额显示单位：元，后端存储单位：毫（1元 = 10000毫）
	$: currentBalanceYuan = Number(selectedUser?.balance || 0) / 10000;
	$: newBalance = currentBalanceYuan + finalAmount;

	const submitHandler = () => {
		if (amount <= 0) {
			toast.error($i18n.t('金额必须大于0'));
			return;
		}
		if (!remark.trim()) {
			toast.error($i18n.t('请填写备注说明操作原因'));
			return;
		}
		showConfirmDialog = true;
	};

	const confirmSubmit = async () => {
		loading = true;
		showConfirmDialog = false;

		try {
			// 提交到后端时：元 * 10000 = 毫
			const amountInMilli = Math.round(finalAmount * 10000);
			const result = await rechargeUser(localStorage.token, {
				user_id: selectedUser.id,
				amount: amountInMilli,
				remark
			});

			// 后端返回的余额单位：毫，显示时除以10000
			const balanceYuan = result.balance / 10000;
			toast.success(`${operationText}${$i18n.t('成功')}! ${$i18n.t('当前余额')}: ¥${balanceYuan.toFixed(2)}`);
			dispatch('save');
			show = false;

			// 重置表单
			amount = 0;
			remark = '';
		} catch (error: any) {
			toast.error(`${operationText}${$i18n.t('失败')}: ${error.detail || error}`);
		} finally {
			loading = false;
		}
	};

	const cancelConfirm = () => {
		showConfirmDialog = false;
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<div class="flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
			<div class="text-lg font-medium self-center">
				{operationText} - {selectedUser?.name}
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

		<form
			class="flex flex-col w-full px-5 pb-5"
			on:submit|preventDefault={submitHandler}
		>
			<!-- 当前余额信息 -->
			<div class="mb-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
				<div class="flex justify-between text-sm mb-1">
					<span>{$i18n.t('当前余额')}:</span>
					<span class="font-medium">¥{(Number(selectedUser?.balance || 0) / 10000).toFixed(2)}</span>
				</div>
				<div class="flex justify-between text-sm">
					<span>{$i18n.t('累计消费')}:</span>
					<span>¥{(Number(selectedUser?.total_consumed || 0) / 10000).toFixed(2)}</span>
				</div>
			</div>

			<!-- 金额输入 -->
			<div class="mb-4">
				<label class="block text-sm font-medium mb-2 dark:text-gray-300">
					{operationText}{$i18n.t('金额')} ({$i18n.t('元')})
				</label>
				<input
					type="number"
					step="0.01"
					min="0"
					bind:value={amount}
					class="w-full px-3 py-2 border dark:border-gray-600 rounded-lg dark:bg-gray-800 dark:text-gray-100"
					placeholder={$i18n.t('请输入金额')}
					required
				/>
			</div>

			<!-- 备注输入 -->
			<div class="mb-4">
				<label class="block text-sm font-medium mb-2 dark:text-gray-300">
					{$i18n.t('备注')} ({$i18n.t('必填')})
				</label>
				<textarea
					bind:value={remark}
					rows="3"
					class="w-full px-3 py-2 border dark:border-gray-600 rounded-lg dark:bg-gray-800 dark:text-gray-100"
					placeholder={$i18n.t('请说明操作原因')}
					required
				/>
			</div>

			<!-- 预览 -->
			{#if amount > 0}
				<div class="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm">
					<div class="flex justify-between">
						<span>{operationText}{$i18n.t('后余额')}:</span>
						<span class="font-medium" class:text-red-600={newBalance < 0}>
							¥{newBalance.toFixed(2)}
						</span>
					</div>
				</div>
			{/if}

			<!-- 按钮 -->
			<div class="flex justify-end gap-2">
				<button
					type="button"
					class="px-4 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 dark:text-gray-300"
					on:click={() => (show = false)}
				>
					{$i18n.t('取消')}
				</button>
				<button
					type="submit"
					class="px-4 py-2 rounded-lg text-white"
					class:bg-green-600={operation === 'recharge'}
					class:hover:bg-green-700={operation === 'recharge'}
					class:bg-red-600={operation === 'deduct'}
					class:hover:bg-red-700={operation === 'deduct'}
					disabled={loading}
				>
					{loading ? $i18n.t('处理中') + '...' : $i18n.t('确认') + operationText}
				</button>
			</div>
		</form>
	</div>
</Modal>

<!-- 二次确认对话框 -->
{#if showConfirmDialog}
	<Modal size="sm" bind:show={showConfirmDialog}>
		<div class="px-5 py-4">
			<div class="text-lg font-medium mb-4 dark:text-gray-300">
				{$i18n.t('确认')}{operationText}
			</div>
			<div class="mb-4 dark:text-gray-300">
				<p>
					{$i18n.t('确认为用户')} <strong>{selectedUser?.name}</strong> {operationText}
					<strong>¥{amount.toFixed(2)}</strong> {$i18n.t('元吗')}?
				</p>
				<p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
					{$i18n.t('当前余额')}: ¥{(Number(selectedUser?.balance || 0) / 10000).toFixed(2)}<br />
					{operationText}{$i18n.t('后余额')}: ¥{newBalance.toFixed(2)}
				</p>
				<p class="mt-2 text-sm dark:text-gray-400">
					{$i18n.t('备注')}: {remark}
				</p>
			</div>
			<div class="flex justify-end gap-2">
				<button
					type="button"
					class="px-4 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 dark:text-gray-300"
					on:click={cancelConfirm}
				>
					{$i18n.t('取消')}
				</button>
				<button
					type="button"
					class="px-4 py-2 rounded-lg text-white"
					class:bg-green-600={operation === 'recharge'}
					class:hover:bg-green-700={operation === 'recharge'}
					class:bg-red-600={operation === 'deduct'}
					class:hover:bg-red-700={operation === 'deduct'}
					on:click={confirmSubmit}
					disabled={loading}
				>
					{loading ? $i18n.t('处理中') + '...' : $i18n.t('确认')}
				</button>
			</div>
		</div>
	</Modal>
{/if}
