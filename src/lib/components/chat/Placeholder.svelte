<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { marked } from 'marked';

	import { onMount, onDestroy, getContext, tick, createEventDispatcher } from 'svelte';
	import { blur, fade } from 'svelte/transition';

	const dispatch = createEventDispatcher();

	import { getChatList } from '$lib/apis/chats';
	import { updateFolderById } from '$lib/apis/folders';

	import {
		config,
		user,
		models as _models,
		temporaryChatEnabled,
		selectedFolder,
		chats,
		currentChatPage,
		mobile
	} from '$lib/stores';
	import { sanitizeResponseContent, extractCurlyBraceWords } from '$lib/utils';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

	import Suggestions from './Suggestions.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EyeSlash from '$lib/components/icons/EyeSlash.svelte';
	import MessageInput from './MessageInput.svelte';
	import FolderPlaceholder from './Placeholder/FolderPlaceholder.svelte';
	import FolderTitle from './Placeholder/FolderTitle.svelte';

	const i18n = getContext('i18n');

	export let createMessagePair: Function;
	export let stopResponse: Function;

	export let autoScroll = false;

	export let atSelectedModel: Model | undefined;
	export let selectedModels: [''];

	export let history;

	export let prompt = '';
	export let files = [];
	export let messageInput = null;

	export let selectedToolIds = [];
	export let selectedFilterIds = [];

	export let showCommands = false;

	export let imageGenerationEnabled = false;
	export let codeInterpreterEnabled = false;
	export let webSearchEnabled = false;

	export let proficiencyLevel = '2';  // 기본값: 중급
	export let responseStyle = 'diagnosis';  // 기본값: 학생 진단 브리핑

	export let onSelect = (e) => {};
	export let onChange = (e) => {};

	export let toolServers = [];

	let models = [];
	let selectedModelIdx = 0;

	// Sticky 상태 감지
	let isStuck = false;
	let sentinelElement: HTMLDivElement;
	let observer: IntersectionObserver;

	// API로부터 받아온 추천 질문들
	let personalSuggestions: any[] = [];
	let allSuggestions: any[] = [];
	let isLoadingSuggestions = true;

	// 캐러셀 상태
	let currentCarouselIndex = 0; // 0: 개인별 진도, 1: 전체 학생
	let carouselInterval = null;
	const CAROUSEL_INTERVAL_MS = 10000; // 10초

	// 캐러셀 자동 전환 시작
	function startCarouselAutoPlay() {
		stopCarouselAutoPlay();
		carouselInterval = setInterval(() => {
			currentCarouselIndex = (currentCarouselIndex + 1) % 2;
		}, CAROUSEL_INTERVAL_MS);
	}

	// 캐러셀 자동 전환 중지
	function stopCarouselAutoPlay() {
		if (carouselInterval) {
			clearInterval(carouselInterval);
			carouselInterval = null;
		}
	}

	// 사용자 interaction 시 타이머 리셋
	function resetCarouselTimer() {
		startCarouselAutoPlay();
	}

	// 이전 슬라이드로 이동
	function goToPrevSlide() {
		currentCarouselIndex = currentCarouselIndex === 0 ? 1 : 0;
		resetCarouselTimer();
	}

	// 다음 슬라이드로 이동
	function goToNextSlide() {
		currentCarouselIndex = (currentCarouselIndex + 1) % 2;
		resetCarouselTimer();
	}

	// 캐러셀 라벨
	const carouselLabels = ['개인별 진도', '전체 학생'];

	// API 응답을 Suggestions 컴포넌트 형식으로 변환
	function transformApiResponse(recommendations: any[]): any[] {
		return recommendations.map((item) => ({
			id: item.id,
			content: item.question,
			title: [item.subsection_title, item.section_title]
		}));
	}

	// 기본 fallback prompts 가져오기
	function getFallbackPrompts() {
		return (
			atSelectedModel?.info?.meta?.suggestion_prompts ??
			models[selectedModelIdx]?.info?.meta?.suggestion_prompts ??
			$config?.default_prompt_suggestions ??
			[]
		);
	}

	// 개인화된 추천 질문 API 호출
	async function fetchPersonalRecommendations() {
		try {
			const response = await fetch(
				`${WEBUI_API_BASE_URL}/textbook/recommendations?k=3&shuffle=true`,
				{
					headers: {
						Authorization: `Bearer ${localStorage.token}`,
						'Content-Type': 'application/json'
					}
				}
			);
			if (!response.ok) throw new Error('Failed to fetch personal recommendations');
			const data = await response.json();
			return transformApiResponse(data);
		} catch (error) {
			console.error('Error fetching personal recommendations:', error);
			return null;
		}
	}

	// 전체 추천 질문 API 호출
	async function fetchAllRecommendations() {
		try {
			const response = await fetch(
				`${WEBUI_API_BASE_URL}/textbook/recommendations?k=3&shuffle=true`,
				{
					headers: {
						Authorization: `Bearer ${localStorage.token}`,
						'Content-Type': 'application/json'
					}
				}
			);
			if (!response.ok) throw new Error('Failed to fetch all recommendations');
			const data = await response.json();
			return transformApiResponse(data);
		} catch (error) {
			console.error('Error fetching all recommendations:', error);
			return null;
		}
	}

	onMount(async () => {
		isLoadingSuggestions = true;

		// 병렬로 두 API 호출
		const [personal, all] = await Promise.all([
			fetchPersonalRecommendations(),
			fetchAllRecommendations()
		]);

		// API 성공 시 사용, 실패 시 fallback
		const fallback = getFallbackPrompts();
		personalSuggestions = personal ?? fallback;
		allSuggestions = all ?? fallback;

		isLoadingSuggestions = false;

		// 캐러셀 자동 전환 시작
		startCarouselAutoPlay();

		// Sticky 감지를 위한 IntersectionObserver 설정 (DOM 준비 후)
		await tick();
		if ($mobile && sentinelElement) {
			observer = new IntersectionObserver(
				([entry]) => {
					// sentinel이 보이지 않으면 sticky 상태
					isStuck = !entry.isIntersecting;
				},
				{ threshold: 0 }
			);
			observer.observe(sentinelElement);
		}
	});

	onDestroy(() => {
		if (observer) {
			observer.disconnect();
		}
		stopCarouselAutoPlay();
	});

	$: if (selectedModels.length > 0) {
		selectedModelIdx = models.length - 1;
	}

	$: models = selectedModels.map((id) => $_models.find((m) => m.id === id));
