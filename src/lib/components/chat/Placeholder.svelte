<script lang="ts">
	import { marked } from 'marked';

	import { getContext } from 'svelte';
	import { fade } from 'svelte/transition';

	import { getChatList } from '$lib/apis/chats';

	import {
		config,
		user,
		WEBUI_NAME,
		models as _models,
		temporaryChatEnabled,
		selectedFolder,
		chats,
		currentChatPage
	} from '$lib/stores';
	import { sanitizeResponseContent } from '$lib/utils';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EyeSlash from '$lib/components/icons/EyeSlash.svelte';
	import Suggestions from './Suggestions.svelte';
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
	export let selectedSkillIds = [];
	export let selectedFilterIds = [];
	export let pendingOAuthTools = [];

	export let showCommands = false;

	export let imageGenerationEnabled = false;
	export let codeInterpreterEnabled = false;
	export let webSearchEnabled = false;

	export let onUpload: Function = (e) => {};
	export let onSelect = (e) => {};
	export let onChange = (e) => {};

	export let toolServers = [];

	export let dragged = false;

	let models = [];
	let selectedModelIdx = 0;

	$: if (selectedModels.length > 0) {
		selectedModelIdx = models.length - 1;
	}

	$: models = selectedModels.map((id) => $_models.find((m) => m.id === id));
</script>

<div class="mws-placeholder m-auto w-full max-w-4xl px-4 @2xl:px-12 py-10 text-center">
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
				<div class="mws-hero-frame w-full max-w-4xl text-center" in:fade={{ duration: 120 }}>
					<div class="mws-hero-badge mb-4" in:fade={{ duration: 100 }}>
					<img src="{WEBUI_BASE_URL}/static/mws-logo.svg" alt="MWS GPT" class="h-16 w-auto" />
					<span>{$WEBUI_NAME}</span>
					</div>

				<div class="mb-8" in:fade={{ duration: 120, delay: 20 }}>
					<h1 class="text-2xl @sm:text-3xl font-semibold text-gray-800 dark:text-gray-100">
						С чего начнем?
					</h1>
				</div>

				<div class="flex flex-row justify-center gap-3 @sm:gap-3.5 w-fit px-5 max-w-xl mx-auto">
					<div
						class=" text-3xl @sm:text-3xl line-clamp-1 flex items-center"
						in:fade={{ duration: 100 }}
					>
							{#if models[selectedModelIdx]?.name}
								{@const modelName = models[selectedModelIdx]?.name}
								<Tooltip
									content={modelName.toLowerCase() === 'auto' ? $i18n.t('Auto') : modelName}
									placement="top"
									className=" flex items-center "
								>
									<span class="line-clamp-1">
										{modelName.toLowerCase() === 'auto' ? $i18n.t('Auto') : modelName}
									</span>
								</Tooltip>
							{:else}
								{$i18n.t('Hello, {{name}}', { name: $user?.name })}
							{/if}
						</div>
					</div>

					<div class="flex mt-1 mb-2 justify-center">
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
				</div>
			{/if}

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
		<div class="mx-auto max-w-2xl font-primary mt-3" in:fade={{ duration: 200, delay: 200 }}>
			<div class="mx-5">
				<Suggestions
					className="mws-suggestions-grid"
					suggestionPrompts={atSelectedModel?.info?.meta?.suggestion_prompts ??
						models[selectedModelIdx]?.info?.meta?.suggestion_prompts ??
						$config?.default_prompt_suggestions ??
						[]}
					inputValue={prompt}
					{onSelect}
				/>
			</div>
		</div>
	{/if}

</div>
