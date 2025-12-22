<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import Modal from '../../common/Modal.svelte';
	import XMark from '../../icons/XMark.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();

	interface Part {
		id: string;
		name: string;
		chapters: any[];
	}

	export let show = false;
	export let editMode = false;
	export let part: Part | null = null;

	let partName = '';

	const handleSubmit = () => {
		if (editMode) {
			dispatch('update', { name: partName, description: '' });
		} else {
			dispatch('create', { name: partName, description: '' });
		}
		resetForm();
	};

	const resetForm = () => {
		partName = '';
	};

	const handleKeydown = (e: KeyboardEvent) => {
		if (e.key === 'Enter' && !e.shiftKey) {
			handleSubmit();
		}
	};

	const handleClose = () => {
		show = false;
		resetForm();
		dispatch('close');
	};

	// When modal opens for editing, populate the form
	$: if (show) {
		if (editMode && part) {
			partName = part.name || '';
		} else {
			resetForm();
		}
	}
</script>

<Modal bind:show size="sm">
	<div class="px-6 py-5">
		<!-- Header -->
		<div class="flex justify-between items-center mb-4">
			<h2 class="text-lg font-medium dark:text-white">
				{editMode ? $i18n.t('파트 수정') : $i18n.t('새 파트 만들기')}
			</h2>
			<button
				class="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
				on:click={handleClose}
			>
				<XMark className="size-5" />
			</button>
		</div>

		<!-- Part Name Input -->
		<div class="mb-5">
			<label class="text-sm text-gray-500 mb-1.5 block">{$i18n.t('파트 제목')}</label>
			<input
				type="text"
				bind:value={partName}
				on:keydown={handleKeydown}
				class="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-transparent dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 transition"
				placeholder={$i18n.t('예: Part A. 상미분방정식 (Ordinary Differential Equations)')}
				autofocus
			/>
		</div>

		<!-- Buttons -->
		<div class="flex gap-2 justify-end">
			<button
				class="px-4 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition text-sm font-medium dark:text-white"
				on:click={handleClose}
			>
				{$i18n.t('취소')}
			</button>
			<button
				class="px-4 py-2 bg-black dark:bg-white text-white dark:text-black hover:bg-gray-800 dark:hover:bg-gray-200 rounded-xl transition text-sm font-medium"
				on:click={handleSubmit}
			>
				{editMode ? $i18n.t('저장') : $i18n.t('만들기')}
			</button>
		</div>
	</div>
</Modal>
