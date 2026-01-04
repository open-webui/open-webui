<script lang="ts">
	import Bolt from '$lib/components/icons/Bolt.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { onMount, getContext } from 'svelte';
	import { settings, WEBUI_NAME, mobile, user } from '$lib/stores';
	import { WEBUI_VERSION } from '$lib/constants';
	import {
		getMyTopTags,
		getGlobalTopTags,
		setTagFeedback,
		type TagWithFeedback,
		type FeedbackStatus
	} from '$lib/apis/message-tags';
	import { fade, fly } from 'svelte/transition';
	import { flip } from 'svelte/animate';

	const i18n = getContext('i18n');

	export let suggestionTitle = '개인별 진도';
	export let className = '';
	export let onSelect = (e) => {};
	export let isPersonalized = true; // true: 개인화 (my-tags), false: 전체 유저 (global-tags)

	let topTags: TagWithFeedback[] = [];
	let loading = false;
	let initialLoad = true; // 초기 로딩 여부
	let cachedPersonalTags: TagWithFeedback[] = [];
	let cachedGlobalTags: TagWithFeedback[] = [];

	onMount(() => {
		loadTopTags();
	});

	// isPersonalized가 변경될 때마다 데이터 다시 로드
	$: if (isPersonalized !== undefined && !initialLoad) {
		loadTopTagsSmooth();
	}

	async function loadTopTags() {
		if (!$user?.token) return;

		loading = true;
		try {
			// isPersonalized에 따라 다른 API 호출
			const tags = isPersonalized
				? await getMyTopTags($user.token, 3)
				: await getGlobalTopTags($user.token, 3);
			if (tags) {
				topTags = tags;
				// 캐시 저장
				if (isPersonalized) {
					cachedPersonalTags = tags;
				} else {
					cachedGlobalTags = tags;
				}
			}
		} catch (err) {
			console.error('Failed to load top tags:', err);
		}
		loading = false;
		initialLoad = false;
	}

	// 부드러운 전환을 위한 로딩 함수
	async function loadTopTagsSmooth() {
		if (!$user?.token) return;

		// 캐시된 데이터가 있으면 즉시 표시
		const cachedData = isPersonalized ? cachedPersonalTags : cachedGlobalTags;
		if (cachedData.length > 0) {
			topTags = cachedData;
		}

		// 백그라운드에서 새 데이터 로드
		try {
			const tags = isPersonalized
				? await getMyTopTags($user.token, 3)
				: await getGlobalTopTags($user.token, 3);
			if (tags) {
				// 캐시 업데이트
				if (isPersonalized) {
					cachedPersonalTags = tags;
				} else {
					cachedGlobalTags = tags;
				}
				
				// 데이터가 변경되었으면 부드럽게 업데이트
				topTags = tags;
			}
		} catch (err) {
			console.error('Failed to load top tags:', err);
		}
		loading = false;
	}

	async function handleFeedback(tagId: string, status: FeedbackStatus) {
		if (!$user?.token) return;

		try {
			// 1. 낙관적 업데이트: 피드백 상태를 먼저 로컬에서 업데이트
			const updatedIndex = topTags.findIndex(t => t.id === tagId);
			if (updatedIndex !== -1) {
				topTags[updatedIndex].feedback_status = status;
				topTags = [...topTags]; // 반응성 트리거
			}

			// 2. 서버에 피드백 저장
			await setTagFeedback($user.token, tagId, status);

			// 3. 백그라운드에서 새 목록 가져오기
			const newTags = isPersonalized
				? await getMyTopTags($user.token, 3)
				: await getGlobalTopTags($user.token, 3);

			if (newTags) {
				// 4. 기존 태그와 새 태그를 비교하여 부드럽게 업데이트
				const existingIds = new Set(topTags.map(t => t.id));
				const newIds = new Set(newTags.map(t => t.id));
				
				// 제거된 태그 필터링
				topTags = topTags.filter(t => newIds.has(t.id));
				
				// 새로운 태그 추가
				const tagsToAdd = newTags.filter(t => !existingIds.has(t.id));
				topTags = [...topTags, ...tagsToAdd];
				
				// 서버 순서대로 정렬
				const orderMap = new Map(newTags.map((t, i) => [t.id, i]));
				topTags.sort((a, b) => (orderMap.get(a.id) || 0) - (orderMap.get(b.id) || 0));
			}
		} catch (err) {
			console.error('Failed to set feedback:', err);
		}
	}

	const handlePractice = (tag: TagWithFeedback) => {
		onSelect({ type: 'prompt', data: `${tag.name}에 대해 설명해주세요.` });
	};