</script>

{#if $mobile}
	<!-- ==================== MOBILE LAYOUT ==================== -->
	<div
		class="h-screen flex flex-col bg-contain bg-center bg-no-repeat overflow-hidden"
		style="background-image: url('/assets/images/bg_chat_placeholder.png');"
	>
		<!-- Inner scroll container (padding applied here to avoid overflow) -->
		<div class="pt-[60px] flex-1 overflow-y-auto scrollbar-none">
			<!-- Content area -->
			<div class="flex flex-col items-center">
				<!-- Spacer -->
				<div class="h-[10vh] w-full shrink-0"></div>

			<!-- Header section with welcome text and input -->
			<div class="px-3 pt-4 pb-3 w-full max-w-2xl">
				{#if $temporaryChatEnabled}
					<Tooltip
						content={$i18n.t("This chat won't appear in history and your messages will not be saved.")}
						className="w-full flex justify-center mb-0.5"
						placement="top"
					>
						<div class="flex items-center gap-2 text-gray-500 text-base my-2 w-fit mx-auto">
							<EyeSlash strokeWidth="2.5" className="size-4" />{$i18n.t('Temporary Chat')}
						</div>
					</Tooltip>
				{/if}

				{#if $selectedFolder}
					<FolderTitle
						folder={$selectedFolder}
						onUpdate={async (folder) => {
							await chats.set(await getChatList(localStorage.token, $currentChatPage));
							currentChatPage.set(1);
						}}
						onDelete={async () => {
							await chats.set(await getChatList(localStorage.token, $currentChatPage));
							currentChatPage.set(1);
							selectedFolder.set(null);
						}}
					/>
				{:else}
					<div class="flex flex-col justify-center gap-1 w-full text-center">
						<div class="text-body-4-medium text-gray-900 dark:text-gray-50">
							안녕하세요! 공업수학 AI 튜터입니다.
						</div>
						<div class="text-title-4 text-gray-900 dark:text-gray-50">
							궁금한 것이 있으시면 언제든지 물어보세요.
						</div>
					</div>
				{/if}

				<div class="text-base font-normal w-full py-2 {atSelectedModel ? 'mt-2' : ''}">
					<MessageInput
						bind:this={messageInput}
						{history}
						{selectedModels}
						bind:files
						bind:prompt
						bind:autoScroll
						bind:selectedToolIds
						bind:selectedFilterIds
						bind:imageGenerationEnabled
						bind:codeInterpreterEnabled
						bind:webSearchEnabled
						bind:proficiencyLevel
						bind:responseStyle
						bind:atSelectedModel
						bind:showCommands
						{toolServers}
						{stopResponse}
						{createMessagePair}
						placeholder={$i18n.t('How can I help you today?')}
						{onChange}
						on:upload={(e) => {
							dispatch('upload', e.detail);
						}}
						on:submit={(e) => {
							dispatch('submit', e.detail);
						}}
					/>
				</div>
			</div>
			<!-- End of header -->

			<!-- Mobile: Suggestions section -->
			{#if $selectedFolder}
				<div class="w-full max-w-2xl px-3 font-primary min-h-62" in:fade={{ duration: 200, delay: 200 }}>
					<FolderPlaceholder folder={$selectedFolder} />
				</div>
			{:else}
				<div class="w-full max-w-2xl font-primary pb-8 px-3 overflow-x-hidden" in:fade={{ duration: 200, delay: 200 }}>
					<!-- 제목 -->
					<div class="text-title-3 text-gray-900 dark:text-gray-50 mt-4 text-center">
						이번 주 자주 묻는 질문 TOP 3
					</div>

					<!-- 캐러셀 네비게이션 -->
					<div class="flex flex-row justify-center items-center gap-10 mt-5">
						<!-- 이전 버튼 -->
						<button
							class="w-5 h-5 flex items-center justify-center text-[#B4BCD0] hover:text-gray-50 transition-colors"
							on:click={goToPrevSlide}
							aria-label="이전"
						>
							<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
								<path d="M12.5 15L7.5 10L12.5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
							</svg>
						</button>

						<!-- 현재 슬라이드 라벨 -->
						<span class="text-body-3-medium text-gray-900 dark:text-gray-50 min-w-[80px] text-center">
							{carouselLabels[currentCarouselIndex]}
						</span>

						<!-- 다음 버튼 -->
						<button
							class="w-5 h-5 flex items-center justify-center text-[#B4BCD0] hover:text-gray-50 transition-colors"
							on:click={goToNextSlide}
							aria-label="다음"
						>
							<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
								<path d="M7.5 5L12.5 10L7.5 15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
							</svg>
						</button>
					</div>

					<!-- 캐러셀 콘텐츠 -->
					<Suggestions
						suggestionPrompts={currentCarouselIndex === 0 ? personalSuggestions : allSuggestions}
						inputValue={prompt}
						suggestionTitle=""
						isPersonalized={currentCarouselIndex === 0}
						{onSelect}
					/>
				</div>
			{/if}
			</div>
			<!-- End of content area -->
		</div>
		<!-- End of inner scroll container -->
	</div>
	<!-- End of mobile container -->
{:else}
	<!-- ==================== DESKTOP LAYOUT ==================== -->
	<div
		class="h-screen flex flex-col bg-contain bg-center bg-no-repeat flex-1"
		style="background-image: url('/assets/images/bg_chat_placeholder.png');"
	>
		<!-- Scrollable content area -->
		<div class="flex-1 overflow-y-auto scrollbar-hidden flex flex-col items-center">
			<!-- Spacer to position input at vertical center initially -->
			<div class="h-[25vh] w-full shrink-0"></div>

			<!-- Sticky header section with welcome text and input -->
			<div class="sticky top-0 z-30 px-4 pt-6 pb-4 transition-all duration-200 w-full max-w-6xl">
				{#if $temporaryChatEnabled}
					<Tooltip
						content={$i18n.t("This chat won't appear in history and your messages will not be saved.")}
						className="w-full flex justify-center mb-0.5"
						placement="top"
					>
						<div class="flex items-center gap-2 text-gray-500 text-base my-2 w-fit mx-auto">
							<EyeSlash strokeWidth="2.5" className="size-4" />{$i18n.t('Temporary Chat')}
						</div>
					</Tooltip>
				{/if}

				<div class="w-full text-3xl text-gray-800 dark:text-gray-100 text-center flex items-center gap-4 font-primary">
					<div class="w-full flex flex-col justify-center items-center">
						{#if $selectedFolder}
							<FolderTitle
								folder={$selectedFolder}
								onUpdate={async (folder) => {
									await chats.set(await getChatList(localStorage.token, $currentChatPage));
									currentChatPage.set(1);
								}}
								onDelete={async () => {
									await chats.set(await getChatList(localStorage.token, $currentChatPage));
									currentChatPage.set(1);
									selectedFolder.set(null);
								}}
							/>
						{:else}
							<div class="flex flex-col justify-center gap-1  w-fit px-5 max-w-xl">
								<div class="text-body-2 text-gray-900 dark:text-gray-50">
									안녕하세요! 공업수학 AI 튜터입니다.
								</div>
								<div class="text-title-1 text-gray-900 dark:text-gray-50">
									궁금한 것이 있으시면 언제든지 물어보세요.
								</div>
							</div>

							<div class="flex mt-1 mb-2">
								<div in:fade={{ duration: 100, delay: 50 }}>
									{#if models[selectedModelIdx]?.info?.meta?.description ?? null}
										<Tooltip
											className=" w-fit"
											content={marked.parse(
												sanitizeResponseContent(
													models[selectedModelIdx]?.info?.meta?.description ?? ''
												).replaceAll('\n', '<br>')
											)}
											placement="top"
										>
											<div
												class="mt-0.5 px-2 text-sm font-normal text-gray-500 dark:text-gray-400 line-clamp-2 max-w-xl markdown"
											>
												{@html marked.parse(
													sanitizeResponseContent(
														models[selectedModelIdx]?.info?.meta?.description ?? ''
													).replaceAll('\n', '<br>')
												)}
											</div>
										</Tooltip>

										{#if models[selectedModelIdx]?.info?.meta?.user}
											<div class="mt-0.5 text-sm font-normal text-gray-400 dark:text-gray-500">
												By
												{#if models[selectedModelIdx]?.info?.meta?.user.community}
													<a
														href="https://openwebui.com/m/{models[selectedModelIdx]?.info?.meta?.user
															.username}"
														>{models[selectedModelIdx]?.info?.meta?.user.name
															? models[selectedModelIdx]?.info?.meta?.user.name
															: `@${models[selectedModelIdx]?.info?.meta?.user.username}`}</a
													>
												{:else}
													{models[selectedModelIdx]?.info?.meta?.user.name}
												{/if}
											</div>
										{/if}
									{/if}
								</div>
							</div>
						{/if}

						<div class="text-base font-normal @md:max-w-4xl w-full py-3 {atSelectedModel ? 'mt-2' : ''}">
							<MessageInput
								bind:this={messageInput}
								{history}
								{selectedModels}
								bind:files
								bind:prompt
								bind:autoScroll
								bind:selectedToolIds
								bind:selectedFilterIds
								bind:imageGenerationEnabled
								bind:codeInterpreterEnabled
								bind:webSearchEnabled
								bind:proficiencyLevel
								bind:responseStyle
								bind:atSelectedModel
								bind:showCommands
								{toolServers}
								{stopResponse}
								{createMessagePair}
								placeholder={$i18n.t('How can I help you today?')}
								{onChange}
								on:upload={(e) => {
									dispatch('upload', e.detail);
								}}
								on:submit={(e) => {
									dispatch('submit', e.detail);
								}}
							/>
						</div>
					</div>
				</div>
			</div>
			<!-- End of sticky header -->

			<!-- Scrollable suggestions section -->
			{#if $selectedFolder}
				<div
					class="w-full max-w-3xl px-4 md:px-6 font-primary min-h-62 pb-8"
					in:fade={{ duration: 200, delay: 200 }}
				>
					<FolderPlaceholder folder={$selectedFolder} />
				</div>
			{:else}
				<div class="w-full max-w-5xl font-primary mt-2 pb-8 px-4 overflow-x-hidden" in:fade={{ duration: 200, delay: 200 }}>
					<!-- 제목 -->
					<div class="text-title-3 text-gray-900 dark:text-gray-50 mt-8 text-center">
						이번 주 자주 묻는 질문 TOP 3
					</div>

					<!-- 캐러셀 네비게이션 -->
					<div class="flex flex-row justify-center items-center gap-10 mt-7">
						<!-- 이전 버튼 -->
						<button
							class="w-5 h-5 flex items-center justify-center text-gray-800 dark:text-gray-200 hover:text-gray-50 hover:bg-gray-600 rounded-md  transition-colors"
							on:click={goToPrevSlide}
							aria-label="이전"
						>
							<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
								<path d="M12.5 15L7.5 10L12.5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
							</svg>
						</button>

						<!-- 현재 슬라이드 라벨 -->
						<span class="text-body-3-medium text-gray-900 dark:text-gray-50 min-w-[80px] text-center">
							{carouselLabels[currentCarouselIndex]}
						</span>

						<!-- 다음 버튼 -->
						<button
							class="w-5 h-5 flex items-center justify-center  text-gray-800 dark:text-gray-200 hover:text-gray-50 hover:bg-gray-600 rounded-md transition-colors"
							on:click={goToNextSlide}
							aria-label="다음"
						>
							<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
								<path d="M7.5 5L12.5 10L7.5 15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
							</svg>
						</button>
					</div>

					<!-- 캐러셀 콘텐츠 -->
					<Suggestions
						suggestionPrompts={currentCarouselIndex === 0 ? personalSuggestions : allSuggestions}
						inputValue={prompt}
						suggestionTitle=""
						isPersonalized={currentCarouselIndex === 0}
						{onSelect}
					/>
				</div>
			{/if}
		</div>
		<!-- End of scrollable content area -->
	</div>
	<!-- End of desktop container -->
{/if}

<style>
	/* Hide scrollbar for Chrome, Safari, Edge, Opera */
	.scrollbar-hidden::-webkit-scrollbar {
		display: none;
	}

	/* Hide scrollbar for Firefox */
	.scrollbar-hidden {
		scrollbar-width: none;
	}

	/* Hide scrollbar for IE and Edge Legacy */
	.scrollbar-hidden {
		-ms-overflow-style: none;
	}
</style>
