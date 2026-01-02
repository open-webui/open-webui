<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { slide } from 'svelte/transition';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import { selectedTextbookSection } from '$lib/stores';

	const dispatch = createEventDispatcher();

	interface Subsection {
		id: string;
		title: string;
		subtitle: string;
	}

	interface Section {
		id: string;
		title: string;
		subsections: Subsection[];
	}

	interface TextbookData {
		title: string;
		author: string;
		edition: string;
		sections: Section[];
	}

	let textbookData: TextbookData | null = null;
	let loading = true;
	let error: string | null = null;

	onMount(async () => {
		await fetchTextbookData();
	});

	async function fetchTextbookData() {
		try {
			loading = true;
			error = null;
			const response = await fetch('/api/v1/textbook/');
			if (!response.ok) {
				throw new Error('교과서 데이터를 불러오는데 실패했습니다.');
			}
			textbookData = await response.json();

			// 데이터 로드 후 선택된 챕터가 있으면 해당 섹션 자동 확장
			expandSelectedSection();
		} catch (e) {
			error = e instanceof Error ? e.message : '알 수 없는 오류가 발생했습니다.';
		} finally {
			loading = false;
		}
	}

	// 선택된 챕터가 있으면 해당 섹션을 자동으로 확장
	function expandSelectedSection() {
		if (!textbookData || !$selectedTextbookSection?.id) return;

		for (const section of textbookData.sections) {
			const foundSubsection = section.subsections.find(
				(sub) => sub.id === $selectedTextbookSection?.id
			);
			if (foundSubsection) {
				expandedSections[section.id] = true;
				expandedSections = { ...expandedSections };
				break;
			}
		}
	}

	// selectedTextbookSection 변경 감지
	$: if ($selectedTextbookSection?.id && textbookData) {
		expandSelectedSection();
	}

	// State for expanded sections
	let expandedSections: Record<string, boolean> = {};

	const toggleSection = (sectionId) => {
		expandedSections[sectionId] = !expandedSections[sectionId];
		expandedSections = { ...expandedSections };
	};

	const selectSubsection = (subsection) => {
		// Toggle: if already selected, deselect it
		if ($selectedTextbookSection?.id === subsection.id) {
			dispatch('section-clear');
		} else {
			dispatch('subsection-select', {
				id: subsection.id,
				title: subsection.title,
				subtitle: subsection.subtitle
			});
		}
	};

	const clearSection = () => {
		dispatch('section-clear');
	};
</script>

<div class="px-5 mt-5">
	<!-- Content -->
	<div class="flex flex-col gap-3">
		{#if loading}
			<div class="px-5 py-4 text-center text-body-4 text-gray-500 dark:text-gray-400">
				불러오는 중...
			</div>
		{:else if error}
			<div class="px-5 py-4 text-center text-body-4 text-red-500">
				{error}
			</div>
		{:else if textbookData}
			<!-- Textbook Card - Click to clear chapter selection -->
			<button
				class="flex flex-col items-start p-4 px-5 gap-1 w-full
					bg-white/70 dark:bg-gray-900/50
					shadow-[4px_4px_20px_rgba(0,0,0,0.1)]
					backdrop-blur-[20px]
					rounded-[20px]
					hover:bg-white/85 dark:hover:bg-gray-900/70
					transition cursor-pointer text-left"
				on:click={clearSection}
			>
				<div class="w-full text-body-4 text-gray-950 dark:text-white">{textbookData.title}</div>
				<div class="flex flex-col gap-1 w-full">
					<div class="text-caption text-gray-700 dark:text-gray-300">저자: {textbookData.author}</div>
					<div class="text-caption text-gray-700 dark:text-gray-300">판: {textbookData.edition}</div>
				</div>
			</button>

			<!-- Sections (Dropdowns) -->
			<div class="flex flex-col gap-3">
				{#each textbookData.sections as section}
					<div class="flex flex-col gap-2">
						<!-- Section Dropdown Button -->
						<button
							class="w-full flex items-center justify-between px-4 py-2 gap-2 h-9
								bg-white/50 dark:bg-gray-900/20
								shadow-[4px_4px_20px_rgba(0,0,0,0.1),inset_2px_2px_10px_rgba(255,255,255,0.05),inset_2px_2px_16px_rgba(206,212,229,0.12)]
								backdrop-blur-sm
								rounded-full
								hover:bg-white/60 dark:hover:bg-gray-900/30
								transition text-left"
							on:click={() => toggleSection(section.id)}
						>
							<span class="text-caption text-gray-950 dark:text-white flex-1 truncate">{section.title}</span>
							<ChevronDown
								className="size-5 flex-shrink-0 transition-transform duration-200 text-gray-950 dark:text-white {expandedSections[section.id]
									? 'rotate-180'
									: ''}"
								strokeWidth="1.5"
							/>
						</button>

						<!-- Subsections List -->
						{#if expandedSections[section.id]}
							<div class="w-full flex flex-col items-start gap-2 rounded-lg" transition:slide={{ duration: 200 }}>
								{#each section.subsections as subsection}
									<button
										class="w-full flex items-center px-1 py-0.5 rounded-xl
											transition text-left
											{$selectedTextbookSection?.id === subsection.id
												? 'bg-gray-200/20 dark:bg-gray-600/30'
												: 'hover:bg-gray-200/20 dark:hover:bg-gray-600/30'}"
										on:click={() => selectSubsection(subsection)}
									>
										<span class="text-body-4 flex-1 truncate
											{$selectedTextbookSection?.id === subsection.id
												? 'text-gray-950 dark:text-white'
												: 'text-gray-500 dark:text-gray-600 hover:text-gray-950 dark:hover:text-white'}">{subsection.title}</span>
									</button>
								{/each}
							</div>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
