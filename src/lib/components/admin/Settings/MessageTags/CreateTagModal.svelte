<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';

	import Modal from '$lib/components/common/Modal.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { createProtectedTag } from '$lib/apis/message-tags';

	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;

	let name = '';
	let isProtected = true;
	let saving = false;

	const handleSubmit = async () => {
		if (!name.trim()) {
			toast.error($i18n.t('태그 이름을 입력해주세요.'));
			return;
		}

		saving = true;
		try {
			const result = await createProtectedTag(localStorage.token, name.trim(), isProtected);
			if (result) {
				dispatch('created', result);
				toast.success($i18n.t('태그가 생성되었습니다.'));
				resetForm();
			}
		} catch (error) {
			console.error('Failed to create tag:', error);
			toast.error($i18n.t('태그 생성에 실패했습니다.'));
		}
		saving = false;
	};

	const resetForm = () => {
		name = '';
		isProtected = true;
	};

	$: if (!show) {
		resetForm();
	}
</script>

<Modal bind:show size="sm">
	<div class="p-5">
		<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
			{$i18n.t('새 태그 생성')}
		</h3>

		<form on:submit|preventDefault={handleSubmit} class="space-y-4">
			<div>
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
					{$i18n.t('태그 이름')}
				</label>
				<input
					type="text"
					bind:value={name}
					placeholder={$i18n.t('태그 이름을 입력하세요')}
					class="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-850 border border-gray-200 dark:border-gray-700 rounded-lg"
					autofocus
				/>
			</div>

			<div class="flex items-center justify-between">
				<div>
					<div class="text-sm font-medium text-gray-700 dark:text-gray-300">
						{$i18n.t('보호 태그')}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400">
						{$i18n.t('보호 태그는 자동 삭제되지 않습니다.')}
					</div>
				</div>
				<Switch bind:state={isProtected} />
			</div>

			<div class="flex justify-end gap-2 pt-2">
				<button
					type="button"
					on:click={() => (show = false)}
					class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
				>
					{$i18n.t('취소')}
				</button>
				<button
					type="submit"
					disabled={saving || !name.trim()}
					class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition disabled:opacity-50"
				>
					{#if saving}
						<Spinner className="w-4 h-4" />
					{:else}
						{$i18n.t('생성')}
					{/if}
				</button>
			</div>
		</form>
	</div>
</Modal>
