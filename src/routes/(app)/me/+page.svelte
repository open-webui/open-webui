<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { Chart } from 'chart.js/auto';

	const i18n = getContext('i18n');

	// ── 더미 데이터 ──────────────────────────────────────────
	const stats = {
		totalQuestions: 127,
		questionsThisWeek: 12,
		reviewCompleted: 23,
		reviewTotal: 31,
		understoodConcepts: 18,
		totalConcepts: 45,
		studyDays: 24
	};

	const weeklyData = [
		{ day: '월', count: 8 },
		{ day: '화', count: 12 },
		{ day: '수', count: 5 },
		{ day: '목', count: 15 },
		{ day: '금', count: 10 },
		{ day: '토', count: 3 },
		{ day: '일', count: 7 }
	];

	const concepts = [
		{ name: '라플라스 변환', chapter: '6장. 라플라스 변환', score: 82 },
		{ name: '푸리에 급수', chapter: '11장. 푸리에 해석', score: 65 },
		{ name: '행렬 고유값', chapter: '8장. 선형대수', score: 45 },
		{ name: '벡터 적분법', chapter: '10장. 벡터 미적분', score: 72 },
		{ name: '복소 함수론', chapter: '13장. 복소해석', score: 30 }
	];

	const checklist = [
		{ name: '라플라스 변환', done: true },
		{ name: '푸리에 해석', done: true },
		{ name: '벡터 미적분학', done: true },
		{ name: '편미분방정식', done: false },
		{ name: '복소해석', done: false }
	];

	// ── 레벨 헬퍼 ────────────────────────────────────────────
	function getLevel(score: number): { label: string; color: string; barColor: string; textColor: string } {
		if (score >= 75) return { label: '상', color: 'bg-green-500', barColor: '#22c55e', textColor: 'text-green-600 dark:text-green-400' };
		if (score >= 40) return { label: '중', color: 'bg-amber-400', barColor: '#f59e0b', textColor: 'text-amber-500 dark:text-amber-400' };
		return { label: '하', color: 'bg-red-500', barColor: '#ef4444', textColor: 'text-red-600 dark:text-red-400' };
	}

	const REVIEW_CTA_THRESHOLD = 60;

	// ── 배너 상태 ─────────────────────────────────────────────
	$: pendingCount = checklist.filter((c) => !c.done).length;
	$: bannerVisible = pendingCount > 0;

	function dismissBanner() {
		bannerVisible = false;
	}

	// ── AI CTA ────────────────────────────────────────────────
	function askAI(concept: string) {
		goto(`/?q=${encodeURIComponent(concept + '에 대해 설명해주세요.')}`);
	}

	// ── Chart.js ──────────────────────────────────────────────
	let chartCanvas: HTMLCanvasElement;
	let chartInstance: Chart;

	onMount(() => {
		chartInstance = new Chart(chartCanvas, {
			type: 'bar',
			data: {
				labels: weeklyData.map((d) => d.day),
				datasets: [
					{
						data: weeklyData.map((d) => d.count),
						backgroundColor: '#076EF4',
						borderRadius: 6,
						borderSkipped: false
					}
				]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: { display: false },
					tooltip: {
						callbacks: {
							label: (ctx) => `${ctx.parsed.y}회`
						}
					}
				},
				scales: {
					y: {
						beginAtZero: true,
						ticks: { stepSize: 5, color: '#6b7280' },
						grid: { color: 'rgba(107,114,128,0.15)' }
					},
					x: {
						ticks: { color: '#6b7280' },
						grid: { display: false }
					}
				}
			}
		});

		return () => {
			chartInstance?.destroy();
		};
	});
</script>

