<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { slide, fly } from 'svelte/transition';
	import { goto } from '$app/navigation';
	import { mobile, user, theme } from '$lib/stores';
	import { userSignOut } from '$lib/apis/auths';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import HYULogo36 from '$lib/components/icons/HYULogo36.svelte';
	import DashboardToggleSwitch from '$lib/components/dashboard/DashboardToggleSwitch.svelte';
	import { getTopTags, getTagMessagesStats, type TagDefinition, type TagMessagesStats, type TagMessageInfo } from '$lib/apis/message-tags';

	// Extended type to include chapter info
	interface ExtendedTagDefinition extends TagDefinition {
		chapter_id?: string | null;
		chapter_name?: string | null;
	}
	import MessagePreviewModal from '$lib/components/dashboard/MessagePreviewModal.svelte';
	const i18n = getContext('i18n');

	// Mobile sidebar state
	let showMobileSidebar = false;

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

	// State
	let loading = true;
	let usageStats: UsageStats | null = null;
	let topTags: ExtendedTagDefinition[] = [];
	let tagMessagesCache: Record<string, TagMessagesStats> = {};
	let loadingTagMessages: Record<string, boolean> = {};

	// Message preview modal state
	let showMessagePreview = false;
	let selectedMessage: TagMessageInfo | null = null;
	let selectedTagName = '';

	// Fetch usage stats
	async function fetchUsageStats(days: number = 7): Promise<UsageStats> {
		const response = await fetch(`/api/v1/textbook/stats/usage?days=${days}`);
		if (!response.ok) {
			throw new Error('Failed to fetch usage stats');
		}
		return response.json();
	}

	// Load tag messages when card is expanded
	async function loadTagMessages(tagId: string) {
		if (tagMessagesCache[tagId] || loadingTagMessages[tagId]) return;

		loadingTagMessages[tagId] = true;
		loadingTagMessages = loadingTagMessages;

		try {
			const result = await getTagMessagesStats(localStorage.token, tagId, 10, 0);
			if (result) {
				tagMessagesCache[tagId] = result;
				tagMessagesCache = tagMessagesCache;
			}
		} catch (error) {
			console.error('Failed to load tag messages:', error);
		} finally {
			loadingTagMessages[tagId] = false;
			loadingTagMessages = loadingTagMessages;
		}
	}

	// Handle card toggle with lazy loading
	const handleCardToggle = (tagId: string, index: number) => {
		toggleCard(index);
		if (!expandedCards[index]) return;
		loadTagMessages(tagId);
	};

	// Show message preview modal
	const openMessagePreview = (message: TagMessageInfo, tagName: string) => {
		selectedMessage = message;
		selectedTagName = tagName;
		showMessagePreview = true;
	};

	// Load data on mount
	onMount(async () => {
		try {
			const [usage, tags] = await Promise.all([
				fetchUsageStats(7),
				getTopTags(localStorage.token, 10)
			]);
			usageStats = usage;
			topTags = tags ?? [];

			// Pre-load messages for first tag if exists
			if (topTags.length > 0) {
				loadTagMessages(topTags[0].id);
			}
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

	// Glass card base style (Figma: rgba(253, 254, 254, 0.7), shadow 4px 4px 20px rgba(0,0,0,0.1), blur 20px, radius 20px)
	const glassCard = `bg-[rgba(253,254,254,0.7)] dark:bg-gray-900/50 shadow-[4px_4px_20px_rgba(0,0,0,0.1)] backdrop-blur-[20px] rounded-[20px]`;

	// Reusable styles for concept cards (Figma: 440px wide, padding 28px 36px)
	$: conceptCardBase = `box-border flex flex-col items-start w-full
		${glassCard} transition-all duration-200 cursor-pointer
		hover:shadow-[4px_4px_24px_rgba(0,0,0,0.15)]
		${$mobile ? 'p-5' : 'py-7 px-9'}`;

	$: conceptCardExpanded = `${conceptCardBase} ${$mobile ? 'gap-5' : 'gap-6'}`;
	$: conceptCardCollapsed = `${conceptCardBase} gap-0.5`;

	// Reusable styles for stat cards (Figma: 300x120px, padding 28px 36px, gap 2px)
	$: statCard = `box-border flex flex-col items-start gap-0.5
		${glassCard}
		${$mobile ? 'w-full p-5' : 'w-[300px] h-[120px] py-7 px-9'}`;
</script>

<!-- Mobile Top Nav Bar -->
{#if $mobile}
	<div
		class="fixed top-0 left-0 right-0 h-[60px] z-40 flex items-center justify-between px-4
			bg-white/70 dark:bg-gray-900/70 backdrop-blur-xl
			border-b border-gray-200/50 dark:border-gray-800/50"
	>
		<!-- Logo + Title -->
		<a href="/" class="flex items-center gap-2">
			<HYULogo36 />
			<span class="text-sm font-medium text-gray-900 dark:text-white font-primary">HYU AI 대시보드</span>
		</a>
		<!-- Menu Button -->
		<button
			on:click={() => (showMobileSidebar = true)}
			class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-700 dark:text-gray-300"
			aria-label="Open menu"
		>
			<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6">
				<path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
			</svg>
		</button>
	</div>
{/if}

<!-- Mobile Sidebar Backdrop -->
{#if $mobile && showMobileSidebar}
	<div
		class="fixed z-40 top-0 right-0 left-0 bottom-0 bg-white/30 dark:bg-gray-900/30 backdrop-blur-md w-full min-h-screen h-screen"
		on:mousedown={() => (showMobileSidebar = false)}
		on:keydown={(e) => e.key === 'Escape' && (showMobileSidebar = false)}
		role="button"
		tabindex="0"
	/>
{/if}

<!-- Mobile Sidebar -->
{#if $mobile && showMobileSidebar}
	<div
		class="fixed top-0 right-0 z-50 h-screen w-[280px] bg-white dark:bg-gray-950 flex flex-col justify-between"
		transition:fly={{ duration: 250, x: 280 }}
	>
		<!-- Top Section -->
		<div class="flex flex-col p-5 gap-5">
			<!-- User Info + Close Button -->
			<div class="flex flex-row justify-between items-center">
				<!-- User -->
				<div class="flex flex-row items-center gap-3">
					<!-- Avatar -->
					<img
						src={`${WEBUI_API_BASE_URL}/users/${$user?.id}/profile/image`}
						class="w-10 h-10 rounded-full object-cover"
						alt="프로필 이미지"
					/>
					<!-- Name & Role -->
					<div class="flex flex-col">
						<span class="text-body-4-medium text-gray-950 dark:text-white">{$user?.name ?? '사용자'}</span>
						<span class="text-caption text-gray-700">{$user?.role === 'admin' ? '관리자' : ( $user?.role === 'professor') ? '교수' : '학생'}</span>
					</div>
				</div>
				<!-- Close Button -->
				<button
					on:click={() => (showMobileSidebar = false)}
					class="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-950 dark:text-white"
				>
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
						<path stroke-linecap="round" stroke-linejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" />
					</svg>
				</button>
			</div>

			<!-- Mode Toggle -->
			<DashboardToggleSwitch activeMode="dashboard" />
		</div>

		<!-- Bottom Section -->
		<div class="flex flex-col p-5 gap-3">
			<!-- Dark Mode Toggle -->
			<button
				class="flex flex-row items-center gap-2 px-1 py-1 rounded-full bg-white/50 dark:bg-gray-800/50 w-fit"
				on:click={() => {
					if ($theme === 'dark') {
						theme.set('light');
						localStorage.setItem('theme', 'light');
					} else {
						theme.set('dark');
						localStorage.setItem('theme', 'dark');
					}
				}}
			>
				<div class="w-7 h-7 rounded-full {$theme === 'dark' ? 'bg-gray-900' : 'bg-gray-200'} flex items-center justify-center shadow-lg">
					{#if $theme === 'dark'}
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-4 h-4 text-white">
							<path fill-rule="evenodd" d="M9.528 1.718a.75.75 0 01.162.819A8.97 8.97 0 009 6a9 9 0 009 9 8.97 8.97 0 003.463-.69.75.75 0 01.981.98 10.503 10.503 0 01-9.694 6.46c-5.799 0-10.5-4.701-10.5-10.5 0-4.368 2.667-8.112 6.46-9.694a.75.75 0 01.818.162z" clip-rule="evenodd" />
						</svg>
					{:else}
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-4 h-4 text-gray-700">
							<path d="M12 2.25a.75.75 0 01.75.75v2.25a.75.75 0 01-1.5 0V3a.75.75 0 01.75-.75zM7.5 12a4.5 4.5 0 119 0 4.5 4.5 0 01-9 0zM18.894 6.166a.75.75 0 00-1.06-1.06l-1.591 1.59a.75.75 0 101.06 1.061l1.591-1.59zM21.75 12a.75.75 0 01-.75.75h-2.25a.75.75 0 010-1.5H21a.75.75 0 01.75.75zM17.834 18.894a.75.75 0 001.06-1.06l-1.59-1.591a.75.75 0 10-1.061 1.06l1.59 1.591zM12 18a.75.75 0 01.75.75V21a.75.75 0 01-1.5 0v-2.25A.75.75 0 0112 18zM7.758 17.303a.75.75 0 00-1.061-1.06l-1.591 1.59a.75.75 0 001.06 1.061l1.591-1.59zM6 12a.75.75 0 01-.75.75H3a.75.75 0 010-1.5h2.25A.75.75 0 016 12zM6.697 7.757a.75.75 0 001.06-1.06l-1.59-1.591a.75.75 0 00-1.061 1.06l1.59 1.591z" />
						</svg>
					{/if}
				</div>
				<span class="text-caption text-gray-950 dark:text-white pr-2">{$theme === 'dark' ? '다크 모드' : '라이트 모드'}</span>
			</button>

			<!-- Help -->
			<button class="flex flex-row items-center gap-2 p-1 text-gray-950 dark:text-white">
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5">
					<path fill-rule="evenodd" d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zm11.378-3.917c-.89-.777-2.366-.777-3.255 0a.75.75 0 01-.988-1.129c1.454-1.272 3.776-1.272 5.23 0 1.513 1.324 1.513 3.518 0 4.842a3.75 3.75 0 01-.837.552c-.676.328-1.028.774-1.028 1.152v.75a.75.75 0 01-1.5 0v-.75c0-1.279 1.06-2.107 1.875-2.502.182-.088.351-.199.503-.331.83-.727.83-1.857 0-2.584zM12 18a.75.75 0 100-1.5.75.75 0 000 1.5z" clip-rule="evenodd" />
				</svg>
				<span class="text-caption">도움말</span>
			</button>

			<!-- Logout -->
			<button
				class="flex flex-row items-center gap-2 p-1 text-gray-950 dark:text-white"
				on:click={async () => {
					await userSignOut();
					goto('/auth');
				}}
			>
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5">
					<path fill-rule="evenodd" d="M7.5 3.75A1.5 1.5 0 006 5.25v13.5a1.5 1.5 0 001.5 1.5h6a1.5 1.5 0 001.5-1.5V15a.75.75 0 011.5 0v3.75a3 3 0 01-3 3h-6a3 3 0 01-3-3V5.25a3 3 0 013-3h6a3 3 0 013 3V9A.75.75 0 0115 9V5.25a1.5 1.5 0 00-1.5-1.5h-6zm10.72 4.72a.75.75 0 011.06 0l3 3a.75.75 0 010 1.06l-3 3a.75.75 0 11-1.06-1.06l1.72-1.72H9a.75.75 0 010-1.5h10.94l-1.72-1.72a.75.75 0 010-1.06z" clip-rule="evenodd" />
				</svg>
				<span class="text-caption">로그아웃</span>
			</button>
		</div>
	</div>
{/if}

<div class="w-full h-full flex flex-col items-center {$mobile ? 'px-5 pt-[76px] pb-10 gap-10' : 'py-10 px-5 gap-16'}" style="max-width: 960px; margin: 0 auto;">
	<!-- 현황 분석 Section (Figma: gap 20px between title and cards) -->
	<div class="flex flex-col justify-center items-start gap-5 w-full max-w-[920px]">
		<!-- Section Title (Figma: 24px, 600 weight, line-height 36px) -->
		<h2 class="text-title-2 text-gray-950 dark:text-gray-50 tracking-[-0.02em]">현황 분석</h2>

		<!-- Cards Container -->
		{#if loading}
			<div class="flex {$mobile ? 'flex-col gap-5' : 'flex-row justify-between items-center gap-5'} w-full">
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
			<div class="flex {$mobile ? 'flex-col gap-5' : 'flex-row justify-between items-center gap-5'} w-full">
				<!-- Card 1: 주간 활성 사용자 수 (Figma: 300x120px, padding 28px 36px) -->
				<div class={statCard}>
					<!-- Top row: Icon + Change info (Figma: space-between) -->
					<div class="flex flex-row justify-between items-center w-full">
						<!-- Icon (Figma: 20x20, color #1A1B1C) -->
						<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" class="text-[#1A1B1C] dark:text-gray-50">
							<mask id="mask0_267_4159" style="mask-type:alpha" maskUnits="userSpaceOnUse" x="0" y="0" width="20" height="20">
								<rect width="20" height="20" fill="currentColor" />
							</mask>
							<g mask="url(#mask0_267_4159)">
								<path d="M2 14.0833C2 13.7253 2.08681 13.3962 2.26042 13.096C2.43403 12.7959 2.67361 12.5556 2.97917 12.375C3.72917 11.9306 4.52431 11.5903 5.36458 11.3542C6.20486 11.1181 7.08333 11 8 11C8.91667 11 9.79514 11.1181 10.6354 11.3542C11.4757 11.5903 12.2708 11.9306 13.0208 12.375C13.3264 12.5556 13.566 12.7959 13.7396 13.096C13.9132 13.3962 14 13.7253 14 14.0833V14.5C14 14.9125 13.8531 15.2656 13.5592 15.5594C13.2653 15.8531 12.9119 16 12.4992 16H3.49417C3.08139 16 2.72917 15.8531 2.4375 15.5594C2.14583 15.2656 2 14.9125 2 14.5V14.0833ZM16.5 16H15.1042C15.2292 15.7639 15.3264 15.5195 15.3958 15.2669C15.4653 15.0144 15.5 14.7587 15.5 14.5V14.0833C15.5 13.5 15.3646 12.9583 15.0938 12.4583C14.8229 11.9583 14.4583 11.5486 14 11.2292C14.5417 11.3403 15.066 11.4896 15.5729 11.6771C16.0799 11.8646 16.5625 12.0972 17.0208 12.375C17.3264 12.5556 17.566 12.7963 17.7396 13.0973C17.9132 13.3984 18 13.7271 18 14.0833V14.5C18 14.9125 17.8531 15.2656 17.5594 15.5594C17.2656 15.8531 16.9125 16 16.5 16ZM8 10C7.16667 10 6.45833 9.70833 5.875 9.125C5.29167 8.54167 5 7.83333 5 7C5 6.16667 5.29167 5.45833 5.875 4.875C6.45833 4.29167 7.16667 4 8 4C8.83333 4 9.54167 4.29167 10.125 4.875C10.7083 5.45833 11 6.16667 11 7C11 7.83333 10.7083 8.54167 10.125 9.125C9.54167 9.70833 8.83333 10 8 10ZM15 7C15 7.83333 14.7083 8.54167 14.125 9.125C13.5417 9.70833 12.8333 10 12 10C11.8889 10 11.7847 9.99653 11.6875 9.98958C11.5903 9.98264 11.4861 9.96528 11.375 9.9375C11.7222 9.53472 11.9965 9.08681 12.1979 8.59375C12.3993 8.10069 12.5 7.56944 12.5 7C12.5 6.43056 12.3993 5.89931 12.1979 5.40625C11.9965 4.91319 11.7222 4.46528 11.375 4.0625C11.4861 4.03472 11.5903 4.01736 11.6875 4.01042C11.7847 4.00347 11.8889 4 12 4C12.8333 4 13.5417 4.29167 14.125 4.875C14.7083 5.45833 15 6.16667 15 7ZM3.5 14.5H12.5V14.0833C12.5 13.9935 12.479 13.9118 12.4369 13.8383C12.3949 13.7647 12.3396 13.7075 12.2708 13.6667C11.6181 13.2917 10.9306 13.0035 10.2083 12.8021C9.48611 12.6007 8.75 12.5 8 12.5C7.25 12.5 6.51389 12.5972 5.79167 12.7917C5.06944 12.9861 4.38194 13.2778 3.72917 13.6667C3.66042 13.706 3.605 13.7609 3.56292 13.8315C3.52097 13.9022 3.5 13.9855 3.5 14.0815V14.5ZM8.00437 8.5C8.41813 8.5 8.77083 8.35271 9.0625 8.05812C9.35417 7.76354 9.5 7.40937 9.5 6.99562C9.5 6.58187 9.35271 6.22917 9.05813 5.9375C8.76354 5.64583 8.40938 5.5 7.99563 5.5C7.58188 5.5 7.22917 5.64729 6.9375 5.94188C6.64583 6.23646 6.5 6.59063 6.5 7.00438C6.5 7.41813 6.64729 7.77083 6.94187 8.0625C7.23646 8.35417 7.59062 8.5 8.00437 8.5Z" fill="currentColor" />
							</g>
						</svg>
						<!-- Change info (Figma: Caption/1 - 12px, color #34BE89 or #FF4D6A) -->
						<span class="text-caption {stats.weeklyActiveUsers.increased >= 0 ? 'text-[#34BE89]' : 'text-[#FF4D6A]'}">
							{stats.weeklyActiveUsers.increased >= 0 ? '+' : ''} 이번 주 {Math.abs(stats.weeklyActiveUsers.increased)}명 {stats.weeklyActiveUsers.increased >= 0 ? '증가' : '감소'}
						</span>
					</div>
					<!-- Bottom row: Label + Value (Figma: space-between) -->
					<div class="flex flex-row justify-between items-center w-full">
						<!-- Figma: Body/3/400 - 16px, 400 weight, color #1A1B1C -->
						<span class="text-body-3 text-[#1A1B1C] dark:text-gray-50">{stats.weeklyActiveUsers.label}</span>
						<!-- Figma: Title/1 - 28px, 600 weight -->
						<span class="text-title-1 text-[#1A1B1C] dark:text-gray-50 tracking-[-0.02em]">{stats.weeklyActiveUsers.value}</span>
					</div>
				</div>

				<!-- Card 2: 총 대화 수 -->
				<div class={statCard}>
					<div class="flex flex-row justify-between items-center w-full">
						<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" class="text-[#1A1B1C] dark:text-gray-50">
							<mask id="mask0_267_4166" style="mask-type:alpha" maskUnits="userSpaceOnUse" x="0" y="0" width="20" height="20">
								<rect width="20" height="20" fill="currentColor" />
							</mask>
							<g mask="url(#mask0_267_4166)">
								<path d="M5.5 15C5.0875 15 4.73438 14.8531 4.44063 14.5594C4.14688 14.2656 4 13.9125 4 13.5V3.5C4 3.0875 4.14688 2.73438 4.44063 2.44063C4.73438 2.14688 5.0875 2 5.5 2H14.5C14.9125 2 15.2656 2.14688 15.5594 2.44063C15.8531 2.73438 16 3.0875 16 3.5V13.5C16 13.9125 15.8531 14.2656 15.5594 14.5594C15.2656 14.8531 14.9125 15 14.5 15H5.5ZM5.5 13.5H14.5V3.5H5.5V13.5ZM2.5 18C2.0875 18 1.73438 17.8531 1.44063 17.5594C1.14688 17.2656 1 16.9125 1 16.5V5.75C1 5.5375 1.07146 5.35937 1.21438 5.21562C1.35729 5.07187 1.53437 5 1.74562 5C1.95687 5 2.13542 5.07187 2.28125 5.21562C2.42708 5.35937 2.5 5.5375 2.5 5.75V16.5H13.25C13.4625 16.5 13.6406 16.5715 13.7844 16.7144C13.9281 16.8573 14 17.0344 14 17.2456C14 17.4569 13.9281 17.6354 13.7844 17.7812C13.6406 17.9271 13.4625 18 13.25 18H2.5Z" fill="currentColor" />
							</g>
						</svg>
						<span class="text-caption {stats.totalConversations.increased >= 0 ? 'text-[#34BE89]' : 'text-[#FF4D6A]'}">
							{stats.totalConversations.increased >= 0 ? '+' : ''} 이번 주 {Math.abs(stats.totalConversations.increased)}개 {stats.totalConversations.increased >= 0 ? '증가' : '감소'}
						</span>
					</div>
					<div class="flex flex-row justify-between items-center w-full">
						<span class="text-body-3 text-[#1A1B1C] dark:text-gray-50">{stats.totalConversations.label}</span>
						<span class="text-title-1 text-[#1A1B1C] dark:text-gray-50 tracking-[-0.02em]">{stats.totalConversations.value}</span>
					</div>
				</div>

				<!-- Card 3: AI 튜터 질문 수 -->
				<div class={statCard}>
					<div class="flex flex-row justify-between items-center w-full">
						<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" class="text-[#1A1B1C] dark:text-gray-50">
							<mask id="mask0_267_4174" style="mask-type:alpha" maskUnits="userSpaceOnUse" x="0" y="0" width="20" height="20">
								<rect width="20" height="20" fill="currentColor" />
							</mask>
							<g mask="url(#mask0_267_4174)">
								<path d="M11.5 12.5C11.7361 12.5 11.934 12.4201 12.0938 12.2604C12.2535 12.1007 12.3333 11.9028 12.3333 11.6667C12.3333 11.4306 12.2535 11.2326 12.0938 11.0729C11.934 10.9132 11.7361 10.8333 11.5 10.8333C11.2639 10.8333 11.066 10.9132 10.9062 11.0729C10.7465 11.2326 10.6667 11.4306 10.6667 11.6667C10.6667 11.9028 10.7465 12.1007 10.9062 12.2604C11.066 12.4201 11.2639 12.5 11.5 12.5ZM11.5058 9.95833C11.6547 9.95833 11.7882 9.90278 11.9062 9.79167C12.0243 9.68056 12.0972 9.53833 12.125 9.365C12.1528 9.205 12.2014 9.0625 12.2708 8.9375C12.3403 8.8125 12.4722 8.65972 12.6667 8.47917C13.1111 8.04861 13.4097 7.70486 13.5625 7.44792C13.7153 7.19097 13.7917 6.90278 13.7917 6.58333C13.7917 5.95833 13.5833 5.45486 13.1667 5.07292C12.75 4.69097 12.1944 4.5 11.5 4.5C11.0628 4.5 10.6653 4.60069 10.3075 4.80208C9.94972 5.00347 9.65972 5.28472 9.4375 5.64583C9.36806 5.77083 9.36493 5.90972 9.42812 6.0625C9.49118 6.21528 9.59847 6.32639 9.75 6.39583C9.88889 6.45139 10.0278 6.45833 10.1667 6.41667C10.3056 6.375 10.4236 6.28472 10.5208 6.14583C10.6319 5.99306 10.7743 5.87153 10.9479 5.78125C11.1215 5.69097 11.308 5.64583 11.5073 5.64583C11.826 5.64583 12.0851 5.73611 12.2844 5.91667C12.4837 6.09722 12.5833 6.33333 12.5833 6.625C12.5833 6.81944 12.5243 7.00347 12.4062 7.17708C12.2882 7.35069 12.0139 7.63889 11.5833 8.04167C11.3333 8.27778 11.1667 8.48264 11.0833 8.65625C11 8.82986 10.9444 9.0625 10.9167 9.35417C10.9028 9.51528 10.9535 9.65625 11.0688 9.77708C11.184 9.89792 11.3297 9.95833 11.5058 9.95833ZM6.5 15C6.0875 15 5.73438 14.8531 5.44062 14.5594C5.14687 14.2656 5 13.9125 5 13.5V3.5C5 3.0875 5.14687 2.73438 5.44062 2.44063C5.73438 2.14688 6.0875 2 6.5 2H16.5C16.9125 2 17.2656 2.14688 17.5594 2.44063C17.8531 2.73438 18 3.0875 18 3.5V13.5C18 13.9125 17.8531 14.2656 17.5594 14.5594C17.2656 14.8531 16.9125 15 16.5 15H6.5ZM6.5 13.5H16.5V3.5H6.5V13.5ZM3.5 18C3.0875 18 2.73438 17.8531 2.44063 17.5594C2.14688 17.2656 2 16.9125 2 16.5V5.75C2 5.5375 2.07146 5.35937 2.21438 5.21562C2.35729 5.07187 2.53437 5 2.74562 5C2.95687 5 3.13542 5.07187 3.28125 5.21562C3.42708 5.35937 3.5 5.5375 3.5 5.75V16.5H14.25C14.4625 16.5 14.6406 16.5715 14.7844 16.7144C14.9281 16.8573 15 17.0344 15 17.2456C15 17.4569 14.9281 17.6354 14.7844 17.7812C14.6406 17.9271 14.4625 18 14.25 18H3.5Z" fill="currentColor" />
							</g>
						</svg>
						<span class="text-caption {stats.aiTutorQuestions.increased >= 0 ? 'text-[#34BE89]' : 'text-[#FF4D6A]'}">
							{stats.aiTutorQuestions.increased >= 0 ? '+' : ''} 이번 주 {Math.abs(stats.aiTutorQuestions.increased)}개 {stats.aiTutorQuestions.increased >= 0 ? '증가' : '감소'}
						</span>
					</div>
					<div class="flex flex-row justify-between items-center w-full">
						<span class="text-body-3 text-[#1A1B1C] dark:text-gray-50">{stats.aiTutorQuestions.label}</span>
						<span class="text-title-1 text-[#1A1B1C] dark:text-gray-50 tracking-[-0.02em]">{stats.aiTutorQuestions.value}</span>
					</div>
				</div>
			</div>
		{/if}
	</div>

	<!-- 자주 묻는 개념 Section (Figma: gap 20px between title and cards) -->
	<div class="flex flex-col justify-center items-start gap-5 w-full max-w-[920px]">
		<!-- Section Title (Figma: 24px, 600 weight, line-height 36px) -->
		<h2 class="text-title-2 text-gray-950 dark:text-gray-50 tracking-[-0.02em]">자주 묻는 개념</h2>

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
		{:else if topTags.length === 0}
			<div class="{conceptCardCollapsed}">
				<span class="text-body-3 text-gray-500">데이터가 없습니다.</span>
			</div>
		{:else}
			{#each topTags as tag, index (tag.id)}
			<button
				class={expandedCards[index] ? conceptCardExpanded : conceptCardCollapsed}
				on:click={() => handleCardToggle(tag.id, index)}
			>
				<!-- Header Row (Figma: space-between, align center) -->
				<div class="flex flex-row justify-between items-center w-full">
					<!-- Left: Tag Name (Figma: gap 8px) -->
					<div class="flex flex-col items-start gap-2 flex-1 min-w-0">
						<!-- Figma: Body/3/500 - 16px, 500 weight -->
						<span class="text-body-3-medium text-gray-950 dark:text-gray-50 text-left">{tag.name}</span>
						<!-- Chapter Name if exists -->
						{#if tag.chapter_name}
							<span class="text-caption text-[#8D96AD]">
								{tag.chapter_name}
							</span>
						{/if}
					</div>

					<!-- Right: Question Count and Chevron (Figma: gap 16px) -->
					<div class="flex flex-row items-center gap-4 shrink-0 ml-4">
						<!-- Question count (Figma: gap 4px) -->
						<div class="flex flex-row items-center gap-1">
							<!-- Figma: Body/3/400 - 16px, 400 weight, color #596172 -->
							<span class="text-body-3 text-[#596172]">질문</span>
							<!-- Figma: Title/1 - 28px, 600 weight -->
							<span class="text-title-1 text-gray-950 dark:text-gray-50 tracking-[-0.02em]">{tag.usage_count}</span>
						</div>
						<!-- Chevron Icon (Figma: 20x20) -->
						<svg
							width="20"
							height="20"
							viewBox="0 0 20 20"
							fill="none"
							xmlns="http://www.w3.org/2000/svg"
							class="transition-transform duration-200 {expandedCards[index] ? 'rotate-180' : ''}"
						>
							<path d="M10 12.5L5 7.5H15L10 12.5Z" fill="currentColor" class="text-gray-950 dark:text-gray-50"/>
						</svg>
					</div>
				</div>

				<!-- Expandable Content (Figma: gap 24px) -->
				{#if expandedCards[index]}
					<div transition:slide={{ duration: 200 }} class="flex flex-col gap-6 w-full">
						<!-- Divider (Figma: border 1px solid rgba(206, 212, 229, 0.2)) -->
						<div class="w-full h-0 border-t border-[rgba(206,212,229,0.2)]"></div>

						<!-- User Count Info -->
						{#if tagMessagesCache[tag.id]}
							<div class="flex flex-row items-center gap-1">
								<!-- Tag Icon (Figma: 20x20, color #8D96AD) -->
								<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" class="text-[#8D96AD]">
									<path d="M3.33333 10.8333L10.8333 3.33333H16.6667V9.16667L9.16667 16.6667L3.33333 10.8333Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
									<circle cx="13.3333" cy="6.66667" r="1.25" fill="currentColor"/>
								</svg>
								<!-- Figma: Caption/1 - 12px, 400 weight, color #8D96AD -->
								<span class="text-caption text-[#8D96AD]">
									{tagMessagesCache[tag.id].unique_users}명의 사용자
								</span>
							</div>
						{/if}

						<!-- Messages List (Figma: gap 8px between items) -->
						<div class="flex flex-col items-start gap-2 w-full">
							{#if loadingTagMessages[tag.id]}
								<div class="flex items-center gap-2 text-gray-500">
									<svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
										<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
										<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
									</svg>
									<span class="text-body-4">로딩 중...</span>
								</div>
							{:else if tagMessagesCache[tag.id]?.messages}
								{#each tagMessagesCache[tag.id].messages as message}
									<button
										class="flex flex-row justify-between items-center w-full gap-6 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg px-2 py-1 -mx-2 transition-colors text-left"
										on:click|stopPropagation={() => openMessagePreview(message, tag.name)}
									>
										<!-- Figma: Body/4/400 - 14px, 400 weight, color #1A1B1C -->
										<span class="text-body-4 text-[#1A1B1C] dark:text-gray-50 flex-1 truncate">
											{message.summary || '(요약 없음)'}
										</span>
										<!-- Figma: Body/4/400 - 14px, 400 weight, color #596172 -->
										<span class="text-body-4 text-[#596172] shrink-0">{message.user_name}</span>
									</button>
								{/each}
							{:else}
								<span class="text-body-4 text-gray-500">메시지가 없습니다.</span>
							{/if}
						</div>
					</div>
				{/if}
			</button>
			{/each}
		{/if}
	</div>
</div>

<!-- Message Preview Modal -->
<MessagePreviewModal
	bind:show={showMessagePreview}
	message={selectedMessage}
	tagName={selectedTagName}
/>
