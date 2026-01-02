<script lang="ts">
	import { createEventDispatcher, getContext, onMount, tick } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import Modal from '$lib/components/common/Modal.svelte';
	import PromptTypeSelector from './PromptTypeSelector.svelte';
	import type { PersonaPrompt, PromptType } from '$lib/apis/prompt-groups';
	import { slugify } from '$lib/utils';

	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let editMode = false;
	export let prompt: PersonaPrompt | null = null;

	let title = '';
	let command = '';
	let content = '';
	let promptType: PromptType = null;
	let personaValue: string | null = null;
	let toolDescription: string = '';
	let toolPriority: number = 0;

	let hasManualEdit = false;

	// Auto-generate command from title (only in create mode)
	$: if (!editMode && !hasManualEdit && title) {
		command = slugify(title);
	}

	const handleCommandInput = () => {
		hasManualEdit = true;
	};

	const resetForm = () => {
		title = '';
		command = '';
		content = '';
		promptType = null;
		personaValue = null;
		toolDescription = '';
		toolPriority = 0;
		hasManualEdit = false;
	};

	const populateForm = () => {
		if (prompt) {
			title = prompt.title;
			command = prompt.command.startsWith('/') ? prompt.command.slice(1) : prompt.command;
			content = prompt.content;
			promptType = prompt.prompt_type;
			personaValue = prompt.persona_value;
			toolDescription = prompt.tool_description ?? '';
			toolPriority = prompt.tool_priority ?? 0;
			hasManualEdit = true;
		}
	};

	const handleSubmit = () => {
		if (!title.trim() || !command.trim() || !content.trim()) {
			return;
		}

		// Validate tool fields when prompt_type is 'tool'
		if (promptType === 'tool' && !toolDescription.trim()) {
			return;
		}

		const promptCommand = command.startsWith('/') ? command : `/${command}`;

		const eventData: Record<string, unknown> = {
			command: promptCommand,
			title: title.trim(),
			content: content.trim(),
			prompt_type: promptType,
			persona_value: personaValue
		};

		// Include tool fields only when prompt_type is 'tool'
		if (promptType === 'tool') {
			eventData.tool_description = toolDescription.trim();
			eventData.tool_priority = toolPriority;
		}

		dispatch(editMode ? 'update' : 'create', eventData);

		resetForm();
		show = false;
	};

	const handleClose = () => {
		resetForm();
		dispatch('close');
	};

	$: if (show) {
		if (editMode && prompt) {
			populateForm();
		} else {
			resetForm();
		}
	}
</script>

<Modal bind:show size="lg" className="bg-white dark:bg-gray-900 rounded-2xl">
	<div class="p-5">
		<!-- Header -->
		<div class="flex justify-between items-center mb-4">
			<h3 class="text-lg font-semibold text-gray-900 dark:text-white">
				{editMode ? $i18n.t('프롬프트 수정') : $i18n.t('새 페르소나 프롬프트')}
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
			<!-- Title -->
			<div>
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
					{$i18n.t('제목')} <span class="text-red-500">*</span>
				</label>
				<input
					type="text"
					class="w-full px-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
					placeholder={$i18n.t('프롬프트 제목을 입력하세요')}
					bind:value={title}
					required
				/>
			</div>

			<!-- Command -->
			<div>
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
					{$i18n.t('명령어')} <span class="text-red-500">*</span>
				</label>
				<div class="flex items-center">
					<span class="px-3 py-2 text-sm bg-gray-100 dark:bg-gray-700 border border-r-0 border-gray-300 dark:border-gray-600 rounded-l-lg text-gray-500">
						/
					</span>
					<input
						type="text"
						class="flex-1 px-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-r-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
						placeholder={$i18n.t('command-name')}
						bind:value={command}
						on:input={handleCommandInput}
						disabled={editMode}
						required
					/>
				</div>
				{#if editMode}
					<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
						{$i18n.t('명령어는 수정할 수 없습니다')}
					</p>
				{/if}
			</div>

			<!-- Prompt Type -->
			<PromptTypeSelector bind:promptType bind:personaValue bind:toolDescription bind:toolPriority />

			<!-- Content -->
			<div class="flex-1 flex flex-col">
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
					{$i18n.t('프롬프트 내용')} <span class="text-red-500">*</span>
				</label>
				<textarea
					class="w-full flex-1 min-h-[200px] max-h-[400px] px-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition resize-y font-mono"
					placeholder={$i18n.t('프롬프트 내용을 입력하세요...\n\n예시:\nYou are a helpful math tutor. Help students understand mathematical concepts clearly and patiently.\n\nWhen explaining:\n- Use simple language\n- Provide step-by-step explanations\n- Give examples when helpful')}
					bind:value={content}
					rows={10}
				></textarea>
				<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t('시스템 프롬프트로 사용될 내용입니다. 마크다운 형식을 지원합니다.')}
				</p>
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
