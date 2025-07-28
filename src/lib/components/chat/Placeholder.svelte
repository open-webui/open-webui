<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { marked } from 'marked';

	import { onMount, getContext, tick, createEventDispatcher } from 'svelte';
	import { blur, fade } from 'svelte/transition';

	const dispatch = createEventDispatcher();

	import { config, user, models as _models, temporaryChatEnabled, clearMessageInput, mobile } from '$lib/stores';
	import { sanitizeResponseContent, extractCurlyBraceWords } from '$lib/utils';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import Suggestions from './Suggestions.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EyeSlash from '$lib/components/icons/EyeSlash.svelte';
	import LogoV4 from '$lib/components/icons/LogoV4.svelte';
	import MessageInput from './MessageInput.svelte';

	const i18n = getContext('i18n');

	export let transparentBackground = false;

	export let createMessagePair: Function;
	export let stopResponse: Function;
	export let saveSessionSelectedModels: Function = () => {};

	export let autoScroll = false;

	export let atSelectedModel: Model | undefined;
	export let selectedModels: [''];

	export let history;

	export let prompt = '';
	export let files = [];

	export let selectedToolIds = [];
	export let selectedFilterIds = [];

	export let imageGenerationEnabled = false;
	export let codeInterpreterEnabled = false;
	export let webSearchEnabled = false;

	export let toolServers = [];

	let models = [];

	const selectSuggestionPrompt = async (p) => {
		let text = p;

		if (p.includes('{{CLIPBOARD}}')) {
			const clipboardText = await navigator.clipboard.readText().catch((err) => {
				toast.error($i18n.t('Failed to read clipboard contents'));
				return '{{CLIPBOARD}}';
			});

			text = p.replaceAll('{{CLIPBOARD}}', clipboardText);

			console.log('Clipboard text:', clipboardText, text);
		}

		prompt = text;

		console.log(prompt);
		await tick();

		const chatInputContainerElement = document.getElementById('chat-input-container');
		const chatInputElement = document.getElementById('chat-input');

		if (chatInputContainerElement) {
			chatInputContainerElement.scrollTop = chatInputContainerElement.scrollHeight;
		}

		await tick();
		if (chatInputElement) {
			chatInputElement.focus();
			chatInputElement.dispatchEvent(new Event('input'));
		}

		await tick();
	};

	let selectedModelIdx = 0;

	$: if (selectedModels.length > 0) {
		selectedModelIdx = models.length - 1;
	}

	$: models = selectedModels.map((id) => $_models.find((m) => m.id === id));

	// Clear message input when starting new conversation from sidebar
	$: if ($clearMessageInput) {
		// Clear input fields
		prompt = '';
		files = [];
		
		// Clear tool and filter selections
		selectedToolIds = [];
		selectedFilterIds = [];
		
		// Reset feature toggles
		webSearchEnabled = false;
		imageGenerationEnabled = false;
		codeInterpreterEnabled = false;
		
		// Reset model selection
		atSelectedModel = undefined;
		
		// Stop any ongoing response generation
		if (stopResponse) {
			stopResponse();
		}
		
		// Reset the store after clearing
		clearMessageInput.set(false);
	}

	$: firstName = $user?.name?.split(' ')[0] ?? 'there';

	onMount(() => {});
</script>

<div class="max-w-[1020px] md:px-4 md:pb-4 w-full mx-auto text-center">
	{#if $temporaryChatEnabled}
		<Tooltip
			content={$i18n.t("This chat won't appear in history and your messages will not be saved.")}
			className="w-full flex justify-center mb-0.5"
			placement="top"
		>
			<div class="flex items-center gap-2 text-gray-500 font-medium text-lg my-2 w-fit">
				<EyeSlash strokeWidth="2.5" className="size-5" />{$i18n.t('Temporary Chat')}
			</div>
		</Tooltip>
	{/if}

	<div
		class="w-full h-full text-3xl text-gray-800 dark:text-gray-100 text-center flex items-center gap-4 font-primary"
	>
		<div class="w-full h-full flex flex-col justify-center items-center">
			<div class="top-box flex-grow flex flex-col justify-center">
				<div class="flex flex-row justify-center">
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
									on:click={() => {
										selectedModelIdx = modelIdx;
									}}
								>
									<img
										crossorigin="anonymous"
										src={model?.info?.meta?.profile_image_url ??
											($i18n.language === 'dg-DG'
												? `/doge.png`
												: `/static/favicon.png`)}
										class=" size-9 @sm:size-10 rounded-full border-[1px] border-gray-100 dark:border-none"
										alt="logo"
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

					<div class="welcome-text">
						{#if !$mobile && !webSearchEnabled}<div class="mb-[110px] flex justify-center">
								<LogoV4 strokeWidth="2.5" className="size-5" />
							</div>{/if}
						<div>
							<h1
								class="pb-[16px] text-typography-titles text-[28px] leading-[22px] font-Inter_SemiBold"
							>
								Hey {firstName} 👋🏼
							</h1>
						</div>
					</div>

					<!--<div class="text-center my-6" in:fade={{ duration: 100 }}>
					{#if models[selectedModelIdx]?.name}
						<Tooltip
							content={models[selectedModelIdx]?.name}
							placement="top"
							className="flex items-center justify-center"
						>
							<h1 class="text-4xl font-bold text-gray-900">
								Welcome to {models[selectedModelIdx].name}
							</h1>
						</Tooltip>
					{/if}

					{#if $user?.name}
						<p class="text-xl text-gray-500 mt-4">
							Hi {$user.name}, how can I help today?
						</p>
					{/if}
				</div>-->
				</div>

				<div class="flex mt-1 mb-2">
					<div in:fade={{ duration: 100, delay: 50 }}>
						{#if models[selectedModelIdx]?.info?.meta?.description ?? null}
							<Tooltip
								className=" w-fit"
								content={marked.parse(
									sanitizeResponseContent(models[selectedModelIdx]?.info?.meta?.description ?? '')
								)}
								placement="top"
							>
								<div
									class="mt-0.5 px-2 text-sm font-normal text-gray-500 dark:text-gray-400 line-clamp-2 max-w-xl markdown"
								>
									{@html marked.parse(
										sanitizeResponseContent(models[selectedModelIdx]?.info?.meta?.description)
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
			</div>

			<div class="suggestion-inputbox w-full">
				{#if !webSearchEnabled}
					<div class="mx-auto font-primary" in:fade={{ duration: 200, delay: 200 }}>
						<div class="">
							<Suggestions
								suggestionPrompts={atSelectedModel?.info?.meta?.suggestion_prompts ??
									models[selectedModelIdx]?.info?.meta?.suggestion_prompts ??
									$config?.default_prompt_suggestions ??
									[]}
								inputValue={prompt}
								on:select={(e) => {
									selectSuggestionPrompt(e.detail);
								}}
							/>
						</div>
					</div>
				{/if}

				<div class="text-base font-normal w-full">
					<MessageInput
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
						{toolServers}
						{transparentBackground}
						{stopResponse}
						{createMessagePair}
						{saveSessionSelectedModels}
						placeholder={$i18n.t('How can I help you today?')}
						onChange={(input) => {
							if (!$temporaryChatEnabled) {
								if (input.prompt !== null) {
									localStorage.setItem(`chat-input`, JSON.stringify(input));
								} else {
									localStorage.removeItem(`chat-input`);
								}
							}
						}}
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
</div>
