<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { slide } from 'svelte/transition';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

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
		} catch (e) {
			error = e instanceof Error ? e.message : '알 수 없는 오류가 발생했습니다.';
		} finally {
			loading = false;
		}
	}

	// State for expanded sections
	let expandedSections: Record<string, boolean> = {};

	const toggleSection = (sectionId) => {
		expandedSections[sectionId] = !expandedSections[sectionId];
		expandedSections = { ...expandedSections };
	};

	const selectSubsection = (subsection) => {
		dispatch('subsection-select', {
			id: subsection.id,
			title: subsection.title,
			subtitle: subsection.subtitle
		});
	};

	const clearSection = () => {
		dispatch('section-clear');
	};
</script>

<div class="px-2 mt-0.5">
	<!-- Header -->
	<div class="flex items-center justify-between py-2 px-2">
		<div class="flex items-center gap-2 text-gray-900 dark:text-gray-50">
			<div class="">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1.5"
					stroke="currentColor"
					class="size-4.5"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25"
					/>
				</svg>
			</div>
			<div class="text-sm font-medium ">교재 정보</div>
		</div>
	</div>

	<!-- Content -->
	<div class="flex flex-col gap-2 mt-2">
		{#if loading}
			<div class="mx-2 px-5 py-4 text-center text-sm text-gray-500 dark:text-gray-400">
				불러오는 중...
			</div>
		{:else if error}
			<div class="mx-2 px-5 py-4 text-center text-sm text-red-500">
				{error}
			</div>
		{:else if textbookData}
			<!-- Textbook Card - Click to clear chapter selection -->
			<button
				class="mx-2 px-5 py-4 rounded-2xl
					bg-white/70 dark:bg-white/5
					border border-gray-200/30 dark:border-gray-200/20
					shadow-[0.25rem_0.25rem_1.25rem_rgba(0,0,0,0.1)] dark:shadow-[0.25rem_0.25rem_1.25rem_rgba(0,0,0,0.2)]
					backdrop-blur-lg
					hover:bg-white/85 dark:hover:bg-white/10
					transition cursor-pointer text-left flex-1"
				on:click={clearSection}
			>
				<div class="w-56 text-sm font-normal text-gray-950 dark:text-white mb-1">{textbookData.title}</div>
				<div class="flex flex-col gap-1 w-56">
					<div class="text-xs font-normal text-gray-700 dark:text-gray-400">저자: {textbookData.author}</div>
					<div class="text-xs font-normal text-gray-700 dark:text-gray-400">판: {textbookData.edition}</div>
				</div>
			</button>

			<!-- Sections -->
			{#each textbookData.sections as section}
				<div class="mx-2">
					<div class="{expandedSections[section.id] ? 'bg-white/50 dark:bg-white/5 shadow-[0.25rem_0.25rem_1.25rem_rgba(0,0,0,0.1),inset_0.125rem_0.125rem_1rem_rgba(206,212,229,0.1)] dark:shadow-[0.25rem_0.25rem_1.25rem_rgba(0,0,0,0.2)] backdrop-blur-md border border-gray-200/30 dark:border-gray-200/20 rounded-2xl' : ''}">
						<!-- Section Button Wrapper -->
						<div>
							<button
								class="w-full flex items-center justify-between px-4 py-2 gap-2 rounded-full
									bg-white/50 dark:bg-white/5
									border border-gray-200/30 dark:border-gray-200/20
									shadow-[0.25rem_0.25rem_1.25rem_rgba(0,0,0,0.1),inset_0.125rem_0.125rem_1rem_rgba(206,212,229,0.1)] dark:shadow-[0.25rem_0.25rem_1.25rem_rgba(0,0,0,0.2)]
									backdrop-blur-md
									hover:bg-white/60 dark:hover:bg-white/10
									transition text-left"
								on:click={() => toggleSection(section.id)}
							>
								<span class="text-xs leading-tight text-gray-950 dark:text-gray-50 font-pretendard font-normal flex-1 truncate">{section.title}</span>
								<ChevronDown
									className="size-5 flex-shrink-0 transition-transform duration-200 text-gray-950 dark:text-gray-50 {expandedSections[section.id]
										? 'rotate-180'
										: ''}"
									strokeWidth="1.5"
								/>
							</button>
						</div>

						<!-- Subsections -->
						{#if expandedSections[section.id]}
							<div class="w-full flex flex-col items-start px-1 py-1 gap-1" transition:slide={{ duration: 200 }}>
								{#each section.subsections as subsection}
									<button
										class="w-full flex items-center px-1 py-4 h-6 rounded-xl hover:bg-black/10 dark:hover:bg-white/10 transition text-left"
										on:click={() => selectSubsection(subsection)}
									>
										<span class="text-xs text-gray-950 dark:text-gray-200 flex-1 truncate">{subsection.title}</span>
									</button>
								{/each}
							</div>
						{/if}
					</div>
				
				</div>
			{/each}
		{/if}
	</div>
</div>
