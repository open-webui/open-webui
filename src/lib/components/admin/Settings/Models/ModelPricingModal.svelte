<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, getContext } from 'svelte';
	import { setModelPricing } from '$lib/apis/billing';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let model: any;
	export let pricing: any;

	let inputPrice = 0; // 元/M
	let outputPrice = 0; // 元/M
	let loading = false;
	let initialized = false;

	// 只在弹窗首次打开时初始化，之后不再重置
	$: if (show && !initialized) {
		if (pricing) {
			// 初始化：毫 → 元
			inputPrice = pricing.input_price / 10000;
			outputPrice = pricing.output_price / 10000;
		} else {
			// 无定价时，使用 0
			inputPrice = 0;
			outputPrice = 0;
		}
		initialized = true;
	} else if (!show) {
		// 弹窗关闭时重置标志
		initialized = false;
	}

	const submitHandler = async () => {
		if (inputPrice < 0 || outputPrice < 0) {
			toast.error($i18n.t('价格不能为负数'));
			return;
		}

		loading = true;
		try {
			// 提交：元 → 毫
			await setModelPricing(localStorage.token, {
				model_id: model.id,
				input_price: Math.round(inputPrice * 10000),
				output_price: Math.round(outputPrice * 10000)
			});

			toast.success($i18n.t('定价更新成功'));
			dispatch('save');
			show = false;
		} catch (error: any) {
			toast.error(`${$i18n.t('更新失败')}: ${error.detail || error}`);
		} finally {
			loading = false;
		}
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<div class="flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
			<div class="text-lg font-medium self-center">
				{$i18n.t('编辑模型定价')} - {model?.name}
			</div>
			<button class="self-center" on:click={() => (show = false)}>
				<XMark className={'size-5'} />
			</button>
		</div>

		<form class="flex flex-col w-full px-5 pb-5" on:submit|preventDefault={submitHandler}>
			<!-- 模型ID -->
			<div class="mb-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
				<div class="text-sm text-gray-600 dark:text-gray-400">
					{$i18n.t('模型ID')}: <code class="font-mono">{model?.id}</code>
				</div>
			</div>

			<!-- 输入价格 -->
			<div class="mb-4">
				<label class="block text-sm font-medium mb-2 dark:text-gray-300">
					{$i18n.t('输入价格')} ({$i18n.t('元')}/{$i18n.t('百万tokens')})
				</label>
				<input
					type="number"
					step="0.01"
					min="0"
					bind:value={inputPrice}
					class="w-full px-3 py-2 border dark:border-gray-600 rounded-lg dark:bg-gray-800 dark:text-gray-100"
					placeholder="{$i18n.t('例如')}: 2.5"
					required
				/>
				<div class="text-xs text-gray-500 dark:text-gray-400 mt-1">
					{$i18n.t('当前')}: ¥{(inputPrice || 0).toFixed(2)}/M = {((inputPrice || 0) * 10000).toFixed(
						0
					)} {$i18n.t('毫')}/M
				</div>
			</div>

			<!-- 输出价格 -->
			<div class="mb-4">
				<label class="block text-sm font-medium mb-2 dark:text-gray-300">
					{$i18n.t('输出价格')} ({$i18n.t('元')}/{$i18n.t('百万tokens')})
				</label>
				<input
					type="number"
					step="0.01"
					min="0"
					bind:value={outputPrice}
					class="w-full px-3 py-2 border dark:border-gray-600 rounded-lg dark:bg-gray-800 dark:text-gray-100"
					placeholder="{$i18n.t('例如')}: 10"
					required
				/>
				<div class="text-xs text-gray-500 dark:text-gray-400 mt-1">
					{$i18n.t('当前')}: ¥{(outputPrice || 0).toFixed(2)}/M = {((outputPrice || 0) * 10000).toFixed(
						0
					)} {$i18n.t('毫')}/M
				</div>
			</div>

			<!-- 预览 -->
			<div class="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm">
				<div class="font-medium mb-2">
					{$i18n.t('计费预览')} ({$i18n.t('以')} 1000 tokens {$i18n.t('为例')})
				</div>
				<div class="space-y-1 text-xs">
					<div>{$i18n.t('输入')}: ¥{((inputPrice || 0) * 0.001).toFixed(4)}</div>
					<div>{$i18n.t('输出')}: ¥{((outputPrice || 0) * 0.001).toFixed(4)}</div>
					<div class="font-medium">
						{$i18n.t('总计')}: ¥{(((inputPrice || 0) + (outputPrice || 0)) * 0.001).toFixed(4)}
					</div>
				</div>
			</div>

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
					class="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white"
					disabled={loading}
				>
					{loading ? $i18n.t('保存中') + '...' : $i18n.t('保存')}
				</button>
			</div>
		</form>
	</div>
</Modal>
