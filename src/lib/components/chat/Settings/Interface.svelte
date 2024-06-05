<script lang="ts">
	import { getBackendConfig } from '$lib/apis';
	import { setDefaultPromptSuggestions } from '$lib/apis/configs';
	import { config, models, settings, user } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let saveSettings: Function;

	// Addons
	let titleAutoGenerate = true;
	let responseAutoCopy = false;
	let titleAutoGenerateModel = '';
	let titleAutoGenerateModelExternal = '';
	let widescreenMode = false;
	let titleGenerationPrompt = '';
	let splitLargeChunks = false;

	// Interface
	let defaultModelId = '';
	let promptSuggestions = [];
	let showUsername = false;
	let chatBubble = true;
	let chatDirection: 'LTR' | 'RTL' = 'LTR';

	const toggleSplitLargeChunks = async () => {
		splitLargeChunks = !splitLargeChunks;
		saveSettings({ splitLargeChunks: splitLargeChunks });
	};

	const togglewidescreenMode = async () => {
		widescreenMode = !widescreenMode;
		saveSettings({ widescreenMode: widescreenMode });
	};

	const toggleChatBubble = async () => {
		chatBubble = !chatBubble;
		saveSettings({ chatBubble: chatBubble });
	};

	const toggleShowUsername = async () => {
		showUsername = !showUsername;
		saveSettings({ showUsername: showUsername });
	};

	const toggleTitleAutoGenerate = async () => {
		titleAutoGenerate = !titleAutoGenerate;
		saveSettings({
			title: {
				...$settings.title,
				auto: titleAutoGenerate
			}
		});
	};

	const toggleResponseAutoCopy = async () => {
		const permission = await navigator.clipboard
			.readText()
			.then(() => {
				return 'granted';
			})
			.catch(() => {
				return '';
			});

		console.log(permission);

		if (permission === 'granted') {
			responseAutoCopy = !responseAutoCopy;
			saveSettings({ responseAutoCopy: responseAutoCopy });
		} else {
			toast.error(
				'Clipboard write permission denied. Please check your browser settings to grant the necessary access.'
			);
		}
	};

	const toggleChangeChatDirection = async () => {
		chatDirection = chatDirection === 'LTR' ? 'RTL' : 'LTR';
		saveSettings({ chatDirection });
	};

	const updateInterfaceHandler = async () => {
		if ($user.role === 'admin') {
			promptSuggestions = await setDefaultPromptSuggestions(localStorage.token, promptSuggestions);
			await config.set(await getBackendConfig());
		}

		saveSettings({
			title: {
				...$settings.title,
				model: titleAutoGenerateModel !== '' ? titleAutoGenerateModel : undefined,
				modelExternal:
					titleAutoGenerateModelExternal !== '' ? titleAutoGenerateModelExternal : undefined,
				prompt: titleGenerationPrompt ? titleGenerationPrompt : undefined
			},
			models: [defaultModelId]
		});
	};

	onMount(async () => {
		if ($user.role === 'admin') {
			promptSuggestions = $config?.default_prompt_suggestions;
		}

		titleAutoGenerate = $settings?.title?.auto ?? true;
		titleAutoGenerateModel = $settings?.title?.model ?? '';
		titleAutoGenerateModelExternal = $settings?.title?.modelExternal ?? '';
		titleGenerationPrompt =
			$settings?.title?.prompt ??
			`Create a concise, 3-5 word phrase as a header for the following query, strictly adhering to the 3-5 word limit and avoiding the use of the word 'title': {{prompt}}`;
		responseAutoCopy = $settings.responseAutoCopy ?? false;
		showUsername = $settings.showUsername ?? false;
		chatBubble = $settings.chatBubble ?? true;
		widescreenMode = $settings.widescreenMode ?? false;
		splitLargeChunks = $settings.splitLargeChunks ?? false;
		chatDirection = $settings.chatDirection ?? 'LTR';

		defaultModelId = ($settings?.models ?? ['']).at(0);
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		updateInterfaceHandler();
		dispatch('save');
	}}
