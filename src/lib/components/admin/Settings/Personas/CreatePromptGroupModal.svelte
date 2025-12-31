<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import Modal from '$lib/components/common/Modal.svelte';
	import type { PromptGroup } from '$lib/apis/prompt-groups';

	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let editMode = false;
	export let group: PromptGroup | null = null;

	let name = '';
	let description = '';

	const resetForm = () => {
		name = '';
		description = '';
	};

	const populateForm = () => {
		if (group) {
			name = group.name;
			description = group.description || '';
		}
	};

	const handleSubmit = () => {
		if (!name.trim()) {
			return;
		}

		dispatch(editMode ? 'update' : 'create', {
			name: name.trim(),
			description: description.trim() || undefined
		});

		resetForm();
		show = false;
	};

	const handleClose = () => {
		resetForm();
		dispatch('close');
	};

	$: if (show) {
		if (editMode && group) {
			populateForm();
		} else {
			resetForm();
		}
	}
</script>

<Modal bind:show size="sm" className="bg-white dark:bg-gray-900 rounded-2xl">
	<div class="p-5">
		<!-- Header -->
		<div class="flex justify-between items-center mb-4">
			<h3 class="text-lg font-semibold text-gray-900 dark:text-white">
				{editMode ? $i18n.t('그룹 수정') : $i18n.t('새 프롬프트 그룹')}
			</h3>
			<button
				type="button"
				class="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
				on:click={handleClose}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="2"
					stroke="currentColor"
					class="size-5"
				>
					<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
				</svg>
			</button>
		</div>

		<!-- Form -->
		<form
			on:submit|preventDefault={handleSubmit}
			class="flex flex-col gap-4"
		>
			<!-- Name -->
			<div>
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
					{$i18n.t('그룹 이름')} <span class="text-red-500">*</span>
				</label>
				<input
					type="text"
					class="w-full px-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
					placeholder={$i18n.t('그룹 이름을 입력하세요')}
					bind:value={name}
					required
				/>
			</div>

			<!-- Description -->
			<div>
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
					{$i18n.t('설명')} <span class="text-gray-400">({$i18n.t('선택')})</span>
				</label>
				<textarea
					class="w-full px-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition resize-none"
					placeholder={$i18n.t('그룹에 대한 설명을 입력하세요')}
					bind:value={description}
					rows={3}
				/>
			</div>

			<!-- Actions -->
			<div class="flex justify-end gap-2 pt-2">
				<button
					type="button"
					class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
					on:click={handleClose}
				>
					{$i18n.t('취소')}
				</button>
				<button
					type="submit"
					class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition"
				>
					{editMode ? $i18n.t('저장') : $i18n.t('생성')}
				</button>
			</div>
		</form>
	</div>
</Modal>
