<script lang="ts">
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';

	import { config, user, recentChats, refreshRecentChats } from '$lib/stores';
	import { onMount, getContext } from 'svelte';

	import { blur, fade } from 'svelte/transition';

	import Suggestions from './Suggestions.svelte';
	import RecentChats from './RecentChats.svelte';
	import { sanitizeResponseContent } from '$lib/utils';
	import {
		resolveLocalizedModelDescription,
		resolveLocalizedModelName,
		resolveLocalizedModelPromptSuggestions,
		resolveLocalizedPromptSuggestions
	} from '$lib/utils/localizedContent';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EyeSlash from '$lib/components/icons/EyeSlash.svelte';
	import { getChatContext } from '$lib/components/chat/context';
	import { firstNameOf, getGreeting } from '$lib/utils/greeting';

	const { models: _models, temporary } = getChatContext();

	const i18n: any = getContext('i18n');

	export let modelIds = [];
	export let models = [];
	export let atSelectedModel;

	export let onSelect = (e) => {};

	let mounted = false;
	let selectedModelIdx = 0;
	let selectedModel;
	let selectedModelName = '';
	let selectedModelDescription = '';
	let selectedSuggestionPrompts = [];

	$: if (modelIds.length > 0) {
		selectedModelIdx = models.length - 1;
	}

	$: models = modelIds.map((id) => ($_models ?? []).find((m) => m.id === id));
	$: selectedModel = atSelectedModel ?? models[selectedModelIdx];
	$: selectedModelName = resolveLocalizedModelName(selectedModel, $i18n.language);
	$: selectedModelDescription =
		$config?.license_metadata?.chat_placeholder_description ||
		resolveLocalizedModelDescription(selectedModel, $i18n.language);
	// Time-of-day greeting, unless the model (or license) gives the placeholder a description.
	$: firstName = firstNameOf($user?.name);
	$: showGreeting = !!firstName && !selectedModelDescription;
	$: greeting = getGreeting((key, options) => $i18n.t(key, options), firstName);
	// The model's own suggestions come first, then recent chats, then the default suggestions.
	$: modelSuggestionPrompts =
		resolveLocalizedModelPromptSuggestions(atSelectedModel, $i18n.language) ??
		resolveLocalizedModelPromptSuggestions(models[selectedModelIdx], $i18n.language);
	$: showRecentChats = !modelSuggestionPrompts?.length && ($recentChats?.length ?? 0) > 0;
	// Until recent chats first load, show neither rather than flash the defaults.
	$: waitingForRecentChats = !modelSuggestionPrompts?.length && $recentChats === null;
	$: selectedSuggestionPrompts =
		modelSuggestionPrompts ??
		resolveLocalizedPromptSuggestions(
			$config?.default_prompt_suggestions,
			$config?.default_prompt_suggestions_i18n ?? {},
			$i18n.language,
			(key) => $i18n.t(key)
		);

	onMount(() => {
		mounted = true;
		refreshRecentChats(localStorage.token);
	});
</script>

{#key mounted}
	<div class="m-auto w-full max-w-[58rem] px-8 lg:px-20">
		<div class="flex justify-start" class:hidden={showGreeting}>
			<div class="flex -space-x-4 mb-0.5" in:fade={{ duration: 200 }}>
				{#each models as model, modelIdx}
					<button
						aria-hidden={models.length <= 1}
						tabindex={models.length > 1 ? 0 : -1}
						aria-label={$i18n.t('Get information on {{name}} in the UI', {
							name: resolveLocalizedModelName(model, $i18n.language)
						})}
						on:click={() => {
							selectedModelIdx = modelIdx;
						}}
					>
						<Tooltip
							content={DOMPurify.sanitize(
								marked.parse(
									sanitizeResponseContent(selectedModelDescription).replaceAll('\n', '<br>')
								)
							)}
							allowHTML={true}
							placement="right"
						>
							<img
								src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${model?.id}&lang=${$i18n.language}&v=${model?.info?.updated_at}`}
								class=" size-[2.7rem] rounded-2xl"
								alt=""
								draggable="false"
								on:error={(e) => {
									// LICENSE covers this Open WebUI fallback logo.
									// Do not alter, remove, obscure, or replace it except as LICENSE permits:
									// https://docs.openwebui.com/license.
									e.currentTarget.src = '/favicon.png';
								}}
							/>
						</Tooltip>
					</button>
				{/each}
			</div>
		</div>

		{#if $temporary}
			<Tooltip
				content={$i18n.t("This chat won't appear in history and your messages will not be saved.")}
				className="w-full flex justify-start mb-0.5"
				placement="top"
			>
				<div class="flex items-center gap-1.5 text-base-500 text-xs mt-1 w-fit">
					<EyeSlash strokeWidth="2" className="size-3.5" />{$i18n.t('Temporary Chat')}
				</div>
			</Tooltip>
		{/if}

		<div
			class=" mt-2 mb-4 text-3xl text-base-800 dark:text-base-100 text-left flex items-center gap-4"
		>
			<div>
				<h2 class="line-clamp-1" class:capitalize={!showGreeting} in:fade={{ duration: 200 }}>
					{#if showGreeting}
						{greeting}
					{:else if selectedModelName}
						{selectedModelName}
					{:else}
						{$i18n.t('Hello, {{name}}', { name: $user?.name })}
					{/if}
				</h2>

				<div in:fade={{ duration: 200, delay: 200 }}>
					{#if selectedModelDescription}
						<div
							class="mt-0.5 text-base font-normal text-base-500 dark:text-base-400 line-clamp-3 markdown"
						>
							{@html DOMPurify.sanitize(
								marked.parse(
									sanitizeResponseContent(selectedModelDescription).replaceAll('\n', '<br>')
								)
							)}
						</div>
						{#if models[selectedModelIdx]?.info?.meta?.user && (!models[selectedModelIdx]?.info?.meta?.user.community || $config?.features.enable_community_sharing)}
							<div class="mt-0.5 text-sm font-normal text-base-400 dark:text-base-500">
								{$i18n.t('By')}
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
					{:else}
						<div class=" text-base-400 dark:text-base-500 line-clamp-1 font-p">
							{$i18n.t('How can I help you today?')}
						</div>
					{/if}
				</div>
			</div>
		</div>

		<!-- Held at the height of either list, so the centred block doesn't jump when it arrives. -->
		<div class=" w-full min-h-[10.5rem]" in:fade={{ duration: 200, delay: 300 }}>
			{#if showRecentChats}
				<div in:fade={{ duration: 150 }}>
					<RecentChats chats={$recentChats} showIdentifier={!selectedSuggestionPrompts?.length} />
				</div>
			{:else if !waitingForRecentChats}
				<div in:fade={{ duration: 150 }}>
					<Suggestions
						className="grid grid-cols-2"
						suggestionPrompts={selectedSuggestionPrompts}
						{onSelect}
					/>
				</div>
			{/if}
		</div>
	</div>
{/key}
