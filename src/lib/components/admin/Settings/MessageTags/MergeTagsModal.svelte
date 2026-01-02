<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';

	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { mergeTags, type TagDefinition } from '$lib/apis/message-tags';

	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let tags: TagDefinition[] = [];

	let keepTagId = '';
	let selectedMergeTagIds: string[] = [];
	let saving = false;

	// Available tags for merging (excluding the keep tag)
	$: availableMergeTags = tags.filter((t) => t.id !== keepTagId);

	const handleToggleMergeTag = (tagId: string) => {
		if (selectedMergeTagIds.includes(tagId)) {
			selectedMergeTagIds = selectedMergeTagIds.filter((id) => id !== tagId);
		} else {
			selectedMergeTagIds = [...selectedMergeTagIds, tagId];
		}
	};

	const handleSubmit = async () => {
		if (!keepTagId) {
			toast.error($i18n.t('유지할 태그를 선택해주세요.'));
			return;
		}

		if (selectedMergeTagIds.length === 0) {
			toast.error($i18n.t('병합할 태그를 최소 1개 이상 선택해주세요.'));
			return;
		}

		saving = true;
		try {
			const result = await mergeTags(localStorage.token, keepTagId, selectedMergeTagIds);
			if (result?.success) {
				dispatch('merged', result);
				toast.success($i18n.t(`${result.merged_count}개의 태그가 병합되었습니다.`));
				resetForm();
			}
		} catch (error) {
			console.error('Failed to merge tags:', error);
			toast.error($i18n.t('태그 병합에 실패했습니다.'));
		}
		saving = false;
	};

	const resetForm = () => {
		keepTagId = '';
		selectedMergeTagIds = [];
	};

	$: if (!show) {
		resetForm();
	}
</script>

<Modal bind:show size="md">
	<div class="p-5">
		<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">
			{$i18n.t('태그 병합')}
		</h3>
		<p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
			{$i18n.t('여러 태그를 하나로 병합합니다. 선택된 태그들의 모든 메시지 태그가 유지할 태그로 이동됩니다.')}
		</p>

		<form on:submit|preventDefault={handleSubmit} class="space-y-4">
			<!-- Keep Tag Selection -->
			<div>
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					{$i18n.t('유지할 태그')}
				</label>
				<select
					bind:value={keepTagId}
					class="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-850 border border-gray-200 dark:border-gray-700 rounded-lg"
				>
					<option value="">{$i18n.t('태그 선택...')}</option>
					{#each tags as tag (tag.id)}
						<option value={tag.id}>
							{tag.name} ({tag.usage_count}회 사용)
						</option>
					{/each}
				</select>
			</div>

			<!-- Merge Tags Selection -->
			{#if keepTagId}
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						{$i18n.t('병합할 태그 선택')}
					</label>
					<div class="max-h-60 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-lg">
						{#each availableMergeTags as tag (tag.id)}
							<label
								class="flex items-center gap-3 px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-850 cursor-pointer border-b border-gray-100 dark:border-gray-800 last:border-b-0"
							>
								<input
									type="checkbox"
									checked={selectedMergeTagIds.includes(tag.id)}
									on:change={() => handleToggleMergeTag(tag.id)}
									class="w-4 h-4 text-blue-600 rounded border-gray-300 dark:border-gray-600"
								/>
								<div class="flex-1 min-w-0">
									<div class="text-sm text-gray-900 dark:text-white truncate">
										{tag.name}
									</div>
									<div class="text-xs text-gray-500 dark:text-gray-400">
										{tag.usage_count}회 사용
										{#if tag.is_protected}
											<span class="ml-1 text-blue-500">(보호됨)</span>
										{/if}
									</div>
								</div>
							</label>
						{:else}
							<div class="px-3 py-4 text-center text-sm text-gray-500 dark:text-gray-400">
								{$i18n.t('병합 가능한 태그가 없습니다.')}
							</div>
						{/each}
					</div>
					{#if selectedMergeTagIds.length > 0}
						<div class="mt-2 text-sm text-gray-600 dark:text-gray-400">
							{$i18n.t(`${selectedMergeTagIds.length}개 태그 선택됨`)}
						</div>
					{/if}
				</div>
			{/if}

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
					disabled={saving || !keepTagId || selectedMergeTagIds.length === 0}
					class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition disabled:opacity-50"
				>
					{#if saving}
						<Spinner className="w-4 h-4" />
					{:else}
						{$i18n.t('병합')}
					{/if}
				</button>
			</div>
		</form>
	</div>
</Modal>
