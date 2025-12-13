<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { marked } from 'marked';

	import { onMount, getContext, tick, createEventDispatcher } from 'svelte';
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
		currentChatPage
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

	export let onSelect = (e) => {};
	export let onChange = (e) => {};

	export let toolServers = [];

	let models = [];
	let selectedModelIdx = 0;

	// API로부터 받아온 추천 질문들
	let personalSuggestions: any[] = [];
	let allSuggestions: any[] = [];
	let isLoadingSuggestions = true;

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
	});

	$: if (selectedModels.length > 0) {
		selectedModelIdx = models.length - 1;
	}

	$: models = selectedModels.map((id) => $_models.find((m) => m.id === id));
</script>

<div class="m-auto w-full max-w-6xl px-2 @2xl:px-20 text-center relative bg-contain bg-center bg-no-repeat min-h-screen flex flex-col items-center justify-center" style="background-image: url('/assets/images/bg_chat_placeholder.png');">
	{#if $temporaryChatEnabled}
		<Tooltip
			content={$i18n.t("This chat won't appear in history and your messages will not be saved.")}
			className="w-full flex justify-center mb-0.5"
			placement="top"
		>
			<div class="flex items-center gap-2 text-gray-500 text-base my-2 w-fit">
				<EyeSlash strokeWidth="2.5" className="size-4" />{$i18n.t('Temporary Chat')}
			</div>
		</Tooltip>
	{/if}

	<div
		class="w-full text-3xl text-gray-800 dark:text-gray-100 text-center flex items-center gap-4 font-primary"
	>
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
				<div class="flex flex-col justify-center gap-3 @sm:gap-3.5 w-fit px-5 max-w-xl">
					<!-- <div class="flex shrink-0 justify-center">
						<div class="flex -space-x-4 mb-0.5" in:fade={{ duration: 100 }}>
							{#each models as model, modelIdx}
								<Tooltip
									content={(models[modelIdx]?.info?.meta?.tags ?? [])
										.map((tag) => tag.name.toUpperCase())
										.join(', ')}
									placement="top"
								>
									<button
										aria-hidden={models.length <= 1}
										aria-label={$i18n.t('Get information on {{name}} in the UI', {
											name: models[modelIdx]?.name
										})}
										on:click={() => {
											selectedModelIdx = modelIdx;
										}}
									>
										<img
											src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${model?.id}&lang=${$i18n.language}`}
											class=" size-9 @sm:size-10 rounded-full border-[1px] border-gray-100 dark:border-none"
											aria-hidden="true"
											draggable="false"
										/>
									</button>
								</Tooltip>
							{/each}
						</div>
					</div> -->

					<!-- <div
						class=" text-3xl @sm:text-3xl line-clamp-1 flex items-center"
						in:fade={{ duration: 100 }}
					>
						{#if models[selectedModelIdx]?.name}
							<Tooltip
								content={models[selectedModelIdx]?.name}
								placement="top"
								className=" flex items-center "
							>
								<span class="line-clamp-1">
									{models[selectedModelIdx]?.name}
									
								</span>
							</Tooltip>
						{:else}
							{$i18n.t('Hello, {{name}}', { name: $user?.name })}
						{/if}
					</div> -->
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

	{#if $selectedFolder}
		<div
			class="mx-auto px-4 md:max-w-3xl md:px-6 font-primary min-h-62"
			in:fade={{ duration: 200, delay: 200 }}
		>
			<FolderPlaceholder folder={$selectedFolder} />
		</div>
	{:else}
		<div class="mx-auto max-w-5xl font-primary mt-2" in:fade={{ duration: 200, delay: 200 }}>
			<div class="text-title-4 text-gray-900 dark:text-gray-50 mt-8">
				이번 주 취약 개념 Top 3
			</div>
			<div class="mx-5">
				<Suggestions
					suggestionPrompts={personalSuggestions}
					inputValue={prompt}
					{onSelect}
				/>
			</div>
			<div class="mx-5">
				<Suggestions
					suggestionPrompts={allSuggestions}
					inputValue={prompt}
					suggestionTitle={$i18n.t('전체 학생')}
					{onSelect}
				/>
			</div>
		</div>
	{/if}
</div>
