<script lang="ts">
	export let title = '제10장. 벡터 적분법, 적분 정리 (Vector Integral Calculus. Integral Theorems)';
	export let subtitle = '벡터장을 다양한 경로와 곡면에 대해 적분하고, 미분과 적분을 연결하는 중요한 정리들을 이해합니다.';
	export let proficiencyLevel = 'intermediate';
	export let responseStyle = 'question_guidance';
	export let hasChapter = false;

	let showProficiencyDropdown = false;
	let showResponseStyleDropdown = false;

	const proficiencyLevels = {
		initial: '초급',
		intermediate: '중급',
		advanced: '고급'
	};

	const responseStyles = {
		question_guidance: '질문식 유도',
		problem_bank: '문제 은행',
		detailed_lecture: '자세한 강의'
	};

	const setProficiencyLevel = (level) => {
		proficiencyLevel = level;
		showProficiencyDropdown = false;
	};

	const setResponseStyle = (style) => {
		responseStyle = style;
		showResponseStyleDropdown = false;
	};

	// Reusable glass dropdown styles
	const glassDropdownBtn = `flex flex-row items-center gap-2 px-4 py-2 h-9 rounded-full cursor-pointer
		bg-[rgba(253,254,254,0.5)] dark:bg-[rgba(39,40,44,0.2)]
		shadow-[4px_4px_20px_rgba(0,0,0,0.1),inset_2px_2px_16px_rgba(206,212,229,0.1)]
		dark:shadow-[4px_4px_20px_rgba(0,0,0,0.1),inset_2px_2px_6px_rgba(206,212,229,0.2),inset_6px_6px_25px_rgba(206,212,229,0.15)]
		backdrop-blur-[10px] transition-all duration-300
		hover:bg-[rgba(253,254,254,0.6)] dark:hover:bg-[rgba(39,40,44,0.25)]
		hover:shadow-[6px_6px_24px_rgba(0,0,0,0.15),inset_2px_2px_16px_rgba(206,212,229,0.15)]
		dark:hover:shadow-[6px_6px_24px_rgba(0,0,0,0.15),inset_2px_2px_6px_rgba(206,212,229,0.25),inset_6px_6px_25px_rgba(206,212,229,0.2)]`;

	const glassDropdownMenu = `absolute flex flex-col items-start w-full z-50 rounded-[20px]
		bg-[rgba(253,254,254,0.7)] dark:bg-[rgba(39,40,44,0.5)]
		shadow-[4px_4px_20px_rgba(0,0,0,0.1)] backdrop-blur-[20px] text-caption`;

	const glassDropdownOption = `flex flex-row items-center w-full px-4 py-2 rounded-xl cursor-pointer text-left transition-all duration-200
		text-[#596172] dark:text-[#B4BCD0]
		hover:bg-[rgba(206,212,229,0.2)] hover:text-[#1A1B1C]
		dark:hover:bg-[rgba(206,212,229,0.1)] dark:hover:text-[#FDFEFE]`;

	const glassDropdownOptionActive = `bg-[rgba(206,212,229,0.25)] text-[#1A1B1C] font-medium dark:bg-[rgba(206,212,229,0.15)] dark:text-[#FDFEFE]`;

	const glassDropdownText = `text-caption text-[#1A1B1C] dark:text-[#FDFEFE]`;

	const glassDropdownIcon = (isOpen) =>
		`w-4 h-4 transition-transform duration-200 text-[#1A1B1C] dark:text-[#FDFEFE] ${isOpen ? 'rotate-180' : ''}`;
</script>

<div class="w-full px-12 py-12 flex justify-between items-center border-b border-gray-200 dark:border-gray-950 bg-gray-200/50 dark:bg-gray-900/50 backdrop-blur-xl">
	<!-- Title and Subtitle Section (Left) -->
	<div class="flex flex-col justify-start gap-1 flex-1 overflow-hidden">
		{#if hasChapter}
			<h2 class="font-semibold text-gray-900 dark:text-gray-100 leading-none text-title-4 mb-3 truncate">{title}</h2>
			<p class="text-gray-800 dark:text-gray-400 text-caption truncate">{subtitle}</p>
		{:else}
			<p class="text-gray-500 dark:text-gray-500 text-caption">사이드바에서 학습할 챕터를 선택해주세요</p>
		{/if}
	</div>


</div>

<style>
</style>
