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

	const i18n = getContext('i18n');

	export let suggestionTitle = '개인별 진도';
	export let className = '';
	export let onSelect = (e) => {};
	export let isPersonalized = true; // true: 개인화 (my-tags), false: 전체 유저 (global-tags)

	let topTags: TagWithFeedback[] = [];
	let loading = false;

	onMount(() => {
		loadTopTags();
	});

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
			}
		} catch (err) {
			console.error('Failed to load top tags:', err);
		}
		loading = false;
	}

	async function handleFeedback(tagId: string, status: FeedbackStatus) {
		if (!$user?.token) return;

		try {
			await setTagFeedback($user.token, tagId, status);
			await loadTopTags(); // 리프레시
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
		<div role="list" class="{$mobile
			? 'flex flex-col gap-4 px-4'
			: 'flex flex-row gap-4 overflow-x-auto scrollbar-thin px-12 pb-4'} {className}">
			{#each topTags as tag (tag.id)}
				<div
					class="box-border flex flex-col items-start py-3 px-4 gap-2.5
						{$mobile ? 'w-full' : 'min-w-[270px] w-[270px]'}
						bg-[rgba(253,254,254,0.7)] dark:bg-[rgba(39,40,44,0.5)]
						shadow-lg rounded-2xl backdrop-blur-[20px]"
				>
					<!-- Usage Count Info -->
					<div class="flex items-center gap-1">
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
					</div>

					<!-- Content -->
					<div class="flex flex-col gap-2">
						<div class="text-base font-medium text-[#1A1B1C] dark:text-white line-clamp-2 w-full">
							{tag.name}
						</div>
						<!-- Feedback Status Badge -->
						{#if tag.feedback_status}
							<div class="flex items-center gap-1 text-xs">
								{#if tag.feedback_status === 'understood'}
									<span class="px-2 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 rounded-full">이해함</span>
								{:else if tag.feedback_status === 'confused'}
									<span class="px-2 py-0.5 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400 rounded-full">잘 모르겠음</span>
								{:else if tag.feedback_status === 'not_interested'}
									<span class="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 rounded-full">관심없음</span>
								{/if}
							</div>
						{/if}
					</div>

					<!-- Divider -->
					<div class="border-t w-full h-0 border-[rgba(206,212,229,0.2)] dark:border-gray-500/30"></div>

					<!-- Action Buttons -->
					<div class="flex items-center justify-between w-full">
						<!-- Left: Feedback buttons -->
						<div class="flex gap-1">
							<!-- 이해함 -->
							<Tooltip content="이해함" placement="bottom">
								<button
									class="w-7 h-7 p-0 border-none rounded-full cursor-pointer flex items-center justify-center transition-all duration-200 hover:scale-110 active:scale-95
										{tag.feedback_status === 'understood' ? 'bg-green-100 dark:bg-green-900/50' : 'bg-transparent hover:bg-gray-100 dark:hover:bg-gray-700'}"
									on:click|stopPropagation={() => handleFeedback(tag.id, tag.feedback_status === 'understood' ? null : 'understood')}
									aria-label="이해함"
								>
									<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
										<circle cx="8" cy="8" r="6" stroke="#34BE89" stroke-width="1.5" />
										<path d="M5 8L7 10L11 6" stroke="#34BE89" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
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
