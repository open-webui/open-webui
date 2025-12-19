<script lang="ts">
	import { slide } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	export let title = '';
	export let subtitle = '';
	export let proficiencyLevel = 'intermediate';
	export let responseStyle = 'question_guidance';
	export let hasChapter = false;

	let isExpanded = false;
	let showProficiencyDropdown = false;
	let showResponseStyleDropdown = false;
	let containerElement: HTMLDivElement;

	const proficiencyLevels: Record<string, string> = {
		initial: '초급',
		intermediate: '중급',
		advanced: '고급'
	};

	const responseStyles: Record<string, string> = {
		question_guidance: '질문식 유도',
		problem_bank: '문제 은행',
		detailed_lecture: '자세한 강의'
	};

	const setProficiencyLevel = (level: string) => {
		proficiencyLevel = level;
		showProficiencyDropdown = false;
	};

	const setResponseStyle = (style: string) => {
		responseStyle = style;
		showResponseStyleDropdown = false;
	};

	const toggleExpanded = () => {
		isExpanded = !isExpanded;
		if (!isExpanded) {
			showProficiencyDropdown = false;
			showResponseStyleDropdown = false;
		}
	};

	const handleClickOutside = (event: MouseEvent) => {
		if (containerElement && !containerElement.contains(event.target as Node)) {
			isExpanded = false;
			showProficiencyDropdown = false;
			showResponseStyleDropdown = false;
		}
	};

	// Glass dropdown styles (from ChatToolbar)
	const glassDropdownBtn = `flex flex-row items-center justify-between gap-2 px-4 py-2 h-9 rounded-full cursor-pointer
		bg-white/50 dark:bg-gray-900/20
		shadow-lg backdrop-blur-md transition-all duration-300
		hover:bg-white/60 dark:hover:bg-gray-900/25`;

	const glassDropdownMenu = `absolute top-full mt-1 flex flex-col items-start w-full z-50 rounded-2xl
		bg-white/90 dark:bg-gray-900/70
		shadow-lg backdrop-blur-xl text-caption overflow-hidden`;

	const glassDropdownOption = `flex flex-row items-center w-full px-4 py-2.5 cursor-pointer text-left transition-all duration-200
		text-gray-700 dark:text-gray-300
		hover:bg-gray-200/20 hover:text-gray-950
		dark:hover:bg-gray-200/10 dark:hover:text-white`;

	const glassDropdownOptionActive = `bg-gray-200/25 text-gray-950 font-medium dark:bg-gray-200/15 dark:text-white`;

	const glassDropdownText = `text-caption text-gray-950 dark:text-white`;

	const glassDropdownIcon = (isOpen: boolean) =>
		`w-5 h-5 transition-transform duration-200 text-gray-950 dark:text-white ${isOpen ? 'rotate-180' : ''}`;
</script>

<svelte:window on:click={handleClickOutside} />

