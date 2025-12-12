<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { slide } from 'svelte/transition';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	const dispatch = createEventDispatcher();

	// Dummy textbook data
	const textbookData = {
		title: 'Advanced Engineering Mathematics',
		author: 'Erwin Kreyszig',
		edition: '10th Edition',
		sections: [
			{
				id: 'part-a',
				title: 'Part A. 상미분방정식',
				subsections: [
					{
						id: 'ode-1',
						title: '1. 1계 상미분방정식 (First-Order ODEs)',
						subtitle: '1계 미분방정식의 기본 개념과 해법을 학습합니다.'
					},
					{
						id: 'ode-2',
						title: '2. 2계 선형 상미분방정식 (Second-Order Linear ODEs)',
						subtitle: '2계 선형 미분방정식의 해법과 응용을 다룹니다.'
					},
					{
						id: 'ode-3',
						title: '3. 고계 선형 상미분방정식 (Higher Order Linear ODEs)',
						subtitle: '3계 이상의 선형 미분방정식을 학습합니다.'
					}
				]
			},
			{
				id: 'part-b',
				title: 'Part B. 선형 대수, 벡터 미적분',
				subsections: [
					{
						id: 'linear-1',
						title: '4. 선형 대수: 행렬, 벡터, 행렬식 (Linear Algebra: Matrices, Vectors, Determinants)',
						subtitle: '행렬과 벡터의 기본 개념을 이해합니다.'
					},
					{
						id: 'linear-2',
						title: '5. 선형 대수: 행렬 고유값 문제 (Linear Algebra: Matrix Eigenvalue Problems)',
						subtitle: '고유값과 고유벡터의 개념과 응용을 학습합니다.'
					},
					{
						id: 'vector-1',
						title: '6. 벡터 미적분: 그래디언트, 발산, 회전 (Vector Calculus: Gradient, Divergence, Curl)',
						subtitle: '벡터장의 미분 연산자를 이해합니다.'
					}
				]
			},
			{
				id: 'part-c',
				title: 'Part C. 푸리에 해석, 편미분방정식',
				subsections: [
					{
						id: 'fourier-1',
						title: '7. 푸리에 급수 (Fourier Series)',
						subtitle: '주기 함수의 푸리에 급수 전개를 학습합니다.'
					},
					{
						id: 'fourier-2',
						title: '8. 푸리에 적분과 변환 (Fourier Integrals and Transforms)',
						subtitle: '푸리에 변환의 개념과 응용을 다룹니다.'
					},
					{
						id: 'pde-1',
						title: '9. 편미분방정식 (Partial Differential Equations)',
						subtitle: '편미분방정식의 기본 개념과 해법을 학습합니다.'
					}
				]
			},
			{
				id: 'part-d',
				title: 'Part D. 복소 해석',
				subsections: [
					{
						id: 'complex-1',
						title: '10. 복소수와 복소 함수 (Complex Numbers and Functions)',
						subtitle: '복소수의 기본 개념과 복소 함수를 이해합니다.'
					},
					{
						id: 'complex-2',
						title: '11. 복소 적분 (Complex Integration)',
						subtitle: '복소 평면에서의 적분을 학습합니다.'
					},
					{
						id: 'complex-3',
						title: '12. 급수, 유수, 특이점 (Series, Residues, Singularities)',
						subtitle: '복소 급수와 유수 정리를 다룹니다.'
					}
				]
			},
			{
				id: 'part-e',
				title: 'Part E. 수치 해석',
				subsections: [
					{
						id: 'numerical-1',
						title: '13. 선형 시스템의 수치 해법 (Numerical Methods for Linear Systems)',
						subtitle: '선형 방정식 시스템의 수치 해법을 학습합니다.'
					},
					{
						id: 'numerical-2',
						title: '14. 미분방정식의 수치 해법 (Numerical Methods for Differential Equations)',
						subtitle: '미분방정식을 수치적으로 풀어냅니다.'
					}
				]
			}
		]
	};

	// State for expanded sections
	let expandedSections = {};

	const toggleSection = (sectionId) => {
		expandedSections[sectionId] = !expandedSections[sectionId];
		expandedSections = { ...expandedSections };
	};

	const selectSubsection = (subsection) => {
		dispatch('subsection-select', {
			title: subsection.title,
			subtitle: subsection.subtitle
		});
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
			<!-- Textbook Card -->
			<div
				class="mx-2 px-5 py-4 rounded-[20px] bg-[rgba(253,254,254,0.7)] border-0 shadow-[4px_4px_20px_rgba(0,0,0,0.1)] backdrop-blur-[20px]"
			>
				<div class="w-[220px] text-sm font-normal text-[#1A1B1C] dark:text-white mb-1">{textbookData.title}</div>
				<div class="flex flex-col gap-1 w-[220px]">
					<div class="text-xs font-normal text-[#596172] dark:text-gray-400">저자: {textbookData.author}</div>
					<div class="text-xs font-normal text-[#596172] dark:text-gray-400">판: {textbookData.edition}</div>
				</div>
			</div>

			<!-- Sections -->
			{#each textbookData.sections as section}
				<div class="mx-2">
					<div class="{expandedSections[section.id] ? 'bg-[rgba(253,254,254,0.5)] shadow-[4px_4px_20px_rgba(0,0,0,0.1),inset_2px_2px_16px_rgba(206,212,229,0.1)] backdrop-blur-[10px] rounded-2xl' : ''}">
						<!-- Section Button Wrapper -->
						<div>
							<button
								class="w-full flex items-center justify-between px-4 py-2 gap-2 rounded-full bg-[rgba(253,254,254,0.5)] shadow-[4px_4px_20px_rgba(0,0,0,0.1),inset_2px_2px_16px_rgba(206,212,229,0.1)] backdrop-blur-[10px] hover:bg-[rgba(253,254,254,0.6)] transition text-left"
								on:click={() => toggleSection(section.id)}
							>
								<span class="text-xs leading-[18px] text-[#1A1B1C] dark:text-[#FDFEFE] font-pretendard font-normal flex-1 truncate">{section.title}</span>
								<ChevronDown
									className="size-5 flex-shrink-0 transition-transform duration-200 text-[#1A1B1C] dark:text-[#FDFEFE] {expandedSections[section.id]
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
										class="w-full flex items-center px-1 py-4 h-[25px] rounded-xl hover:bg-black/10 dark:hover:bg-white/10 transition text-left"
										on:click={() => selectSubsection(subsection)}
									>
										<span class="text-xs text-[#1A1B1C] dark:text-gray-200 flex-1 truncate">{subsection.title}</span>
									</button>
								{/each}
							</div>
						{/if}
					</div>
				
				</div>
			{/each}
	</div>
</div>
