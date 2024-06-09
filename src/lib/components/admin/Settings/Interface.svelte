<script lang="ts">
	import { getBackendConfig } from '$lib/apis';
	import { setDefaultPromptSuggestions } from '$lib/apis/configs';
	import { config, models, settings, user } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	let taskModel = '';
	let taskModelExternal = '';

	let titleGenerationPrompt = '';
	let promptSuggestions = [];

	const updateInterfaceHandler = async () => {
		promptSuggestions = await setDefaultPromptSuggestions(localStorage.token, promptSuggestions);
		await config.set(await getBackendConfig());
	};

	onMount(async () => {
		taskModel = $settings?.title?.model ?? '';
		taskModelExternal = $settings?.title?.modelExternal ?? '';
		titleGenerationPrompt =
			$settings?.title?.prompt ??
			`Create a concise, 3-5 word phrase as a header for the following query, strictly adhering to the 3-5 word limit and avoiding the use of the word 'title': {{prompt}}`;

		promptSuggestions = $config?.default_prompt_suggestions;
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		updateInterfaceHandler();
		dispatch('save');
	}}
>
	<div class=" space-y-3 pr-1.5 overflow-y-scroll">
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
					<div class=" text-xs mb-1">{$i18n.t('Local Models')}</div>
					<select
						class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
						bind:value={taskModel}
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
					<div class=" text-xs mb-1">{$i18n.t('External Models')}</div>
					<select
						class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
						bind:value={taskModelExternal}
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
				<div class="flex flex-col gap-1.5">
					{#each promptSuggestions as prompt, promptIdx}
						<div class=" flex dark:bg-gray-850 rounded-xl py-1.5">
							<div class="flex flex-col flex-1 pl-1">
								<div class="flex border-b dark:border-gray-800 w-full">
									<input
										class="px-3 py-1.5 text-xs w-full bg-transparent outline-none border-r dark:border-gray-800"
										placeholder={$i18n.t('Title (e.g. Tell me a fun fact)')}
										bind:value={prompt.title[0]}
									/>

									<input
										class="px-3 py-1.5 text-xs w-full bg-transparent outline-none border-r dark:border-gray-800"
										placeholder={$i18n.t('Subtitle (e.g. about the Roman Empire)')}
										bind:value={prompt.title[1]}
									/>
								</div>

								<input
									class="px-3 py-1.5 text-xs w-full bg-transparent outline-none border-r dark:border-gray-800"
									placeholder={$i18n.t('Prompt (e.g. Tell me a fun fact about the Roman Empire)')}
									bind:value={prompt.content}
								/>
							</div>

							<button
								class="px-3"
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
