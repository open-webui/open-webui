<script lang="ts">
	import { getBackendConfig } from '$lib/apis';
	import { setDefaultPromptSuggestions } from '$lib/apis/configs';
	import { config, models, user } from '$lib/stores';
	import { createEventDispatcher, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	const dispatch = createEventDispatcher();

	export let saveSettings: Function;

	// Addons
	let titleAutoGenerate = true;
	let responseAutoCopy = false;
	let titleAutoGenerateModel = '';
	let fullScreenMode = false;
	let titleGenerationPrompt = '';

	// Interface
	let promptSuggestions = [];
	let showUsername = false;

	const toggleFullScreenMode = async () => {
		fullScreenMode = !fullScreenMode;
		saveSettings({ fullScreenMode: fullScreenMode });
	};

	const toggleShowUsername = async () => {
		showUsername = !showUsername;
		saveSettings({ showUsername: showUsername });
	};

	const toggleTitleAutoGenerate = async () => {
		titleAutoGenerate = !titleAutoGenerate;
		saveSettings({ titleAutoGenerate: titleAutoGenerate });
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

	const updateInterfaceHandler = async () => {
		if ($user.role === 'admin') {
			promptSuggestions = await setDefaultPromptSuggestions(localStorage.token, promptSuggestions);
			await config.set(await getBackendConfig());
		}

		saveSettings({
			titleAutoGenerateModel: titleAutoGenerateModel !== '' ? titleAutoGenerateModel : undefined,
			titleGenerationPrompt: titleGenerationPrompt ? titleGenerationPrompt : undefined
		});
	};

	onMount(async () => {
		if ($user.role === 'admin') {
			promptSuggestions = $config?.default_prompt_suggestions;
		}

		let settings = JSON.parse(localStorage.getItem('settings') ?? '{}');

		titleAutoGenerate = settings.titleAutoGenerate ?? true;
		responseAutoCopy = settings.responseAutoCopy ?? false;
		showUsername = settings.showUsername ?? false;
		fullScreenMode = settings.fullScreenMode ?? false;
		titleAutoGenerateModel = settings.titleAutoGenerateModel ?? '';
		titleGenerationPrompt =
			settings.titleGenerationPrompt ??
			`Create a concise, 3-5 word phrase as a header for the following query, strictly adhering to the 3-5 word limit and avoiding the use of the word 'title': {{prompt}}`;
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		updateInterfaceHandler();
		dispatch('save');
	}}
>
	<div class=" space-y-3 pr-1.5 overflow-y-scroll h-80">
		<div>
			<div class=" mb-1 text-sm font-medium">WebUI Add-ons</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">Title Auto-Generation</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
						on:click={() => {
							toggleTitleAutoGenerate();
						}}
						type="button"
					>
						{#if titleAutoGenerate === true}
							<span class="ml-2 self-center">On</span>
						{:else}
							<span class="ml-2 self-center">Off</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">Response AutoCopy to Clipboard</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
						on:click={() => {
							toggleResponseAutoCopy();
						}}
						type="button"
					>
						{#if responseAutoCopy === true}
							<span class="ml-2 self-center">On</span>
						{:else}
							<span class="ml-2 self-center">Off</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">Full Screen Mode</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
						on:click={() => {
							toggleFullScreenMode();
						}}
						type="button"
					>
						{#if fullScreenMode === true}
							<span class="ml-2 self-center">On</span>
						{:else}
							<span class="ml-2 self-center">Off</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">
						Display the username instead of "You" in the Chat
					</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
						on:click={() => {
							toggleShowUsername();
						}}
						type="button"
					>
						{#if showUsername === true}
							<span class="ml-2 self-center">On</span>
						{:else}
							<span class="ml-2 self-center">Off</span>
						{/if}
					</button>
				</div>
			</div>
		</div>

		<hr class=" dark:border-gray-700" />

		<div>
			<div class=" mb-2.5 text-sm font-medium">Set Title Auto-Generation Model</div>
			<div class="flex w-full">
				<div class="flex-1 mr-2">
					<select
						class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
						bind:value={titleAutoGenerateModel}
						placeholder="Select a model"
					>
						<option value="" selected>Current Model</option>
						{#each $models as model}
							{#if model.size != null}
								<option value={model.name} class="bg-gray-100 dark:bg-gray-700">
									{model.name + ' (' + (model.size / 1024 ** 3).toFixed(1) + ' GB)'}
								</option>
							{/if}
						{/each}
					</select>
				</div>
			</div>
			<div class="mt-3 mr-2">
				<div class=" mb-2.5 text-sm font-medium">Title Generation Prompt</div>
				<textarea
					bind:value={titleGenerationPrompt}
					class="w-full rounded-lg p-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none resize-none"
					rows="3"
				/>
			</div>
		</div>

		{#if $user.role === 'admin'}
			<hr class=" dark:border-gray-700" />

			<div class=" space-y-3 pr-1.5 overflow-y-scroll max-h-80">
				<div class="flex w-full justify-between mb-2">
					<div class=" self-center text-sm font-semibold">Default Prompt Suggestions</div>

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
										placeholder="Title (e.g. Tell me a fun fact)"
										bind:value={prompt.title[0]}
									/>

									<input
										class="px-3 py-1.5 text-xs w-full bg-transparent outline-none border-r dark:border-gray-600"
										placeholder="Subtitle (e.g. about the Roman Empire)"
										bind:value={prompt.title[1]}
									/>
								</div>

								<input
									class="px-3 py-1.5 text-xs w-full bg-transparent outline-none border-r dark:border-gray-600"
									placeholder="Prompt (e.g. Tell me a fun fact about the Roman Empire)"
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
						Adjusting these settings will apply changes universally to all users.
					</div>
				{/if}
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
			type="submit"
		>
			Save
		</button>
	</div>
</form>
