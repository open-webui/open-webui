<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { getAvailablePersonas } from '$lib/apis/prompt-groups';
	import type { AvailablePersonas, PersonaOption } from '$lib/apis/prompt-groups';

	const i18n: Writable<i18nType> = getContext('i18n');

	export let promptType: 'base' | 'proficiency' | 'style' | null = null;
	export let personaValue: string | null = null;

	// 동적 페르소나 옵션
	let availablePersonas: AvailablePersonas | null = null;
	let personasLoading = false;

	// 새 값 추가 모드
	let isAddingNewProficiency = false;
	let isAddingNewStyle = false;
	let newProficiencyValue = '';
	let newStyleValue = '';

	// 라벨 헬퍼 함수
	const getPersonaLabel = (option: PersonaOption): string => {
		return option.prompts[0]?.title ?? option.value;
	};

	// 페르소나 로드
	const loadPersonas = async () => {
		personasLoading = true;
		try {
			availablePersonas = await getAvailablePersonas(localStorage.token);
		} catch (e) {
			console.error('Failed to load personas:', e);
		}
		personasLoading = false;
	};

	onMount(() => {
		loadPersonas();
	});

	// Reset persona value when type changes
	$: if (promptType !== 'proficiency' && promptType !== 'style') {
		personaValue = null;
		isAddingNewProficiency = false;
		isAddingNewStyle = false;
	}

	// 새 값 추가 처리
	const handleProficiencySelectChange = (e: Event) => {
		const value = (e.target as HTMLSelectElement).value;
		if (value === '__new__') {
			isAddingNewProficiency = true;
			personaValue = null;
		} else {
			isAddingNewProficiency = false;
			personaValue = value || null;
		}
	};

	const handleStyleSelectChange = (e: Event) => {
		const value = (e.target as HTMLSelectElement).value;
		if (value === '__new__') {
			isAddingNewStyle = true;
			personaValue = null;
		} else {
			isAddingNewStyle = false;
			personaValue = value || null;
		}
	};

	const applyNewProficiencyValue = () => {
		if (newProficiencyValue.trim()) {
			personaValue = newProficiencyValue.trim();
			isAddingNewProficiency = false;
			newProficiencyValue = '';
		}
	};

	const applyNewStyleValue = () => {
		if (newStyleValue.trim()) {
			personaValue = newStyleValue.trim();
			isAddingNewStyle = false;
			newStyleValue = '';
		}
	};

	const cancelNewValue = (type: 'proficiency' | 'style') => {
		if (type === 'proficiency') {
			isAddingNewProficiency = false;
			newProficiencyValue = '';
		} else {
			isAddingNewStyle = false;
			newStyleValue = '';
		}
	};
</script>

<div class="flex flex-col gap-3">
	<!-- Prompt Type Selection -->
	<div>
		<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
			{$i18n.t('프롬프트 타입')}
		</label>
		<select
			class="w-full px-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
			bind:value={promptType}
		>
			<option value={null}>{$i18n.t('일반 (타입 없음)')}</option>
			<option value="base">{$i18n.t('기본 (base)')}</option>
			<option value="proficiency">{$i18n.t('난이도 (proficiency)')}</option>
			<option value="style">{$i18n.t('스타일 (style)')}</option>
		</select>
		<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
			{#if promptType === 'base'}
				{$i18n.t('모든 페르소나에 공통으로 적용되는 기본 프롬프트')}
			{:else if promptType === 'proficiency'}
				{$i18n.t('학생 숙련도에 따라 선택되는 프롬프트')}
			{:else if promptType === 'style'}
				{$i18n.t('응답 스타일에 따라 선택되는 프롬프트')}
			{:else}
				{$i18n.t('페르소나와 무관한 일반 프롬프트 (채팅에서 /명령어로 사용)')}
			{/if}
		</p>
	</div>

	<!-- Persona Value Selection (conditional) -->
	{#if promptType === 'proficiency'}
		<div>
			<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
				{$i18n.t('숙련도 레벨')}
			</label>

			{#if isAddingNewProficiency}
				<!-- 새 값 입력 모드 -->
				<div class="flex gap-2">
					<input
						type="text"
						class="flex-1 px-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
						placeholder={$i18n.t('새 숙련도 값 입력 (예: 4)')}
						bind:value={newProficiencyValue}
						on:keydown={(e) => e.key === 'Enter' && applyNewProficiencyValue()}
					/>
					<button
						type="button"
						class="px-3 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition"
						on:click={applyNewProficiencyValue}
					>
						{$i18n.t('적용')}
					</button>
					<button
						type="button"
						class="px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition"
						on:click={() => cancelNewValue('proficiency')}
					>
						{$i18n.t('취소')}
					</button>
				</div>
			{:else}
				<!-- 선택 드롭다운 -->
				<select
					class="w-full px-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
					value={personaValue ?? ''}
					on:change={handleProficiencySelectChange}
				>
					<option value="">{$i18n.t('선택하세요')}</option>
					{#if personasLoading}
						<option disabled>{$i18n.t('로딩 중...')}</option>
					{:else if availablePersonas}
						{#each availablePersonas.proficiency_levels as option}
							<option value={option.value}>{getPersonaLabel(option)}</option>
						{/each}
					{/if}
					<option value="__new__" class="text-blue-600">+ {$i18n.t('새 값 추가...')}</option>
				</select>

				{#if personaValue && availablePersonas && !availablePersonas.proficiency_levels.find(p => p.value === personaValue)}
					<p class="mt-1 text-xs text-blue-600 dark:text-blue-400">
						{$i18n.t('새 값')}: {personaValue}
					</p>
				{/if}
			{/if}
		</div>
	{:else if promptType === 'style'}
		<div>
			<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
				{$i18n.t('응답 스타일')}
			</label>

			{#if isAddingNewStyle}
				<!-- 새 값 입력 모드 -->
				<div class="flex gap-2">
					<input
						type="text"
						class="flex-1 px-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
						placeholder={$i18n.t('새 스타일 값 입력 (예: detailed)')}
						bind:value={newStyleValue}
						on:keydown={(e) => e.key === 'Enter' && applyNewStyleValue()}
					/>
					<button
						type="button"
						class="px-3 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition"
						on:click={applyNewStyleValue}
					>
						{$i18n.t('적용')}
					</button>
					<button
						type="button"
						class="px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition"
						on:click={() => cancelNewValue('style')}
					>
						{$i18n.t('취소')}
					</button>
				</div>
			{:else}
				<!-- 선택 드롭다운 -->
				<select
					class="w-full px-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
					value={personaValue ?? ''}
					on:change={handleStyleSelectChange}
				>
					<option value="">{$i18n.t('선택하세요')}</option>
					{#if personasLoading}
						<option disabled>{$i18n.t('로딩 중...')}</option>
					{:else if availablePersonas}
						{#each availablePersonas.response_styles as option}
							<option value={option.value}>{getPersonaLabel(option)}</option>
						{/each}
					{/if}
					<option value="__new__" class="text-blue-600">+ {$i18n.t('새 값 추가...')}</option>
				</select>

				{#if personaValue && availablePersonas && !availablePersonas.response_styles.find(s => s.value === personaValue)}
					<p class="mt-1 text-xs text-blue-600 dark:text-blue-400">
						{$i18n.t('새 값')}: {personaValue}
					</p>
				{/if}
			{/if}
		</div>
	{/if}
</div>
