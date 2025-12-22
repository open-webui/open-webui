<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import Modal from '../../common/Modal.svelte';
	import XMark from '../../icons/XMark.svelte';
	import KnowledgeGroupSelector from './KnowledgeGroupSelector.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();

	interface Chapter {
		id: string;
		partId: string;
		name: string;
		description: string;
		linkedKnowledgeGroups: string[];
	}

	interface Part {
		id: string;
		name: string;
		chapters: Chapter[];
	}

	interface KnowledgeGroup {
		id: string;
		name: string;
		itemCount: number;
	}

	export let show = false;
	export let editMode = false;
	export let chapter: Chapter | null = null;
	export let partId: string | null = null;
	export let parts: Part[] = [];
	export let knowledgeGroups: KnowledgeGroup[] = [];

	let selectedPartId = '';
	let chapterName = ''; // API title
	let chapterDescription = ''; // API subtitle
	let linkedKnowledgeGroups: string[] = [];

	const handleSubmit = () => {
		dispatch('save', {
			partId: selectedPartId,
			name: chapterName,
			title: '', // not used in new schema
			description: chapterDescription,
			linkedKnowledgeGroups
		});
		resetForm();
	};

	const resetForm = () => {
		chapterName = '';
		chapterDescription = '';
		linkedKnowledgeGroups = [];
		selectedPartId = '';
	};

	const handleClose = () => {
		show = false;
		resetForm();
		dispatch('close');
	};

	$: if (show) {
		if (editMode && chapter) {
			selectedPartId = chapter.partId;
			chapterName = chapter.name || '';
			chapterDescription = chapter.description || '';
			linkedKnowledgeGroups = [...chapter.linkedKnowledgeGroups];
		} else {
			selectedPartId = partId || (parts.length > 0 ? parts[0].id : '');
			chapterName = '';
			chapterDescription = '';
			linkedKnowledgeGroups = [];
		}
	}
</script>

<Modal bind:show size="md">
	<div class="px-6 py-5">
		<!-- Header -->
		<div class="flex justify-between items-center mb-4">
			<h2 class="text-lg font-medium dark:text-white">
				{editMode ? $i18n.t('챕터 수정') : $i18n.t('새 챕터 만들기')}
			</h2>
			<button
				class="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
				on:click={handleClose}
			>
				<XMark className="size-5" />
			</button>
		</div>

		<!-- Part Selection -->
		<div class="mb-4">
			<label class="text-sm text-gray-500 mb-1.5 block">{$i18n.t('파트 선택')}</label>
			<select
				bind:value={selectedPartId}
				class="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-transparent dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 transition"
				disabled={editMode}
			>
				{#each parts as part}
					<option value={part.id}>{part.name}</option>
				{/each}
			</select>
		</div>

		<!-- Chapter Title Input -->
		<div class="mb-4">
			<label class="text-sm text-gray-500 mb-1.5 block">{$i18n.t('챕터 제목')}</label>
			<input
				type="text"
				bind:value={chapterName}
				class="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-transparent dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 transition"
				placeholder={$i18n.t('예: 1. 1계 상미분방정식 (First-Order ODEs)')}
			/>
		</div>

		<!-- Chapter Description Input -->
		<div class="mb-4">
			<label class="text-sm text-gray-500 mb-1.5 block">
				{$i18n.t('설명')}
				<span class="text-gray-400">({$i18n.t('선택사항')})</span>
			</label>
			<textarea
				bind:value={chapterDescription}
				rows="2"
				class="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl bg-transparent dark:text-white focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 transition resize-none"
				placeholder={$i18n.t('예: 1계 미분방정식의 기본 개념과 해법을 학습합니다.')}
			></textarea>
		</div>

		<!-- Knowledge Group Selection -->
		<div class="mb-5">
			<label class="text-sm text-gray-500 mb-1.5 block">
				{$i18n.t('연결된 지식 그룹')}
				<span class="text-gray-400">({$i18n.t('선택사항')})</span>
			</label>
			<KnowledgeGroupSelector
				bind:selectedGroups={linkedKnowledgeGroups}
				availableGroups={knowledgeGroups}
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
