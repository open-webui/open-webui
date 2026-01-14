<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { marked } from 'marked';

	import { goto } from '$app/navigation';
	import { onMount, getContext, tick, createEventDispatcher } from 'svelte';
	import { blur, fade } from 'svelte/transition';

	const dispatch = createEventDispatcher();

	import { getChatList } from '$lib/apis/chats';
	import { updateFolderById } from '$lib/apis/folders';

	import {
		config,
		models as _models,
		temporaryChatEnabled,
		selectedFolder,
	} from '$lib/stores';

	import Suggestions from './Suggestions.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EyeSlash from '$lib/components/icons/EyeSlash.svelte';
	import MessageInput from './MessageInput.svelte';
	import FolderPlaceholder from './Placeholder/FolderPlaceholder.svelte';
	import QuestionMarkCircle from '../icons/QuestionMarkCircle.svelte';

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

	$: if (selectedModels.length > 0) {
		selectedModelIdx = models.length - 1;
	}

	$: models = selectedModels.map((id) => $_models.find((m) => m.id === id));
</script>

<div class="m-auto w-full max-w-6xl px-2 @2xl:px-20 translate-y-6 py-24 text-center">
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

			<div class="flex items-center justify-between gap-4 w-full max-w-3xl px-2">
					
				<Tooltip 
				className="flex items-center justify-center rounded-full p-2 text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white transition"
				content={$i18n.t("How to Ask Luxor")}>
					<button
						type="button"
						aria-label={$i18n.t('How to Ask Luxor')}
						on:click={() => goto('/how-to-ask')}
					>
						<QuestionMarkCircle className="size-5" />
					</button>
				</Tooltip>
				

				<div class="flex flex-row items-center justify-center flex-1 gap-2">
					<img
						src="/static/favicon.png"
						class="size-16 rounded-full border border-gray-100 dark:border-gray-800"
						alt="Model icon"
						draggable="false"
					/>
					<h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-100">
						{$i18n.t("Hello")}
					</h1>
				</div>

				<div class="w-8" />
			</div>
				
				

			<div class="text-base font-normal @md:max-w-3xl w-full py-3 {atSelectedModel ? 'mt-2' : ''}">
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
		<div class="mx-auto max-w-2xl font-primary mt-2" in:fade={{ duration: 200, delay: 200 }}>
			<div class="mx-5">
				<Suggestions
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
