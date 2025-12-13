<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { slide } from 'svelte/transition';
	const i18n = getContext('i18n');

	// Expand/collapse state for concept cards
	let expandedCards = { 0: true }; // First card expanded by default

	const toggleCard = (index) => {
		expandedCards[index] = !expandedCards[index];
		expandedCards = expandedCards; // Trigger reactivity
	};

	// API response types
	interface UsageStats {
		period_days: number;
		active_users: number;
		active_users_increased: number;
		total_conversations: number;
		total_conversations_increased: number;
		total_qa_pairs: number;
		total_qa_pairs_increased: number;
		start_timestamp: number;
		end_timestamp: number;
	}

	interface ChapterQuestion {
		question: string;
		user_name: string;
		timestamp: number;
	}

	interface ChapterStats {
		chapter_id: string;
		chapter_title: string;
		question_count: number;
		questions: ChapterQuestion[];
	}

	interface ChapterStatsResponse {
		period_days: number;
		total_questions: number;
		chapters: ChapterStats[];
	}

	// State
	let loading = true;
	let usageStats: UsageStats | null = null;
	let chapterStats: ChapterStatsResponse | null = null;

	// Fetch usage stats
	async function fetchUsageStats(days: number = 7): Promise<UsageStats> {
		const response = await fetch(`/api/v1/textbook/stats/usage?days=${days}`);
		if (!response.ok) {
			throw new Error('Failed to fetch usage stats');
		}
		return response.json();
	}

	// Fetch chapter stats
	async function fetchChapterStats(days: number = 7): Promise<ChapterStatsResponse> {
		const response = await fetch(
			`/api/v1/textbook/stats/by-chapter?days=${days}&include_questions=true&max_questions_per_chapter=10`
		);
		if (!response.ok) {
			throw new Error('Failed to fetch chapter stats');
		}
		return response.json();
	}

	// Load data on mount
	onMount(async () => {
		try {
			const [usage, chapters] = await Promise.all([
				fetchUsageStats(7),
				fetchChapterStats(7)
			]);
			usageStats = usage;
			chapterStats = chapters;
		} catch (error) {
			console.error('Failed to load dashboard data:', error);
		} finally {
			loading = false;
		}
	});

	// Reactive stats for display
	$: stats = {
		weeklyActiveUsers: {
			value: usageStats?.active_users ?? 0,
			increased: usageStats?.active_users_increased ?? 0,
			label: '주간 활성 사용자 수'
		},
		totalConversations: {
			value: usageStats?.total_conversations ?? 0,
			increased: usageStats?.total_conversations_increased ?? 0,
			label: '총 대화 수'
		},
		aiTutorQuestions: {
			value: usageStats?.total_qa_pairs ?? 0,
			increased: usageStats?.total_qa_pairs_increased ?? 0,
			label: 'AI 튜터 질문 수'
		}
	};

	// Transform chapter stats to display format
	$: frequentConcepts = chapterStats?.chapters.map((chapter, index) => ({
		id: index,
		title: chapter.chapter_title.split('.')[1]?.trim() || chapter.chapter_title,
		chapter: chapter.chapter_title,
		questionCount: chapter.question_count,
		questions: chapter.questions.map((q) => ({
			text: q.question,
			author: q.user_name
		}))
	})) ?? [];

	// Reusable styles for concept cards
	const conceptCardBase = `box-border flex flex-col items-start px-9 py-7 w-full
		bg-[rgba(253,254,254,0.7)] dark:bg-[rgba(39,40,44,0.5)]
		shadow-[4px_4px_20px_rgba(0,0,0,0.1)] backdrop-blur-[20px]
		rounded-[20px] transition-all duration-200 cursor-pointer
		hover:shadow-[6px_6px_24px_rgba(0,0,0,0.15)]`;

	const conceptCardExpanded = `${conceptCardBase} gap-6`;
	const conceptCardCollapsed = `${conceptCardBase} gap-0.5`;

	// Reusable styles for stat cards
	const statCard = `box-border flex flex-col items-start px-9 py-7 gap-0.5
		w-[300px] h-[120px]
		bg-[rgba(253,254,254,0.7)] dark:bg-[rgba(39,40,44,0.5)]
		shadow-[4px_4px_20px_rgba(0,0,0,0.1)] backdrop-blur-[20px]
		rounded-[20px] flex-none flex-grow-0`;
</script>

