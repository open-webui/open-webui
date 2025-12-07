<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Modal from '$lib/components/common/Modal.svelte';
	import { createUserSuggestionFeedback } from '$lib/apis/evaluations';

	const i18n = getContext('i18n');

	export let show = false;
	export let onClose: () => void = () => {};

	let content = '';
	let contact = '';
	let submitting = false;

	const reset = () => {
		content = '';
		contact = '';
	};

	const handleClose = () => {
		reset();
		onClose();
	};

	const submit = async () => {
		if (submitting) return;
		const trimmed = content.trim();
		if (!trimmed) {
			toast.error('请填写反馈内容');
			return;
		}
		submitting = true;
		try {
			await createUserSuggestionFeedback(localStorage.token, {
				content: trimmed,
				contact: contact.trim() || undefined
			});
			toast.success('反馈已提交，感谢您的建议');
			handleClose();
		} catch (err) {
			const msg = typeof err === 'string' ? err : err?.detail ?? '提交失败，请稍后重试';
			toast.error(msg);
		} finally {
			submitting = false;
		}
	};
</script>

<Modal bind:show className="bg-white dark:bg-gray-900 rounded-2xl" size="sm">
	<div class="p-4 sm:p-6 space-y-4">
		<div class="text-lg font-semibold text-gray-900 dark:text-white">
			{$i18n.t('反馈') ?? '反馈'}
		</div>

		<div class="space-y-2">
			<label class="text-sm text-gray-600 dark:text-gray-300">{$i18n.t('反馈内容') ?? '反馈内容'}</label>
			<textarea
				class="w-full rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-850 p-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
				rows="5"
				placeholder={$i18n.t('请描述您遇到的问题或建议') ?? '请描述您遇到的问题或建议'}
				bind:value={content}
			/>
		</div>

		<div class="space-y-2">
			<label class="text-sm text-gray-600 dark:text-gray-300">{$i18n.t('联系方式（可选）') ?? '联系方式（可选）'}</label>
			<input
				class="w-full rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-850 p-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
				placeholder={$i18n.t('邮箱/手机号/微信等') ?? '邮箱/手机号/微信等'}
				bind:value={contact}
			/>
		</div>

		<div class="flex justify-end gap-3 pt-2">
			<button
				class="px-4 py-2 rounded-xl text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
				on:click={handleClose}
				disabled={submitting}
			>
				{$i18n.t('取消') ?? '取消'}
			</button>
			<button
				class="px-4 py-2 rounded-xl text-sm text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-60"
				on:click={submit}
				disabled={submitting}
			>
				{submitting ? $i18n.t('提交中...') ?? '提交中...' : $i18n.t('提交') ?? '提交'}
			</button>
		</div>
	</div>
</Modal>
