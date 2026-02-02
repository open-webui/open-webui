<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { marked } from 'marked';
	import { onMount, getContext, tick, createEventDispatcher } from 'svelte';

	import { config, user, models as _models, temporaryChatEnabled } from '$lib/stores';
	import { sanitizeResponseContent } from '$lib/utils';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import Suggestions from './Suggestions.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EyeSlash from '$lib/components/icons/EyeSlash.svelte';
	import MessageInput from './MessageInput.svelte';

	const dispatch = createEventDispatcher();
	const i18n: any = getContext('i18n');

	/* -----------------------------
	   Props
	----------------------------- */
	export let transparentBackground = false;
	export let createMessagePair: Function;
	export let stopResponse: Function;
	export let autoScroll = false;

	export let atSelectedModel: any;
	export let selectedModels: string[] = [];
	export let history;

	export let prompt = '';
	export let files: any[] = [];

	export let selectedToolIds: any[] = [];
	export let imageGenerationEnabled = false;
	export let codeInterpreterEnabled = false;
	export let webSearchEnabled = false;

	export let toolServers: any[] = [];

	/* -----------------------------
	   Models
	----------------------------- */
	let models: any[] = [];
	let selectedModelIdx = 0;

	$: models = selectedModels.map((id) => $_models.find((m) => m.id === id));
	$: if (selectedModels.length > 0) selectedModelIdx = models.length - 1;

	let selectedModelsForInput: any = selectedModels;
	$: selectedModelsForInput = selectedModels;

	/* -----------------------------
	   ✅ VISIBILITY CONTROL (FINAL)
	----------------------------- */
	let inputActive = false;
	let userInteracted = false;

	// Only show after REAL user interaction
	$: showSuggestions = userInteracted && (inputActive || prompt.length > 0);

	/* -----------------------------
	   Suggestion helpers
	----------------------------- */
	const getSuggestionPrompts = (meta: any) => meta?.suggestion_prompts;

	const selectSuggestionPrompt = async (p: string) => {
		let text = p;

		if (p.includes('{{CLIPBOARD}}')) {
			const clipboardText = await navigator.clipboard.readText().catch(() => {
				toast.error($i18n.t('Failed to read clipboard contents'));
				return '{{CLIPBOARD}}';
			});
			text = p.replaceAll('{{CLIPBOARD}}', clipboardText);
		}

		prompt = text;
		await tick();

		const chatInputElement = document.getElementById('chat-input');
		chatInputElement?.focus();
		chatInputElement?.dispatchEvent(new Event('input'));
	};

	onMount(() => {
		// 🔒 Force hidden on first load
		inputActive = false;
		userInteracted = false;
	});
</script>

<!-- =====================================================
     PAGE WRAPPER
===================================================== -->
<div class="m-auto w-full max-w-6xl px-2 @2xl:px-20 py-24 text-center">

	{#if $temporaryChatEnabled}
		<Tooltip
			content={$i18n.t('This chat won’t appear in history and your messages will not be saved.')}
			className="w-full flex justify-center mb-2"
			placement="top"
		>
			<div class="flex items-center gap-2 text-gray-500 font-medium text-sm">
				<EyeSlash strokeWidth="2.5" className="size-4" />
				{$i18n.t('Temporary Chat')}
			</div>
		</Tooltip>
	{/if}

	<!-- HEADER -->
	<div class="flex flex-col items-center justify-center text-center font-primary">
		<img
			src={`${WEBUI_BASE_URL}/static/favicon.png`}
			alt="Copai Logo"
			class="w-14 h-14 mb-4"
			draggable="false"
		/>

		<h1 class="text-3xl @sm:text-4xl font-semibold text-gray-900 dark:text-gray-100">
			Welcome to Copai
		</h1>

		<p class="mt-2 text-sm text-gray-500 dark:text-gray-400 max-w-md">
			Start by scripting a task, and let the chat take over.
		</p>

		<p class="text-sm text-gray-500 dark:text-gray-400">
			Not sure where to start?
		</p>
	</div>

	<!-- =====================================================
	     INPUT + SUGGESTIONS (FINAL, STABLE)
	===================================================== -->
	<div
		class="mt-10 w-full flex flex-col-reverse items-center text-left"
		on:focusin={() => {
			inputActive = true;
			userInteracted = true;
		}}
		on:click={() => {
			inputActive = true;
			userInteracted = true;
		}}    
		on:keydown={() => (userInteracted = true)}
	>

		<!-- INPUT -->
		<div class="w-full @md:max-w-3xl py-3">
			<MessageInput
				{history}
				selectedModels={selectedModelsForInput}
				bind:files
				bind:prompt
				bind:autoScroll
				bind:selectedToolIds
				bind:imageGenerationEnabled
				bind:codeInterpreterEnabled
				bind:webSearchEnabled
				bind:atSelectedModel
				{toolServers}
				{transparentBackground}
				{stopResponse}
				{createMessagePair}
				placeholder={$i18n.t('How can I help you today?')}
				on:upload={(e) => dispatch('upload', e.detail)}
				on:submit={(e) => dispatch('submit', e.detail)}
			/>
		</div>

		<!-- 🔒 RESERVED SPACE (NO SHIFT EVER) -->
		<div class="mx-auto max-w-2xl w-full min-h-[220px]">
			<div
				class="transition-opacity duration-200"
				style="
					opacity: {showSuggestions ? 1 : 0};
					pointer-events: {showSuggestions ? 'auto' : 'none'};
				"
			>
				<div class="mx-5">
					<Suggestions
						suggestionPrompts={
							getSuggestionPrompts(atSelectedModel?.info?.meta) ??
							getSuggestionPrompts(models[selectedModelIdx]?.info?.meta) ??
							$config?.default_prompt_suggestions ??
							[]
						}
						inputValue={prompt}
						on:select={(e) => selectSuggestionPrompt(e.detail)}
					/>
				</div>
			</div>
		</div>

	</div>
</div>