<div class="w-full h-full flex flex-col items-center p-8">
	<!-- 현황 분석 Section -->
	<div class="flex flex-col justify-center items-start gap-5 w-full max-w-[920px]">
		<!-- Section Title -->
		<h2 class="text-title-1 text-gray-950 dark:text-gray-50 tracking-[-0.02em]">현황 분석</h2>

		<!-- Cards Container -->
		{#if loading}
			<div class="flex flex-row justify-between items-center gap-5 w-full">
				{#each [1, 2, 3] as _}
					<div class="{statCard} animate-pulse">
						<div class="w-5 h-5 bg-gray-200 dark:bg-gray-700 rounded"></div>
						<div class="flex flex-row justify-between items-center w-full mt-2">
							<div class="w-24 h-4 bg-gray-200 dark:bg-gray-700 rounded"></div>
							<div class="w-12 h-6 bg-gray-200 dark:bg-gray-700 rounded"></div>
						</div>
					</div>
				{/each}
			</div>
		{:else}
			<div class="flex flex-row justify-between items-center gap-5 w-full">
				<!-- Card 1: 주간 활성 사용자 수 -->
				<div class={statCard}>
					<div class="flex flex-row justify-between items-center w-full">
						<svg
							width="20"
							height="20"
							viewBox="0 0 20 20"
							fill="none"
							xmlns="http://www.w3.org/2000/svg"
							class="text-gray-950 dark:text-gray-50"
						>
							<mask
								id="mask0_267_4159"
								style="mask-type:alpha"
								maskUnits="userSpaceOnUse"
								x="0"
								y="0"
								width="20"
								height="20"
							>
								<rect width="20" height="20" fill="currentColor" />
							</mask>
							<g mask="url(#mask0_267_4159)">
								<path
									d="M2 14.0833C2 13.7253 2.08681 13.3962 2.26042 13.096C2.43403 12.7959 2.67361 12.5556 2.97917 12.375C3.72917 11.9306 4.52431 11.5903 5.36458 11.3542C6.20486 11.1181 7.08333 11 8 11C8.91667 11 9.79514 11.1181 10.6354 11.3542C11.4757 11.5903 12.2708 11.9306 13.0208 12.375C13.3264 12.5556 13.566 12.7959 13.7396 13.096C13.9132 13.3962 14 13.7253 14 14.0833V14.5C14 14.9125 13.8531 15.2656 13.5592 15.5594C13.2653 15.8531 12.9119 16 12.4992 16H3.49417C3.08139 16 2.72917 15.8531 2.4375 15.5594C2.14583 15.2656 2 14.9125 2 14.5V14.0833ZM16.5 16H15.1042C15.2292 15.7639 15.3264 15.5195 15.3958 15.2669C15.4653 15.0144 15.5 14.7587 15.5 14.5V14.0833C15.5 13.5 15.3646 12.9583 15.0938 12.4583C14.8229 11.9583 14.4583 11.5486 14 11.2292C14.5417 11.3403 15.066 11.4896 15.5729 11.6771C16.0799 11.8646 16.5625 12.0972 17.0208 12.375C17.3264 12.5556 17.566 12.7963 17.7396 13.0973C17.9132 13.3984 18 13.7271 18 14.0833V14.5C18 14.9125 17.8531 15.2656 17.5594 15.5594C17.2656 15.8531 16.9125 16 16.5 16ZM8 10C7.16667 10 6.45833 9.70833 5.875 9.125C5.29167 8.54167 5 7.83333 5 7C5 6.16667 5.29167 5.45833 5.875 4.875C6.45833 4.29167 7.16667 4 8 4C8.83333 4 9.54167 4.29167 10.125 4.875C10.7083 5.45833 11 6.16667 11 7C11 7.83333 10.7083 8.54167 10.125 9.125C9.54167 9.70833 8.83333 10 8 10ZM15 7C15 7.83333 14.7083 8.54167 14.125 9.125C13.5417 9.70833 12.8333 10 12 10C11.8889 10 11.7847 9.99653 11.6875 9.98958C11.5903 9.98264 11.4861 9.96528 11.375 9.9375C11.7222 9.53472 11.9965 9.08681 12.1979 8.59375C12.3993 8.10069 12.5 7.56944 12.5 7C12.5 6.43056 12.3993 5.89931 12.1979 5.40625C11.9965 4.91319 11.7222 4.46528 11.375 4.0625C11.4861 4.03472 11.5903 4.01736 11.6875 4.01042C11.7847 4.00347 11.8889 4 12 4C12.8333 4 13.5417 4.29167 14.125 4.875C14.7083 5.45833 15 6.16667 15 7ZM3.5 14.5H12.5V14.0833C12.5 13.9935 12.479 13.9118 12.4369 13.8383C12.3949 13.7647 12.3396 13.7075 12.2708 13.6667C11.6181 13.2917 10.9306 13.0035 10.2083 12.8021C9.48611 12.6007 8.75 12.5 8 12.5C7.25 12.5 6.51389 12.5972 5.79167 12.7917C5.06944 12.9861 4.38194 13.2778 3.72917 13.6667C3.66042 13.706 3.605 13.7609 3.56292 13.8315C3.52097 13.9022 3.5 13.9855 3.5 14.0815V14.5ZM8.00437 8.5C8.41813 8.5 8.77083 8.35271 9.0625 8.05812C9.35417 7.76354 9.5 7.40937 9.5 6.99562C9.5 6.58187 9.35271 6.22917 9.05813 5.9375C8.76354 5.64583 8.40938 5.5 7.99563 5.5C7.58188 5.5 7.22917 5.64729 6.9375 5.94188C6.64583 6.23646 6.5 6.59063 6.5 7.00438C6.5 7.41813 6.64729 7.77083 6.94187 8.0625C7.23646 8.35417 7.59062 8.5 8.00437 8.5Z"
									fill="currentColor"
								/>
							</g>
						</svg>
						<span class="text-caption {stats.weeklyActiveUsers.increased >= 0 ? 'text-[#34BE89]' : 'text-[#DB576D]'}">
							{stats.weeklyActiveUsers.increased >= 0 ? '+' : ''}{stats.weeklyActiveUsers.increased}
						</span>
					</div>
					<div class="flex flex-row justify-between items-center w-full">
						<span class="text-body-3 text-gray-950 dark:text-gray-50">{stats.weeklyActiveUsers.label}</span>
						<span class="text-title-1 text-gray-950 dark:text-gray-50 tracking-[-0.02em]">{stats.weeklyActiveUsers.value}</span>
					</div>
				</div>

				<!-- Card 2: 총 대화 수 -->
				<div class={statCard}>
					<div class="flex flex-row justify-between items-center w-full">
						<svg
							width="20"
							height="20"
							viewBox="0 0 20 20"
							fill="none"
							xmlns="http://www.w3.org/2000/svg"
							class="text-gray-950 dark:text-gray-50"
						>
							<mask
								id="mask0_chat"
								style="mask-type:alpha"
								maskUnits="userSpaceOnUse"
								x="0"
								y="0"
								width="20"
								height="20"
							>
								<rect width="20" height="20" fill="currentColor" />
							</mask>
							<g mask="url(#mask0_chat)">
								<path
									d="M5 13.5H11.5C11.7083 13.5 11.8854 13.4271 12.0313 13.2812C12.1771 13.1354 12.25 12.9583 12.25 12.75C12.25 12.5417 12.1771 12.3646 12.0313 12.2188C11.8854 12.0729 11.7083 12 11.5 12H5C4.79167 12 4.61458 12.0729 4.46875 12.2188C4.32292 12.3646 4.25 12.5417 4.25 12.75C4.25 12.9583 4.32292 13.1354 4.46875 13.2812C4.61458 13.4271 4.79167 13.5 5 13.5ZM5 10.5H15C15.2083 10.5 15.3854 10.4271 15.5312 10.2812C15.6771 10.1354 15.75 9.95833 15.75 9.75C15.75 9.54167 15.6771 9.36458 15.5312 9.21875C15.3854 9.07292 15.2083 9 15 9H5C4.79167 9 4.61458 9.07292 4.46875 9.21875C4.32292 9.36458 4.25 9.54167 4.25 9.75C4.25 9.95833 4.32292 10.1354 4.46875 10.2812C4.61458 10.4271 4.79167 10.5 5 10.5ZM5 7.5H15C15.2083 7.5 15.3854 7.42708 15.5312 7.28125C15.6771 7.13542 15.75 6.95833 15.75 6.75C15.75 6.54167 15.6771 6.36458 15.5312 6.21875C15.3854 6.07292 15.2083 6 15 6H5C4.79167 6 4.61458 6.07292 4.46875 6.21875C4.32292 6.36458 4.25 6.54167 4.25 6.75C4.25 6.95833 4.32292 7.13542 4.46875 7.28125C4.61458 7.42708 4.79167 7.5 5 7.5ZM2 17.5V3.5C2 3.0875 2.14687 2.73438 2.44063 2.44063C2.73438 2.14687 3.0875 2 3.5 2H16.5C16.9125 2 17.2656 2.14687 17.5594 2.44063C17.8531 2.73438 18 3.0875 18 3.5V13.5C18 13.9125 17.8531 14.2656 17.5594 14.5594C17.2656 14.8531 16.9125 15 16.5 15H5L2.7 17.3C2.51667 17.4833 2.30556 17.5208 2.06667 17.4125C1.82778 17.3042 1.70833 17.1167 1.70833 16.85V17.5H2Z"
									fill="currentColor"
								/>
							</g>
						</svg>
						<span class="text-caption {stats.totalConversations.increased >= 0 ? 'text-[#34BE89]' : 'text-[#DB576D]'}">
							{stats.totalConversations.increased >= 0 ? '+' : ''}{stats.totalConversations.increased}
						</span>
					</div>
					<div class="flex flex-row justify-between items-center w-full">
						<span class="text-body-3 text-gray-950 dark:text-gray-50">{stats.totalConversations.label}</span>
						<span class="text-title-1 text-gray-950 dark:text-gray-50 tracking-[-0.02em]">{stats.totalConversations.value}</span>
					</div>
				</div>

				<!-- Card 3: AI 튜터 질문 수 -->
				<div class={statCard}>
					<div class="flex flex-row justify-between items-center w-full">
						<svg
							width="20"
							height="20"
							viewBox="0 0 20 20"
							fill="none"
							xmlns="http://www.w3.org/2000/svg"
							class="text-gray-950 dark:text-gray-50"
						>
							<mask
								id="mask0_267_4174"
								style="mask-type:alpha"
								maskUnits="userSpaceOnUse"
								x="0"
								y="0"
								width="20"
								height="20"
							>
								<rect width="20" height="20" fill="currentColor" />
							</mask>
							<g mask="url(#mask0_267_4174)">
								<path
									d="M11.5 12.5C11.7361 12.5 11.934 12.4201 12.0938 12.2604C12.2535 12.1007 12.3333 11.9028 12.3333 11.6667C12.3333 11.4306 12.2535 11.2326 12.0938 11.0729C11.934 10.9132 11.7361 10.8333 11.5 10.8333C11.2639 10.8333 11.066 10.9132 10.9062 11.0729C10.7465 11.2326 10.6667 11.4306 10.6667 11.6667C10.6667 11.9028 10.7465 12.1007 10.9062 12.2604C11.066 12.4201 11.2639 12.5 11.5 12.5ZM11.5058 9.95833C11.6547 9.95833 11.7882 9.90278 11.9062 9.79167C12.0243 9.68056 12.0972 9.53833 12.125 9.365C12.1528 9.205 12.2014 9.0625 12.2708 8.9375C12.3403 8.8125 12.4722 8.65972 12.6667 8.47917C13.1111 8.04861 13.4097 7.70486 13.5625 7.44792C13.7153 7.19097 13.7917 6.90278 13.7917 6.58333C13.7917 5.95833 13.5833 5.45486 13.1667 5.07292C12.75 4.69097 12.1944 4.5 11.5 4.5C11.0628 4.5 10.6653 4.60069 10.3075 4.80208C9.94972 5.00347 9.65972 5.28472 9.4375 5.64583C9.36806 5.77083 9.36493 5.90972 9.42812 6.0625C9.49118 6.21528 9.59847 6.32639 9.75 6.39583C9.88889 6.45139 10.0278 6.45833 10.1667 6.41667C10.3056 6.375 10.4236 6.28472 10.5208 6.14583C10.6319 5.99306 10.7743 5.87153 10.9479 5.78125C11.1215 5.69097 11.308 5.64583 11.5073 5.64583C11.826 5.64583 12.0851 5.73611 12.2844 5.91667C12.4837 6.09722 12.5833 6.33333 12.5833 6.625C12.5833 6.81944 12.5243 7.00347 12.4062 7.17708C12.2882 7.35069 12.0139 7.63889 11.5833 8.04167C11.3333 8.27778 11.1667 8.48264 11.0833 8.65625C11 8.82986 10.9444 9.0625 10.9167 9.35417C10.9028 9.51528 10.9535 9.65625 11.0688 9.77708C11.184 9.89792 11.3297 9.95833 11.5058 9.95833ZM6.5 15C6.0875 15 5.73438 14.8531 5.44062 14.5594C5.14687 14.2656 5 13.9125 5 13.5V3.5C5 3.0875 5.14687 2.73438 5.44062 2.44063C5.73438 2.14688 6.0875 2 6.5 2H16.5C16.9125 2 17.2656 2.14688 17.5594 2.44063C17.8531 2.73438 18 3.0875 18 3.5V13.5C18 13.9125 17.8531 14.2656 17.5594 14.5594C17.2656 14.8531 16.9125 15 16.5 15H6.5ZM6.5 13.5H16.5V3.5H6.5V13.5ZM3.5 18C3.0875 18 2.73438 17.8531 2.44063 17.5594C2.14688 17.2656 2 16.9125 2 16.5V5.75C2 5.5375 2.07146 5.35937 2.21438 5.21562C2.35729 5.07187 2.53437 5 2.74562 5C2.95687 5 3.13542 5.07187 3.28125 5.21562C3.42708 5.35937 3.5 5.5375 3.5 5.75V16.5H14.25C14.4625 16.5 14.6406 16.5715 14.7844 16.7144C14.9281 16.8573 15 17.0344 15 17.2456C15 17.4569 14.9281 17.6354 14.7844 17.7812C14.6406 17.9271 14.4625 18 14.25 18H3.5Z"
									fill="currentColor"
								/>
							</g>
						</svg>
						<span class="text-caption {stats.aiTutorQuestions.increased >= 0 ? 'text-[#34BE89]' : 'text-[#DB576D]'}">
							{stats.aiTutorQuestions.increased >= 0 ? '+' : ''}{stats.aiTutorQuestions.increased}
						</span>
					</div>
					<div class="flex flex-row justify-between items-center w-full">
						<span class="text-body-3 text-gray-950 dark:text-gray-50">{stats.aiTutorQuestions.label}</span>
						<span class="text-title-1 text-gray-950 dark:text-gray-50 tracking-[-0.02em]">{stats.aiTutorQuestions.value}</span>
					</div>
				</div>
			</div>
		{/if}
	</div>

	<!-- 자주 묻는 개념 Section -->
	<div class="flex flex-col justify-center items-start gap-5 w-full max-w-[920px] mt-10">
		<!-- Section Title -->
		<h2 class="text-title-1 text-gray-950 dark:text-gray-50 tracking-[-0.02em]">자주 묻는 개념</h2>

		<!-- Concept Cards -->
		{#if loading}
			{#each [1, 2, 3] as _}
				<div class="{conceptCardCollapsed} animate-pulse">
					<div class="flex flex-row justify-between items-center w-full">
						<div class="flex flex-col items-start gap-2">
							<div class="w-32 h-5 bg-gray-200 dark:bg-gray-700 rounded"></div>
							<div class="w-64 h-4 bg-gray-200 dark:bg-gray-700 rounded"></div>
						</div>
						<div class="flex flex-row items-center gap-4">
							<div class="w-16 h-6 bg-gray-200 dark:bg-gray-700 rounded"></div>
							<div class="w-5 h-5 bg-gray-200 dark:bg-gray-700 rounded"></div>
						</div>
					</div>
				</div>
			{/each}
		{:else if frequentConcepts.length === 0}
			<div class="{conceptCardCollapsed}">
				<span class="text-body-3 text-gray-500">데이터가 없습니다.</span>
			</div>
		{:else}
			{#each frequentConcepts as concept}
			<button
				class={expandedCards[concept.id] ? conceptCardExpanded : conceptCardCollapsed}
				on:click={() => toggleCard(concept.id)}
			>
				<!-- Header Row -->
				<div class="flex flex-row justify-between items-center w-full">
					<!-- Left: Title and Chapter -->
					<div class="flex flex-col items-start gap-2">
						<span class="text-body-3 text-gray-950 dark:text-gray-50">{concept.title}</span>
						<div class="flex flex-row items-center gap-1">
							<!-- Book Icon -->
							<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
								<mask id="mask_book_{concept.id}" style="mask-type:alpha" maskUnits="userSpaceOnUse" x="0" y="0" width="20" height="20">
									<rect width="20" height="20" fill="#D9D9D9"/>
								</mask>
								<g mask="url(#mask_book_{concept.id})">
									<path d="M6.5 14C5.80556 14 5.18056 14.1319 4.625 14.3958C4.06944 14.6597 3.58333 15.0139 3.16667 15.4583V5.08333C3.58333 4.75 4.04861 4.47917 4.5625 4.27083C5.07639 4.0625 5.69444 3.95833 6.41667 3.95833C6.97222 3.95833 7.51042 4.02431 8.03125 4.15625C8.55208 4.28819 9.04167 4.47222 9.5 4.70833V14.3958C9.09722 14.1736 8.67361 14.0035 8.22917 13.8854C7.78472 13.7674 7.15278 13.7083 6.33333 13.7083L6.5 14ZM10.5 14.3958V4.70833C10.9583 4.47222 11.4479 4.28819 11.9688 4.15625C12.4896 4.02431 13.0278 3.95833 13.5833 3.95833C14.3056 3.95833 14.9236 4.0625 15.4375 4.27083C15.9514 4.47917 16.4167 4.75 16.8333 5.08333V15.4583C16.4167 15.0139 15.9306 14.6597 15.375 14.3958C14.8194 14.1319 14.1944 14 13.5 14L13.6667 13.7083C12.8472 13.7083 12.2153 13.7674 11.7708 13.8854C11.3264 14.0035 10.9028 14.1736 10.5 14.3958ZM10 16.7083C9.41667 16.2361 8.77778 15.8681 8.08333 15.6042C7.38889 15.3403 6.63889 15.2083 5.83333 15.2083C5.30556 15.2083 4.79167 15.2778 4.29167 15.4167C3.79167 15.5556 3.31944 15.75 2.875 16C2.59722 16.1528 2.32292 16.1424 2.05208 15.9688C1.78125 15.7951 1.64583 15.5556 1.64583 15.25V4.875C1.64583 4.70833 1.69097 4.55208 1.78125 4.40625C1.87153 4.26042 1.99306 4.15278 2.14583 4.08333C2.70139 3.77778 3.29167 3.54167 3.91667 3.375C4.54167 3.20833 5.18056 3.125 5.83333 3.125C6.61111 3.125 7.36806 3.22917 8.10417 3.4375C8.84028 3.64583 9.5 3.95833 10.0833 4.375C10.6667 3.95833 11.3194 3.64583 12.0417 3.4375C12.7639 3.22917 13.5139 3.125 14.2917 3.125C14.9444 3.125 15.5833 3.20833 16.2083 3.375C16.8333 3.54167 17.4236 3.77778 17.9792 4.08333C18.1319 4.15278 18.2535 4.26042 18.3438 4.40625C18.434 4.55208 18.4792 4.70833 18.4792 4.875V15.25C18.4792 15.5556 18.3403 15.7951 18.0625 15.9688C17.7847 16.1424 17.5139 16.1528 17.25 16C16.8056 15.75 16.3333 15.5556 15.8333 15.4167C15.3333 15.2778 14.8194 15.2083 14.2917 15.2083C13.4861 15.2083 12.7361 15.3403 12.0417 15.6042C11.3472 15.8681 10.7083 16.2361 10.125 16.7083H10Z" fill="#8D96AD"/>
								</g>
							</svg>
							<span class="text-caption text-[#8D96AD]">{concept.chapter}</span>
						</div>
					</div>

					<!-- Right: Question Count and Chevron -->
					<div class="flex flex-row items-center gap-4">
						<div class="flex flex-row items-center gap-1">
							<span class="text-body-3 text-[#596172]">질문</span>
							<span class="text-title-1 text-gray-950 dark:text-gray-50 tracking-[-0.02em]">{concept.questionCount}</span>
						</div>
						<!-- Chevron Icon -->
						<svg
							width="20"
							height="20"
							viewBox="0 0 20 20"
							fill="none"
							xmlns="http://www.w3.org/2000/svg"
							class="transition-transform duration-200 {expandedCards[concept.id] ? 'rotate-180' : ''}"
						>
							<path d="M10 12.5L5 7.5H15L10 12.5Z" fill="currentColor" class="text-gray-950 dark:text-gray-50"/>
						</svg>
					</div>
				</div>

				<!-- Expandable Content -->
				{#if expandedCards[concept.id]}
					<div transition:slide={{ duration: 200 }} class="flex flex-col gap-6 w-full">
						<!-- Divider -->
						<div class="w-full h-0 border-t border-[rgba(206,212,229,0.2)]"></div>

						<!-- Questions List -->
						<div class="flex flex-col items-start gap-2 w-full">
							{#each concept.questions as question}
								<div class="flex flex-row justify-between items-center w-full">
									<span class="text-body-4 text-gray-950 dark:text-gray-50 text-left">{question.text}</span>
									<span class="text-body-3 text-[#596172] shrink-0">{question.author}</span>
								</div>
							{/each}
						</div>
					</div>
				{/if}
			</button>
			{/each}
		{/if}
	</div>
</div>