>
	<div class=" space-y-3 pr-1.5 overflow-y-scroll max-h-[25rem]">
		<div>
			<div class=" mb-1 text-sm font-medium">{$i18n.t('WebUI Add-ons')}</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">{$i18n.t('Chat Bubble UI')}</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
						on:click={() => {
							toggleChatBubble();
						}}
						type="button"
					>
						{#if chatBubble === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">{$i18n.t('Title Auto-Generation')}</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
						on:click={() => {
							toggleTitleAutoGenerate();
						}}
						type="button"
					>
						{#if titleAutoGenerate === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Response AutoCopy to Clipboard')}
					</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
						on:click={() => {
							toggleResponseAutoCopy();
						}}
						type="button"
					>
						{#if responseAutoCopy === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">{$i18n.t('Widescreen Mode')}</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
						on:click={() => {
							togglewidescreenMode();
						}}
						type="button"
					>
						{#if widescreenMode === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			{#if !$settings.chatBubble}
				<div>
					<div class=" py-0.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Display the username instead of You in the Chat')}
						</div>

						<button
							class="p-1 px-3 text-xs flex rounded transition"
							on:click={() => {
								toggleShowUsername();
							}}
							type="button"
						>
							{#if showUsername === true}
								<span class="ml-2 self-center">{$i18n.t('On')}</span>
							{:else}
								<span class="ml-2 self-center">{$i18n.t('Off')}</span>
							{/if}
						</button>
					</div>
				</div>
			{/if}

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Fluidly stream large external response chunks')}
					</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
						on:click={() => {
							toggleSplitLargeChunks();
						}}
						type="button"
					>
						{#if splitLargeChunks === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>
		</div>

		<div>
			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs font-medium">{$i18n.t('Chat direction')}</div>

				<button
					class="p-1 px-3 text-xs flex rounded transition"
					on:click={toggleChangeChatDirection}
					type="button"
				>
					{#if chatDirection === 'LTR'}
						<span class="ml-2 self-center">{$i18n.t('LTR')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('RTL')}</span>
					{/if}
				</button>
			</div>
		</div>

		<hr class=" dark:border-gray-850" />

		<div class=" space-y-1 mb-3">
			<div class="mb-2">
				<div class="flex justify-between items-center text-xs">
					<div class=" text-xs font-medium">{$i18n.t('Default Model')}</div>
				</div>
			</div>

			<div class="flex-1 mr-2">
				<select
					class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
					bind:value={defaultModelId}
					placeholder="Select a model"
				>
					<option value="" disabled selected>{$i18n.t('Select a model')}</option>
					{#each $models.filter((model) => model.id) as model}
						<option value={model.id} class="bg-gray-100 dark:bg-gray-700">{model.name}</option>
					{/each}
				</select>
			</div>
		</div>

		<hr class=" dark:border-gray-850" />

		<div>
			<div class=" mb-2.5 text-sm font-medium flex">
				<div class=" mr-1">{$i18n.t('Set Task Model')}</div>
				<Tooltip
					content={$i18n.t(
						'A task model is used when performing tasks such as generating titles for chats and web search queries'
					)}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="1.5"
						stroke="currentColor"
						class="w-5 h-5"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z"
						/>
					</svg>
				</Tooltip>
			</div>
			<div class="flex w-full gap-2 pr-2">
				<div class="flex-1">
					<div class=" text-xs mb-1">Local Models</div>
					<select
						class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
						bind:value={titleAutoGenerateModel}
						placeholder={$i18n.t('Select a model')}
					>
						<option value="" selected>{$i18n.t('Current Model')}</option>
						{#each $models.filter((m) => m.owned_by === 'ollama') as model}
							<option value={model.id} class="bg-gray-100 dark:bg-gray-700">
								{model.name}
							</option>
						{/each}
					</select>
				</div>

				<div class="flex-1">
					<div class=" text-xs mb-1">External Models</div>
					<select
						class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
						bind:value={titleAutoGenerateModelExternal}
						placeholder={$i18n.t('Select a model')}
					>
						<option value="" selected>{$i18n.t('Current Model')}</option>
						{#each $models as model}
							<option value={model.id} class="bg-gray-100 dark:bg-gray-700">
								{model.name}
							</option>
						{/each}
					</select>
				</div>
			</div>

			<div class="mt-3 mr-2">
				<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Title Generation Prompt')}</div>
				<textarea
					bind:value={titleGenerationPrompt}
					class="w-full rounded-lg p-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none resize-none"
					rows="3"
				/>
			</div>
		</div>

		{#if $user.role === 'admin'}
			<hr class=" dark:border-gray-700" />

			<div class=" space-y-3 pr-1.5">
				<div class="flex w-full justify-between mb-2">
					<div class=" self-center text-sm font-semibold">
						{$i18n.t('Default Prompt Suggestions')}
					</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
						type="button"
						on:click={() => {
							if (promptSuggestions.length === 0 || promptSuggestions.at(-1).content !== '') {
								promptSuggestions = [...promptSuggestions, { content: '', title: ['', ''] }];
							}
						}}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z"
							/>
						</svg>
					</button>
				</div>
				<div class="flex flex-col space-y-1">
					{#each promptSuggestions as prompt, promptIdx}
						<div class=" flex border dark:border-gray-600 rounded-lg">
							<div class="flex flex-col flex-1">
								<div class="flex border-b dark:border-gray-600 w-full">
									<input
										class="px-3 py-1.5 text-xs w-full bg-transparent outline-none border-r dark:border-gray-600"
										placeholder={$i18n.t('Title (e.g. Tell me a fun fact)')}
										bind:value={prompt.title[0]}
									/>

									<input
										class="px-3 py-1.5 text-xs w-full bg-transparent outline-none border-r dark:border-gray-600"
										placeholder={$i18n.t('Subtitle (e.g. about the Roman Empire)')}
										bind:value={prompt.title[1]}
									/>
								</div>

								<input
									class="px-3 py-1.5 text-xs w-full bg-transparent outline-none border-r dark:border-gray-600"
									placeholder={$i18n.t('Prompt (e.g. Tell me a fun fact about the Roman Empire)')}
									bind:value={prompt.content}
								/>
							</div>

							<button
								class="px-2"
								type="button"
								on:click={() => {
									promptSuggestions.splice(promptIdx, 1);
									promptSuggestions = promptSuggestions;
								}}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="w-4 h-4"
								>
									<path
										d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
									/>
								</svg>
							</button>
						</div>
					{/each}
				</div>

				{#if promptSuggestions.length > 0}
					<div class="text-xs text-left w-full mt-2">
						{$i18n.t('Adjusting these settings will apply changes universally to all users.')}
					</div>
				{/if}
			</div>
		{/if}
	</div>

	<div class="flex justify-end text-sm font-medium">
		<button
			class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