<div class="relative z-20 mt-16 " bind:this={containerElement}>
	<!-- FilterGroup Container -->
	<div
		class="flex flex-row justify-between items-center
			
			backdrop-blur-xl px-4 gap-3
			scrollbar-hidden"
	>
		<!-- Dropdown Trigger -->
		<button
			on:click|stopPropagation={toggleExpanded}
			class="flex flex-row flex-1 min-w-0 items-center gap-2 px-4 h-9 rounded-full cursor-pointer
				bg-white/50 dark:bg-gray-900/20
				shadow-lg backdrop-blur-xl transition-all duration-300 overflow-hidden"
		>
			<p class="flex-1 min-w-0 text-caption text-gray-950 dark:text-white truncate text-left">
				{hasChapter ? title : '사이드바에서 학습할 챕터를 선택해주세요'}
			</p>
			<svg
				class={glassDropdownIcon(isExpanded)}
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path
					d="M9.99595 12.75C9.89595 12.75 9.8022 12.7326 9.7147 12.6979C9.6272 12.6632 9.54873 12.6111 9.47928 12.5416L5.52803 8.59038C5.37053 8.43288 5.29525 8.25343 5.3022 8.05204C5.30914 7.85065 5.389 7.67357 5.54178 7.52079C5.69456 7.36801 5.87164 7.29163 6.07303 7.29163C6.27442 7.29163 6.4515 7.36801 6.60428 7.52079L10.0001 10.9375L13.4168 7.52079C13.5696 7.36801 13.7466 7.2951 13.948 7.30204C14.1494 7.30899 14.3265 7.38885 14.4793 7.54163C14.6321 7.6944 14.7084 7.87149 14.7084 8.07288C14.7084 8.27426 14.6297 8.45329 14.4722 8.60996L10.5209 12.5416C10.4459 12.6111 10.3647 12.6632 10.2772 12.6979C10.1897 12.7326 10.0959 12.75 9.99595 12.75Z"
					fill="currentColor"
				/>
			</svg>
		</button>

		<!-- Info Button -->
		{#if hasChapter}
			<Tooltip content={subtitle} placement="bottom">
				<button
					class="flex items-center justify-center w-9 h-9 rounded-full
						bg-white dark:bg-gray-900/40
						shadow-lg backdrop-blur-md transition-all duration-300
						hover:bg-gray-100 dark:hover:bg-gray-900/50"
				>
					<svg
						class="w-5 h-5 text-gray-950 dark:text-white"
						fill="currentColor"
						viewBox="0 0 20 20"
					>
						<path
							fill-rule="evenodd"
							d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
							clip-rule="evenodd"
						/>
					</svg>
				</button>
			</Tooltip>
		{/if}
	</div>

	<!-- Expanded Panel -->
	{#if isExpanded}
		<div
			class="absolute left-0 right-0 z-40 px-4 py-4
				bg-white/50 dark:bg-gray-950/50
				backdrop-blur-xl border-b border-gray-200/50 dark:border-gray-800/50
				shadow-lg rounded-2xl mt-2 mx-2"
			transition:slide={{ duration: 200, easing: quintOut }}
			on:click|stopPropagation
		>
			<!-- Chapter Info -->
			{#if hasChapter}
				<div class="mb-4">
					<h3 class="font-semibold text-gray-950 dark:text-white text-body-4 mb-1 line-clamp-2">
						{title}
					</h3>
					<p class="text-gray-700 dark:text-gray-300 text-caption line-clamp-2">
						{subtitle}
					</p>
				</div>
			{/if}

			<!-- Dropdowns Row -->
			<div class="flex flex-row gap-3">
				<!-- Proficiency Level Dropdown -->
				<div class="flex-1">
					<span class="block text-caption text-gray-700 dark:text-gray-300 mb-1.5">수준</span>
					<div class="relative">
						<button
							on:click|stopPropagation={() => {
								showProficiencyDropdown = !showProficiencyDropdown;
								showResponseStyleDropdown = false;
							}}
							class="{glassDropdownBtn} w-full"
						>
							<span class={glassDropdownText}>{proficiencyLevels[proficiencyLevel]}</span>
							<svg
								class={glassDropdownIcon(showProficiencyDropdown)}
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									d="M9.99595 12.75C9.89595 12.75 9.8022 12.7326 9.7147 12.6979C9.6272 12.6632 9.54873 12.6111 9.47928 12.5416L5.52803 8.59038C5.37053 8.43288 5.29525 8.25343 5.3022 8.05204C5.30914 7.85065 5.389 7.67357 5.54178 7.52079C5.69456 7.36801 5.87164 7.29163 6.07303 7.29163C6.27442 7.29163 6.4515 7.36801 6.60428 7.52079L10.0001 10.9375L13.4168 7.52079C13.5696 7.36801 13.7466 7.2951 13.948 7.30204C14.1494 7.30899 14.3265 7.38885 14.4793 7.54163C14.6321 7.6944 14.7084 7.87149 14.7084 8.07288C14.7084 8.27426 14.6297 8.45329 14.4722 8.60996L10.5209 12.5416C10.4459 12.6111 10.3647 12.6632 10.2772 12.6979C10.1897 12.7326 10.0959 12.75 9.99595 12.75Z"
									fill="currentColor"
								/>
							</svg>
						</button>

						{#if showProficiencyDropdown}
							<div class={glassDropdownMenu} transition:slide={{ duration: 150 }}>
								{#each Object.entries(proficiencyLevels) as [key, label]}
									<button
										on:click|stopPropagation={() => setProficiencyLevel(key)}
										class="{glassDropdownOption} {proficiencyLevel === key
											? glassDropdownOptionActive
											: ''}"
									>
										{label}
									</button>
								{/each}
							</div>
						{/if}
					</div>
				</div>

				<!-- Response Style Dropdown -->
				<div class="flex-1">
					<span class="block text-caption text-gray-700 dark:text-gray-300 mb-1.5"
						>응답 스타일</span
					>
					<div class="relative">
						<button
							on:click|stopPropagation={() => {
								showResponseStyleDropdown = !showResponseStyleDropdown;
								showProficiencyDropdown = false;
							}}
							class="{glassDropdownBtn} w-full"
						>
							<span class={glassDropdownText}>{responseStyles[responseStyle]}</span>
							<svg
								class={glassDropdownIcon(showResponseStyleDropdown)}
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									d="M9.99595 12.75C9.89595 12.75 9.8022 12.7326 9.7147 12.6979C9.6272 12.6632 9.54873 12.6111 9.47928 12.5416L5.52803 8.59038C5.37053 8.43288 5.29525 8.25343 5.3022 8.05204C5.30914 7.85065 5.389 7.67357 5.54178 7.52079C5.69456 7.36801 5.87164 7.29163 6.07303 7.29163C6.27442 7.29163 6.4515 7.36801 6.60428 7.52079L10.0001 10.9375L13.4168 7.52079C13.5696 7.36801 13.7466 7.2951 13.948 7.30204C14.1494 7.30899 14.3265 7.38885 14.4793 7.54163C14.6321 7.6944 14.7084 7.87149 14.7084 8.07288C14.7084 8.27426 14.6297 8.45329 14.4722 8.60996L10.5209 12.5416C10.4459 12.6111 10.3647 12.6632 10.2772 12.6979C10.1897 12.7326 10.0959 12.75 9.99595 12.75Z"
									fill="currentColor"
								/>
							</svg>
						</button>

						{#if showResponseStyleDropdown}
							<div class={glassDropdownMenu} transition:slide={{ duration: 150 }}>
								{#each Object.entries(responseStyles) as [key, label]}
									<button
										on:click|stopPropagation={() => setResponseStyle(key)}
										class="{glassDropdownOption} {responseStyle === key
											? glassDropdownOptionActive
											: ''}"
									>
										{label}
									</button>
								{/each}
							</div>
						{/if}
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>
