<!-- Base on Open WebUI's Placeholder.svelte -->
<script lang="ts">
	import type { Readable } from 'svelte/store';
	import type { I18Next } from '$lib/IONOS/i18next.d.ts';
	import { getContext, createEventDispatcher } from 'svelte';

	import {
		type Model,
		models as modelsStore,
		chats
	} from '$lib/stores';
	import { getUserSettings } from '$lib/apis/users';

	import MessageInput from '$lib/IONOS/components/chat/MessageInput.svelte';
	import SmallAgentSelector from '$lib/IONOS/components/SmallAgentSelector.svelte';
	import TermsHint from '$lib/IONOS/components/TermsHint.svelte';

	const i18n = getContext<Readable<I18Next>>('i18n');

	const dispatch = createEventDispatcher();

	export let transparentBackground = false;

	// eslint-disable-next-line @typescript-eslint/ban-types
	export let createMessagePair: Function;
	// eslint-disable-next-line @typescript-eslint/ban-types
	export let stopResponse: Function;

	export let autoScroll = false;

	export let atSelectedModel: Model | undefined;
	export let selectedModels: [''];

	export let history;

	export let prompt = '';
	export let files = [];

	export let selectedToolIds: string[] = [];
	export let imageGenerationEnabled = false;
	export let webSearchEnabled = false;

	let models = [];

	let selectedModelIdx = 0;

	$: if (selectedModels.length > 0) {
		selectedModelIdx = models.length - 1;
	}

	$: models = selectedModels.map((id) => $modelsStore.find((m) => m.id === id));
	$: agentName = models[selectedModelIdx]?.name ?? '';
	$: placeholder = $i18n.t('Message {{agentName}}', { agentName: agentName, ns: 'ionos' });

	let userSettings = getUserSettings(localStorage.token);
</script>

<div class="m-auto w-full max-w-6xl px-2 xl:px-20 translate-y-6 py-24 text-center">
	<div class="w-full text-3xl text-gray-800 dark:text-gray-100 font-medium text-center flex items-center gap-4 font-primary">
		<div class="w-full flex flex-col justify-center items-center gap-5 md:gap-10">
			<div class="flex flex-row justify-center gap-3 sm:gap-3.5 w-fit px-5">
				<div class="pb-[50px] md:pb-[100px] text-3xl sm:text-5xl leading-[56px] font-overpass text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-purple-700">
					{#if agentName}
							{$i18n.t("I'm {{agentName}},", { agentName, ns: 'ionos' })}
							<br>
							{$i18n.t("What can I help with?", { ns: 'ionos' })}
					{/if}
				</div>
			</div>
			{#if $chats.length < 1 && !userSettings.ui?.ionosAgreedToTerms}
				<div class="xl:translate-x-6 md:max-w-3xl w-full px-2.5">
					<TermsHint />
				</div>
			{/if}
			<div
				class="text-base font-normal xl:translate-x-6 md:max-w-3xl w-full py-3 {atSelectedModel
					? 'mt-2'
					: ''}"
			>
				<MessageInput
					{history}
					{selectedModels}
					bind:files
					bind:prompt
					bind:autoScroll
					bind:selectedToolIds
					bind:imageGenerationEnabled
					bind:webSearchEnabled
					bind:atSelectedModel
					{transparentBackground}
					{stopResponse}
					{createMessagePair}
					placeholder={placeholder}
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

	<div class="mx-auto max-w-3xl font-primary">
		<div class="mx-9 mt-4">
			<SmallAgentSelector
				bind:selectedModels={selectedModels}
			/>
		</div>
	</div>
</div>