</script>

{#if suggestionTitle}
	<div
		class="mb-1 flex gap-1 text-xs font-medium items-center text-gray-600 dark:text-gray-400 w-full justify-center mt-6"
	>
		{#if topTags.length > 0 || loading}
			<!-- <Bolt /> -->
			<p class="text-body-3-medium text-[#1A1B1C] dark:text-gray-50">{suggestionTitle}</p>
			<!-- {$i18n.t('Suggested')} -->
		{:else}
			<!-- Keine Vorschläge -->

			<div
				class="flex w-full {$settings?.landingPageMode === 'chat'
					? ' -mt-1'
					: 'text-center items-center justify-center'}  self-start text-gray-600 dark:text-gray-400"
			>
				{$WEBUI_NAME} ‧ v{WEBUI_VERSION}
			</div>
		{/if}
	</div>
{/if}

<div class="w-full py-4">
	{#if loading}
		<div class="flex justify-center items-center py-8">
			<div class="animate-spin rounded-full h-6 w-6 border-b-2 border-gray-500"></div>
		</div>
	{:else if topTags.length > 0}
		<div
			role="list"
			class="{$mobile
				? 'flex flex-col gap-4 px-4'
				: 'flex flex-row gap-4 overflow-x-hidden scrollbar-thin px-12 pb-4'} {className}"
		>
			{#each topTags as tag (tag.id)}
				<div
					class="box-border flex flex-col items-start p-5 gap-2.5
						{$mobile ? 'w-full' : 'min-w-[270px] w-[270px]'}
						bg-[rgba(253,254,254,0.7)] dark:bg-[rgba(39,40,44,0.5)]
						shadow-lg rounded-xl backdrop-blur-[20px]"
					in:fly={{ x: 100, duration: 400, delay: 100 }}
					out:fly={{ x: -100, duration: 300 }}
					animate:flip={{ duration: 400 }}
				>
					<!-- Usage Count Info -->
					<!-- <div class="flex items-center gap-1">
						<svg
							width="20"
							height="20"
							viewBox="0 0 20 20"
							fill="none"
							xmlns="http://www.w3.org/2000/svg"
							class="tag-icon"
						>
							<path
								d="M9.5 3L3 9.5L10.5 17L17 10.5L9.5 3Z"
								class="stroke-[#596172] dark:stroke-[#B4BCD0]"
								stroke-width="1.5"
								stroke-linecap="round"
								stroke-linejoin="round"
							/>
							<circle cx="7" cy="7" r="1.5" class="fill-[#596172] dark:fill-[#B4BCD0]" />
						</svg>
						<span class="text-xs text-[#596172] dark:text-[#B4BCD0]">{tag.usage_count}회 학습</span>
					</div> -->

					<!-- Content -->
					<div class="flex flex-col gap-2">
						<div
							class="text-base font-medium text-[#1A1B1C] dark:text-white w-full overflow-hidden truncate max-w-[240px]"
						>
							{tag.name}
						</div>
						<div class="text-caption text-gray-500 flex flex-row items-center gap-1">
							<svg
								width="20"
								height="20"
								viewBox="0 0 20 20"
								fill="none"
								xmlns="http://www.w3.org/2000/svg"
							>
								<mask
									id="mask0_497_8992"
									style="mask-type:alpha"
									maskUnits="userSpaceOnUse"
									x="0"
									y="0"
									width="20"
									height="20"
								>
									<rect width="20" height="20" fill="#D9D9D9" />
								</mask>
								<g mask="url(#mask0_497_8992)">
									<path
										d="M5.33333 14C6.01972 14 6.68785 14.0764 7.33771 14.2292C7.98757 14.3819 8.625 14.5972 9.25 14.875V5.41667C8.65278 5.09722 8.03104 4.86458 7.38479 4.71875C6.73868 4.57292 6.08549 4.5 5.42521 4.5C4.91951 4.5 4.41667 4.54167 3.91667 4.625C3.41667 4.70833 2.94444 4.86097 2.5 5.08292V14.5C2.94444 14.3056 3.40625 14.1736 3.88542 14.1042C4.36458 14.0347 4.84722 14 5.33333 14ZM10.75 14.875C11.375 14.5972 12.0124 14.3819 12.6623 14.2292C13.3122 14.0764 13.9803 14 14.6667 14C15.1528 14 15.6354 14.0347 16.1146 14.1042C16.5938 14.1736 17.0556 14.3056 17.5 14.5V5.08333C17.0139 4.90278 16.5105 4.76042 15.9898 4.65625C15.4691 4.55208 14.9447 4.5 14.4167 4.5C13.7778 4.5 13.1528 4.57986 12.5417 4.73958C11.9306 4.89931 11.3333 5.125 10.75 5.41667V14.875ZM10 16.8542C9.81944 16.8542 9.65625 16.8125 9.51042 16.7292C9.36458 16.6458 9.21375 16.5625 9.05792 16.4792C8.50542 16.1597 7.92375 15.9167 7.31292 15.75C6.70194 15.5833 6.07681 15.5 5.4375 15.5C4.99306 15.5 4.54514 15.5278 4.09375 15.5833C3.64236 15.6389 3.20833 15.7569 2.79167 15.9375C2.36111 16.1319 1.95486 16.1562 1.57292 16.0104C1.19097 15.8646 1 15.6042 1 15.2292V4.75C1 4.55556 1.05556 4.37847 1.16667 4.21875C1.27778 4.05903 1.41667 3.93056 1.58333 3.83333C2.16667 3.5 2.78042 3.27778 3.42458 3.16667C4.06875 3.05556 4.72583 3 5.39583 3C6.20139 3 6.96875 3.08333 7.69792 3.25C8.42708 3.41667 9.19444 3.70833 10 4.125C10.8056 3.70833 11.5729 3.41667 12.3021 3.25C13.0313 3.08333 13.7986 3 14.6042 3C15.2218 3 15.8276 3.05208 16.4217 3.15625C17.0156 3.26042 17.5833 3.4375 18.125 3.6875C18.3611 3.79861 18.5694 3.94097 18.75 4.11458C18.9306 4.28819 19.0208 4.5 19.0208 4.75V15.2292C19.0208 15.5625 18.8576 15.8056 18.5312 15.9583C18.2049 16.1111 17.8542 16.1181 17.4792 15.9792C16.9931 15.7986 16.4965 15.6736 15.9896 15.6042C15.4826 15.5347 14.9722 15.5 14.4583 15.5C13.8381 15.5 13.2316 15.5799 12.639 15.7396C12.0463 15.8993 11.4861 16.1458 10.9583 16.4792C10.8056 16.5764 10.6512 16.6632 10.4954 16.7396C10.3396 16.816 10.1744 16.8542 10 16.8542ZM11.75 7.02083C11.75 6.82639 11.809 6.65278 11.9271 6.5C12.0451 6.34722 12.2014 6.25 12.3958 6.20833C12.7431 6.13889 13.0851 6.08333 13.4219 6.04167C13.7588 6 14.1131 5.97917 14.4848 5.97917C14.7172 5.97917 14.9571 5.99076 15.2046 6.01396C15.4521 6.03701 15.6964 6.06708 15.9375 6.10417C16.1042 6.13194 16.2396 6.21208 16.3438 6.34458C16.4479 6.47708 16.5 6.62611 16.5 6.79167C16.5 7.02778 16.4167 7.22222 16.25 7.375C16.0833 7.52778 15.8819 7.58826 15.6458 7.55646C15.4514 7.53271 15.2583 7.51042 15.0667 7.48958C14.875 7.46875 14.6802 7.45833 14.4823 7.45833C14.1608 7.45833 13.8507 7.47569 13.5521 7.51042C13.2535 7.54514 12.9522 7.60326 12.6483 7.68479C12.4106 7.75604 12.2014 7.72222 12.0208 7.58333C11.8403 7.44444 11.75 7.25694 11.75 7.02083ZM11.7917 11.9167C11.7917 11.7222 11.8507 11.5486 11.9688 11.3958C12.0868 11.2431 12.2431 11.1458 12.4375 11.1042C12.7847 11.0347 13.1267 10.9792 13.4635 10.9375C13.8005 10.8958 14.1548 10.875 14.5265 10.875C14.7588 10.875 14.9987 10.8866 15.2463 10.9098C15.4938 10.9328 15.7381 10.9629 15.9792 11C16.1458 11.0278 16.2812 11.1079 16.3854 11.2404C16.4896 11.3729 16.5417 11.5219 16.5417 11.6875C16.5417 11.9236 16.4583 12.1181 16.2917 12.2708C16.125 12.4236 15.9236 12.4841 15.6875 12.4523C15.4931 12.4285 15.3 12.4062 15.1083 12.3854C14.9167 12.3646 14.7219 12.3542 14.524 12.3542C14.2024 12.3542 13.8924 12.3715 13.5938 12.4062C13.2951 12.441 12.9939 12.4991 12.69 12.5806C12.4522 12.6519 12.2431 12.6181 12.0625 12.4792C11.8819 12.3403 11.7917 12.1528 11.7917 11.9167ZM11.7917 9.47917C11.7917 9.28472 11.8507 9.11111 11.9688 8.95833C12.0868 8.80556 12.2431 8.70833 12.4375 8.66667C12.7847 8.59722 13.1267 8.54167 13.4635 8.5C13.8005 8.45833 14.1548 8.4375 14.5265 8.4375C14.7588 8.4375 14.9987 8.4491 15.2463 8.47229C15.4938 8.49535 15.7381 8.52542 15.9792 8.5625C16.1458 8.59028 16.2812 8.67042 16.3854 8.80292C16.4896 8.93542 16.5417 9.08444 16.5417 9.25C16.5417 9.48611 16.4583 9.68056 16.2917 9.83333C16.125 9.98611 15.9236 10.0466 15.6875 10.0148C15.4931 9.99104 15.3 9.96875 15.1083 9.94792C14.9167 9.92708 14.7219 9.91667 14.524 9.91667C14.2024 9.91667 13.8924 9.93403 13.5938 9.96875C13.2951 10.0035 12.9939 10.0616 12.69 10.1431C12.4522 10.2144 12.2431 10.1806 12.0625 10.0417C11.8819 9.90278 11.7917 9.71528 11.7917 9.47917Z"
										fill="#8D96AD"
									/>
								</g>
							</svg>
							<div class="text-caption text-gray-500 flex flex-row items-center gap-1 overflow-hidden truncate max-w-[180px]">{tag.chapter_name}</div>
						</div>
						
					</div>

					<!-- Divider -->
					<div
						class="border-t w-full h-0 border-[rgba(206,212,229,0.2)] dark:border-gray-500/30"
					></div>

					<!-- Action Buttons -->
					<div class="flex items-center justify-between w-full">
						<!-- Left: Feedback buttons -->
						<!-- Feedback Status Badge -->
						{#if tag.feedback_status}
							<div class="flex items-center gap-1 text-xs">
								{#if tag.feedback_status === 'understood'}
									<span
										class="px-2 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 rounded-full"
										>이해함</span
									>
								{:else if tag.feedback_status === 'confused'}
									<span
										class="px-2 py-0.5 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400 rounded-full"
										>잘 모르겠음</span
									>
								{:else if tag.feedback_status === 'not_interested'}
									<span
										class="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 rounded-full"
										>관심없음</span
									>
								{/if}
							</div>
						{/if}


						<div class="flex gap-1">
							<!-- 이해함 -->
							<Tooltip content="이해함" placement="bottom">
								<button
									class="w-7 h-7 p-0 border-none rounded-full cursor-pointer flex items-center justify-center transition-all duration-200 hover:scale-110 active:scale-95
										{tag.feedback_status === 'understood'
										? 'bg-green-100 dark:bg-green-900/50'
										: 'bg-transparent hover:bg-gray-100 dark:hover:bg-gray-700'}"
									on:click|stopPropagation={() =>
										handleFeedback(
											tag.id,
											tag.feedback_status === 'understood' ? null : 'understood'
										)}
									aria-label="이해함"
								>
									<svg
										width="16"
										height="16"
										viewBox="0 0 16 16"
										fill="none"
										xmlns="http://www.w3.org/2000/svg"
									>
										<circle cx="8" cy="8" r="6" stroke="#34BE89" stroke-width="1.5" />
										<path
											d="M5 8L7 10L11 6"
											stroke="#34BE89"
											stroke-width="1.5"
											stroke-linecap="round"
											stroke-linejoin="round"
										/>
									</svg>
								</button>
							</Tooltip>
							<!-- 잘 모르겠음 -->
							<!-- <Tooltip content="잘 모르겠음" placement="bottom">
								<button
									class="w-7 h-7 p-0 border-none rounded-full cursor-pointer flex items-center justify-center transition-all duration-200 hover:scale-110 active:scale-95
										{tag.feedback_status === 'confused' ? 'bg-yellow-100 dark:bg-yellow-900/50' : 'bg-transparent hover:bg-gray-100 dark:hover:bg-gray-700'}"
									on:click|stopPropagation={() => handleFeedback(tag.id, tag.feedback_status === 'confused' ? null : 'confused')}
									aria-label="잘 모르겠음"
								>
									<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
										<circle cx="8" cy="8" r="6" stroke="#F59E0B" stroke-width="1.5" />
										<path d="M6.5 6.5C6.5 5.67 7.17 5 8 5C8.83 5 9.5 5.67 9.5 6.5C9.5 7.33 8.83 8 8 8V9" stroke="#F59E0B" stroke-width="1.5" stroke-linecap="round" />
										<circle cx="8" cy="11" r="0.75" fill="#F59E0B" />
									</svg>
								</button>
							</Tooltip> -->
							<!-- 관심없음 -->
							<!-- <Tooltip content="관심없음" placement="bottom">
								<button
									class="w-7 h-7 p-0 border-none rounded-full cursor-pointer flex items-center justify-center transition-all duration-200 hover:scale-110 active:scale-95
										{tag.feedback_status === 'not_interested' ? 'bg-gray-200 dark:bg-gray-600' : 'bg-transparent hover:bg-gray-100 dark:hover:bg-gray-700'}"
									on:click|stopPropagation={() => handleFeedback(tag.id, tag.feedback_status === 'not_interested' ? null : 'not_interested')}
									aria-label="관심없음"
								>
									<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
										<circle cx="8" cy="8" r="6" stroke="#6B7280" stroke-width="1.5" />
										<path d="M5 8H11" stroke="#6B7280" stroke-width="1.5" stroke-linecap="round" />
									</svg>
								</button>
							</Tooltip> -->
						</div>

						<!-- Right: Practice button -->
						<button
							class="flex flex-row items-center py-1 pl-4 pr-3 gap-1 bg-[#076EF4] rounded-full border-none cursor-pointer
								font-['Pretendard',sans-serif] font-normal text-sm leading-[21px] text-[#FDFEFE]
								transition-all duration-200 hover:bg-[#0558c7] hover:-translate-y-px active:translate-y-0"
							on:click={() => handlePractice(tag)}
						>
							<span>복습하기</span>
							<svg
								width="20"
								height="20"
								viewBox="0 0 20 20"
								fill="none"
								xmlns="http://www.w3.org/2000/svg"
							>
								<path
									d="M7 4L13 10L7 16"
									stroke="#FDFEFE"
									stroke-width="2"
									stroke-linecap="round"
									stroke-linejoin="round"
								/>
							</svg>
						</button>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	/* Scrollbar styling */
	:global(.scrollbar-thin) {
		scrollbar-width: thin;
		scrollbar-color: rgba(113, 122, 143, 0.3) transparent;
	}

	:global(.scrollbar-thin::-webkit-scrollbar) {
		height: 6px;
	}

	:global(.scrollbar-thin::-webkit-scrollbar-track) {
		background: transparent;
	}

	:global(.scrollbar-thin::-webkit-scrollbar-thumb) {
		background-color: rgba(113, 122, 143, 0.3);
		border-radius: 3px;
	}

	:global(.scrollbar-thin::-webkit-scrollbar-thumb:hover) {
		background-color: rgba(113, 122, 143, 0.5);
	}
</style>