<div class="flex flex-col gap-6 p-6 max-w-6xl mx-auto w-full">
	<!-- 페이지 타이틀 -->
	<div>
		<h1 class="text-2xl font-bold text-gray-900 dark:text-white">내 학습 대시보드</h1>
		<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
			{$user?.name ?? ''}님의 학습 현황을 확인하세요.
		</p>
	</div>

	<!-- 복습 미완료 배너 -->
	{#if bannerVisible}
		<div
			class="flex items-center justify-between gap-3 px-4 py-3 rounded-xl
				bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700/50"
		>
			<div class="flex items-center gap-2 text-sm text-amber-800 dark:text-amber-300">
				<svg class="size-4 shrink-0" viewBox="0 0 20 20" fill="currentColor">
					<path fill-rule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd"/>
				</svg>
				복습 미완료 항목이 <strong>{pendingCount}개</strong> 있습니다.
			</div>
			<div class="flex items-center gap-2 shrink-0">
				<button
					class="text-xs font-medium text-amber-700 dark:text-amber-300 hover:underline"
					on:click={() => document.getElementById('review-checklist')?.scrollIntoView({ behavior: 'smooth' })}
				>
					지금 시작하기 →
				</button>
				<button
					class="text-amber-600 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-200"
					on:click={dismissBanner}
					aria-label="닫기"
				>
					<svg class="size-4" viewBox="0 0 20 20" fill="currentColor">
						<path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"/>
					</svg>
				</button>
			</div>
		</div>
	{/if}

	<!-- 통계 카드 4개 -->
	<div class="grid grid-cols-2 @md:grid-cols-4 gap-4">
		<!-- 총 질문 수 -->
		<div class="flex flex-col gap-1 p-4 rounded-2xl bg-white dark:bg-gray-800 shadow-sm border border-gray-100 dark:border-gray-700">
			<span class="text-xs text-gray-500 dark:text-gray-400">총 질문 수</span>
			<span class="text-2xl font-bold text-gray-900 dark:text-white">{stats.totalQuestions}</span>
			<span class="text-xs text-blue-500">이번 주 +{stats.questionsThisWeek}개</span>
		</div>
		<!-- 복습 완료 -->
		<div class="flex flex-col gap-1 p-4 rounded-2xl bg-white dark:bg-gray-800 shadow-sm border border-gray-100 dark:border-gray-700">
			<span class="text-xs text-gray-500 dark:text-gray-400">복습 완료</span>
			<span class="text-2xl font-bold text-gray-900 dark:text-white">{stats.reviewCompleted}<span class="text-sm font-normal text-gray-400">/{stats.reviewTotal}</span></span>
			<span class="text-xs text-green-500">{Math.round((stats.reviewCompleted / stats.reviewTotal) * 100)}% 달성</span>
		</div>
		<!-- 이해 개념 -->
		<div class="flex flex-col gap-1 p-4 rounded-2xl bg-white dark:bg-gray-800 shadow-sm border border-gray-100 dark:border-gray-700">
			<span class="text-xs text-gray-500 dark:text-gray-400">이해 개념</span>
			<span class="text-2xl font-bold text-gray-900 dark:text-white">{stats.understoodConcepts}<span class="text-sm font-normal text-gray-400">/{stats.totalConcepts}</span></span>
			<span class="text-xs text-purple-500">개념 학습 중</span>
		</div>
		<!-- 학습 일수 -->
		<div class="flex flex-col gap-1 p-4 rounded-2xl bg-white dark:bg-gray-800 shadow-sm border border-gray-100 dark:border-gray-700">
			<span class="text-xs text-gray-500 dark:text-gray-400">학습 일수</span>
			<span class="text-2xl font-bold text-gray-900 dark:text-white">{stats.studyDays}<span class="text-sm font-normal text-gray-400">일</span></span>
			<span class="text-xs text-orange-500">꾸준히 학습 중</span>
		</div>
	</div>

	<!-- 주간 학습 패턴 + 개념별 이해도 -->
	<div class="grid grid-cols-1 @lg:grid-cols-2 gap-4">
		<!-- 주간 학습 패턴 -->
		<div class="flex flex-col gap-3 p-5 rounded-2xl bg-white dark:bg-gray-800 shadow-sm border border-gray-100 dark:border-gray-700">
			<div class="flex items-center gap-2">
				<svg class="size-4 text-blue-500" viewBox="0 0 20 20" fill="currentColor">
					<path fill-rule="evenodd" d="M5.75 2a.75.75 0 01.75.75V4h7V2.75a.75.75 0 011.5 0V4h.25A2.75 2.75 0 0118 6.75v8.5A2.75 2.75 0 0115.25 18H4.75A2.75 2.75 0 012 15.25v-8.5A2.75 2.75 0 014.75 4H5V2.75A.75.75 0 015.75 2zm-1 5.5c-.69 0-1.25.56-1.25 1.25v6.5c0 .69.56 1.25 1.25 1.25h10.5c.69 0 1.25-.56 1.25-1.25v-6.5c0-.69-.56-1.25-1.25-1.25H4.75z" clip-rule="evenodd"/>
				</svg>
				<h2 class="text-sm font-semibold text-gray-800 dark:text-gray-200">주간 학습 패턴</h2>
			</div>
			<div class="h-48 w-full">
				<canvas bind:this={chartCanvas}></canvas>
			</div>
		</div>

		<!-- 개념별 이해도 -->
		<div class="flex flex-col gap-3 p-5 rounded-2xl bg-white dark:bg-gray-800 shadow-sm border border-gray-100 dark:border-gray-700">
			<div class="flex items-center gap-2">
				<svg class="size-4 text-indigo-500" viewBox="0 0 20 20" fill="currentColor">
					<path d="M15.98 1.804a1 1 0 00-1.96 0l-.24 1.192a1 1 0 01-.784.785l-1.192.238a1 1 0 000 1.962l1.192.238a1 1 0 01.785.785l.238 1.192a1 1 0 001.962 0l.238-1.192a1 1 0 01.785-.785l1.192-.238a1 1 0 000-1.962l-1.192-.238a1 1 0 01-.785-.785l-.238-1.192zM6.949 5.684a1 1 0 00-1.898 0l-.683 2.051a1 1 0 01-.633.633l-2.051.683a1 1 0 000 1.898l2.051.684a1 1 0 01.633.632l.683 2.051a1 1 0 001.898 0l.683-2.051a1 1 0 01.633-.633l2.051-.683a1 1 0 000-1.898l-2.051-.683a1 1 0 01-.633-.633L6.95 5.684z"/>
				</svg>
				<h2 class="text-sm font-semibold text-gray-800 dark:text-gray-200">개념별 이해도</h2>
			</div>
			<div class="flex flex-col gap-3">
				{#each concepts as concept}
					{@const level = getLevel(concept.score)}
					<div class="flex flex-col gap-1">
						<div class="flex items-center justify-between gap-2">
							<div class="flex items-center gap-2 min-w-0">
								<span
									class="shrink-0 inline-flex items-center justify-center text-[10px] font-bold
										text-white px-1.5 py-0.5 rounded {level.color}"
								>
									{level.label}
								</span>
								<span class="text-sm text-gray-700 dark:text-gray-200 truncate">{concept.name}</span>
							</div>
							<div class="flex items-center gap-2 shrink-0">
								<span class="text-xs font-semibold {level.textColor}">{concept.score}%</span>
								{#if concept.score < REVIEW_CTA_THRESHOLD}
									<button
										class="text-xs px-2 py-1 rounded-lg font-medium
											bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400
											hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors"
										on:click={() => askAI(concept.name)}
									>
										AI에게 다시 물어보기
									</button>
								{/if}
							</div>
						</div>
						<!-- 진행 바 -->
						<div class="h-1.5 w-full rounded-full bg-gray-100 dark:bg-gray-700">
							<div
								class="h-1.5 rounded-full transition-all duration-500"
								style="width: {concept.score}%; background-color: {level.barColor};"
							></div>
						</div>
						<span class="text-[11px] text-gray-400 dark:text-gray-500">{concept.chapter}</span>
					</div>
				{/each}
			</div>
		</div>
	</div>

	<!-- 복습 체크리스트 -->
	<div
		id="review-checklist"
		class="flex flex-col gap-3 p-5 rounded-2xl bg-white dark:bg-gray-800 shadow-sm border border-gray-100 dark:border-gray-700"
	>
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2">
				<svg class="size-4 text-green-500" viewBox="0 0 20 20" fill="currentColor">
					<path fill-rule="evenodd" d="M16.403 12.652a3 3 0 000-5.304 3 3 0 00-3.75-3.751 3 3 0 00-5.305 0 3 3 0 00-3.751 3.75 3 3 0 000 5.305 3 3 0 003.75 3.751 3 3 0 005.305 0 3 3 0 003.751-3.75zm-2.546-4.46a.75.75 0 00-1.214-.883l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clip-rule="evenodd"/>
				</svg>
				<h2 class="text-sm font-semibold text-gray-800 dark:text-gray-200">복습 체크리스트</h2>
			</div>
			<span class="text-xs text-gray-400 dark:text-gray-500">
				{checklist.filter((c) => c.done).length}/{checklist.length} 완료
			</span>
		</div>
		<div class="flex flex-col gap-2">
			{#each checklist as item}
				<div class="flex items-center gap-3 py-2 px-3 rounded-xl
					{item.done
						? 'bg-gray-50 dark:bg-gray-700/50'
						: 'bg-amber-50 dark:bg-amber-900/10 border border-amber-100 dark:border-amber-800/30'}">
					<div
						class="size-5 rounded-full shrink-0 flex items-center justify-center
							{item.done ? 'bg-green-500' : 'bg-white dark:bg-gray-800 border-2 border-gray-300 dark:border-gray-600'}"
					>
						{#if item.done}
							<svg class="size-3 text-white" viewBox="0 0 12 12" fill="none">
								<path d="M2 6l3 3 5-5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
							</svg>
						{/if}
					</div>
					<span
						class="text-sm {item.done
							? 'text-gray-400 dark:text-gray-500 line-through'
							: 'text-gray-700 dark:text-gray-200'}"
					>
						{item.name}
					</span>
					{#if !item.done}
						<button
							class="ml-auto text-xs px-2 py-0.5 rounded-lg font-medium
								bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400
								hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors"
							on:click={() => askAI(item.name)}
						>
							AI와 복습하기
						</button>
					{/if}
				</div>
			{/each}
		</div>
	</div>
</div>
