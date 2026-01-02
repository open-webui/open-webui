<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';

	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { renameTag, type TagDefinition } from '$lib/apis/message-tags';

	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let tag: TagDefinition | null = null;

	let newName = '';
	let saving = false;

	const handleSubmit = async () => {
		if (!tag || !newName.trim()) {
			toast.error($i18n.t('새 이름을 입력해주세요.'));
			return;
		}

		if (newName.trim() === tag.name) {
			toast.error($i18n.t('새 이름이 기존 이름과 같습니다.'));
			return;
		}

		saving = true;
		try {
			const result = await renameTag(localStorage.token, tag.id, newName.trim());
			if (result) {
				dispatch('renamed', result);
				toast.success($i18n.t('태그 이름이 변경되었습니다.'));
			}
		} catch (error) {
			console.error('Failed to rename tag:', error);
			toast.error($i18n.t('태그 이름 변경에 실패했습니다.'));
		}
		saving = false;
	};

	$: if (tag && show) {
		newName = tag.name;
	}

	$: if (!show) {
		newName = '';
	}
</script>

<Modal bind:show size="sm">
	<div class="p-5">
		<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
			{$i18n.t('태그 이름 변경')}
		</h3>

		{#if tag}
			<form on:submit|preventDefault={handleSubmit} class="space-y-4">
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
						{$i18n.t('현재 이름')}
					</label>
					<div class="px-3 py-2 text-sm bg-gray-100 dark:bg-gray-800 rounded-lg text-gray-600 dark:text-gray-400">
						{tag.name}
					</div>
				</div>

				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
						{$i18n.t('새 이름')}
					</label>
					<input
						type="text"
						bind:value={newName}
						placeholder={$i18n.t('새 태그 이름을 입력하세요')}
						class="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-850 border border-gray-200 dark:border-gray-700 rounded-lg"
						autofocus
					/>
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
						disabled={saving || !newName.trim() || newName.trim() === tag.name}
						class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition disabled:opacity-50"
					>
						{#if saving}
							<Spinner className="w-4 h-4" />
						{:else}
							{$i18n.t('변경')}
						{/if}
					</button>
				</div>
			</form>
		{/if}
	</div>
</Modal>
