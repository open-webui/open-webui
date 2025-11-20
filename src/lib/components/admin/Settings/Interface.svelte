<script lang="ts">
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { v4 as uuidv4 } from 'uuid';
	import { toast } from 'svelte-sonner';

	import { getBackendConfig, getModels, getTaskConfig, updateTaskConfig } from '$lib/apis';
	import { setDefaultPromptSuggestions } from '$lib/apis/configs';
	import { config, settings, user } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext } from 'svelte';

	import { banners as _banners } from '$lib/stores';
	import type { Banner } from '$lib/types';

	import { getBaseModels } from '$lib/apis/models';
	import { getBanners, setBanners } from '$lib/apis/configs';
	import { resetAllUsersInterfaceSettings } from '$lib/apis/users';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Banners from './Interface/Banners.svelte';
	import InterfaceDefaultsModal from './Interface/InterfaceDefaultsModal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	let taskConfig = {
		TASK_MODEL: '',
		TASK_MODEL_EXTERNAL: '',
		ENABLE_TITLE_GENERATION: true,
		TITLE_GENERATION_PROMPT_TEMPLATE: '',
		ENABLE_FOLLOW_UP_GENERATION: true,
		FOLLOW_UP_GENERATION_PROMPT_TEMPLATE: '',
		IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE: '',
		ENABLE_AUTOCOMPLETE_GENERATION: true,
		AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH: -1,
		TAGS_GENERATION_PROMPT_TEMPLATE: '',
		ENABLE_TAGS_GENERATION: true,
		ENABLE_SEARCH_QUERY_GENERATION: true,
		ENABLE_RETRIEVAL_QUERY_GENERATION: true,
		QUERY_GENERATION_PROMPT_TEMPLATE: '',
		TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE: '',
		VOICE_MODE_PROMPT_TEMPLATE: ''
	};

	let promptSuggestions = [];
	let banners: Banner[] = [];

	let showInterfaceDefaultsModal = false;
	let showResetConfirmDialog = false;
	let resettingUsers = false;

	const updateInterfaceHandler = async () => {
		taskConfig = await updateTaskConfig(localStorage.token, taskConfig);

		promptSuggestions = promptSuggestions.filter((p) => p.content !== '');
		promptSuggestions = await setDefaultPromptSuggestions(localStorage.token, promptSuggestions);
		await updateBanners();

		await config.set(await getBackendConfig());
	};

	const updateBanners = async () => {
		_banners.set(await setBanners(localStorage.token, banners));
	};

	const handleResetAllUsers = async () => {
		resettingUsers = true;
		try {
			const result = await resetAllUsersInterfaceSettings(localStorage.token);
			toast.success($i18n.t(`Reset interface settings for ${result.users_reset} users`));
			showResetConfirmDialog = false;
		} catch (error) {
			console.error('Error resetting users:', error);
			toast.error($i18n.t('Failed to reset users\' interface settings'));
		} finally {
			resettingUsers = false;
		}
	};

	let workspaceModels = null;
	let baseModels = null;

	let models = null;

	const init = async () => {
		taskConfig = await getTaskConfig(localStorage.token);
		promptSuggestions = $config?.default_prompt_suggestions ?? [];
		banners = await getBanners(localStorage.token);

		workspaceModels = await getBaseModels(localStorage.token);
		baseModels = await getModels(localStorage.token, null, false);

		models = baseModels.map((m) => {
			const workspaceModel = workspaceModels.find((wm) => wm.id === m.id);

			if (workspaceModel) {
				return {
					...m,
					...workspaceModel
				};
			} else {
				return {
					...m,
					id: m.id,
					name: m.name,

					is_active: true
				};
			}
		});

		console.debug('models', models);
	};

	onMount(async () => {
		await init();
	});
</script>

<InterfaceDefaultsModal bind:show={showInterfaceDefaultsModal} />

<ConfirmDialog
	bind:show={showResetConfirmDialog}
	on:confirm={handleResetAllUsers}
>
	<div class="text-sm text-gray-500 dark:text-gray-300">
		<div class="font-bold text-red-600 dark:text-red-500 mb-2">
			{$i18n.t('Warning: This action is irreversible!')}
		</div>
		<div class="mb-2">
			{$i18n.t(
				'This will reset ALL users\' interface settings to the admin-configured defaults. Users who have customized their settings will lose their customizations.'
			)}
		</div>
		<div>
			{$i18n.t('Are you sure you want to continue?')}
		</div>
	</div>
</ConfirmDialog>

{#if models !== null && taskConfig}
	<form
		class="flex flex-col h-full justify-between space-y-3 text-sm"
		on:submit|preventDefault={() => {
			updateInterfaceHandler();
			dispatch('save');
		}}
	>
		<div class="  overflow-y-scroll scrollbar-hidden h-full pr-1.5">
			<div class="mb-3.5">
				<div class=" mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('Tasks')}</div>

				<hr class=" border-gray-100 dark:border-gray-850 my-2" />

				<div class=" mb-2 font-medium flex items-center">
					<div class=" text-xs mr-1">{$i18n.t('Task Model')}</div>
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
							class="size-3.5"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z"
							/>
						</svg>
					</Tooltip>
				</div>

				<div class=" mb-2.5 flex w-full gap-2">
					<div class="flex-1">
						<div class=" text-xs mb-1">{$i18n.t('Local Task Model')}</div>
						<select
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
							bind:value={taskConfig.TASK_MODEL}
							placeholder={$i18n.t('Select a model')}
							on:change={() => {
								if (taskConfig.TASK_MODEL) {
									const model = models.find((m) => m.id === taskConfig.TASK_MODEL);
									if (model) {
										if (model?.access_control !== null) {
											toast.error(
												$i18n.t(
													'This model is not publicly available. Please select another model.'
												)
											);
										}

										taskConfig.TASK_MODEL = model.id;
									} else {
										taskConfig.TASK_MODEL = '';
									}
								}
							}}
						>
							<option value="" selected>{$i18n.t('Current Model')}</option>
							{#each models as model}
								<option value={model.id} class="bg-gray-100 dark:bg-gray-700">
									{model.name}
									{model?.connection_type === 'local' ? `(${$i18n.t('Local')})` : ''}
								</option>
							{/each}
						</select>
					</div>

					<div class="flex-1">
						<div class=" text-xs mb-1">{$i18n.t('External Task Model')}</div>
						<select
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
							bind:value={taskConfig.TASK_MODEL_EXTERNAL}
							placeholder={$i18n.t('Select a model')}
							on:change={() => {
								if (taskConfig.TASK_MODEL_EXTERNAL) {
									const model = models.find((m) => m.id === taskConfig.TASK_MODEL_EXTERNAL);
									if (model) {
										if (model?.access_control !== null) {
											toast.error(
												$i18n.t(
													'This model is not publicly available. Please select another model.'
												)
											);
										}

										taskConfig.TASK_MODEL_EXTERNAL = model.id;
									} else {
										taskConfig.TASK_MODEL_EXTERNAL = '';
									}
								}
							}}
						>
							<option value="" selected>{$i18n.t('Current Model')}</option>
							{#each models as model}
								<option value={model.id} class="bg-gray-100 dark:bg-gray-700">
									{model.name}
									{model?.connection_type === 'local' ? `(${$i18n.t('Local')})` : ''}
								</option>
							{/each}
						</select>
					</div>
				</div>

				<div class="mb-2.5 flex w-full items-center justify-between">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Title Generation')}
					</div>

					<Switch bind:state={taskConfig.ENABLE_TITLE_GENERATION} />
				</div>

				{#if taskConfig.ENABLE_TITLE_GENERATION}
					<div class="mb-2.5">
						<div class=" mb-1 text-xs font-medium">{$i18n.t('Title Generation Prompt')}</div>

						<Tooltip
							content={$i18n.t('Leave empty to use the default prompt, or enter a custom prompt')}
							placement="top-start"
						>
							<Textarea
								bind:value={taskConfig.TITLE_GENERATION_PROMPT_TEMPLATE}
								placeholder={$i18n.t(
									'Leave empty to use the default prompt, or enter a custom prompt'
								)}
							/>
						</Tooltip>
					</div>
				{/if}

				<div class="mb-2.5 flex w-full items-center justify-between">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Voice Mode Custom Prompt')}
					</div>

					<Switch
						state={taskConfig.VOICE_MODE_PROMPT_TEMPLATE != null}
						on:change={(e) => {
							if (e.detail) {
								taskConfig.VOICE_MODE_PROMPT_TEMPLATE = '';
							} else {
								taskConfig.VOICE_MODE_PROMPT_TEMPLATE = null;
							}
						}}
					/>
				</div>

				{#if taskConfig.VOICE_MODE_PROMPT_TEMPLATE != null}
					<div class="mb-2.5">
						<div class=" mb-1 text-xs font-medium">{$i18n.t('Voice Mode Prompt')}</div>

						<Tooltip
							content={$i18n.t('Leave empty to use the default prompt, or enter a custom prompt')}
							placement="top-start"
						>
							<Textarea
								bind:value={taskConfig.VOICE_MODE_PROMPT_TEMPLATE}
								placeholder={$i18n.t(
									'Leave empty to use the default prompt, or enter a custom prompt'
								)}
							/>
						</Tooltip>
					</div>
				{/if}

				<div class="mb-2.5 flex w-full items-center justify-between">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Follow Up Generation')}
					</div>

					<Switch bind:state={taskConfig.ENABLE_FOLLOW_UP_GENERATION} />
				</div>

				{#if taskConfig.ENABLE_FOLLOW_UP_GENERATION}
					<div class="mb-2.5">
						<div class=" mb-1 text-xs font-medium">{$i18n.t('Follow Up Generation Prompt')}</div>

						<Tooltip
							content={$i18n.t('Leave empty to use the default prompt, or enter a custom prompt')}
							placement="top-start"
						>
							<Textarea
								bind:value={taskConfig.FOLLOW_UP_GENERATION_PROMPT_TEMPLATE}
								placeholder={$i18n.t(
									'Leave empty to use the default prompt, or enter a custom prompt'
								)}
							/>
						</Tooltip>
					</div>
				{/if}

				<div class="mb-2.5 flex w-full items-center justify-between">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Tags Generation')}
					</div>

					<Switch bind:state={taskConfig.ENABLE_TAGS_GENERATION} />
				</div>

				{#if taskConfig.ENABLE_TAGS_GENERATION}
					<div class="mb-2.5">
						<div class=" mb-1 text-xs font-medium">{$i18n.t('Tags Generation Prompt')}</div>

						<Tooltip
							content={$i18n.t('Leave empty to use the default prompt, or enter a custom prompt')}
							placement="top-start"
						>
							<Textarea
								bind:value={taskConfig.TAGS_GENERATION_PROMPT_TEMPLATE}
								placeholder={$i18n.t(
									'Leave empty to use the default prompt, or enter a custom prompt'
								)}
							/>
						</Tooltip>
					</div>
				{/if}

				<div class="mb-2.5 flex w-full items-center justify-between">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Retrieval Query Generation')}
					</div>

					<Switch bind:state={taskConfig.ENABLE_RETRIEVAL_QUERY_GENERATION} />
				</div>

				<div class="mb-2.5 flex w-full items-center justify-between">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Web Search Query Generation')}
					</div>

					<Switch bind:state={taskConfig.ENABLE_SEARCH_QUERY_GENERATION} />
				</div>

				<div class="mb-2.5">
					<div class=" mb-1 text-xs font-medium">{$i18n.t('Query Generation Prompt')}</div>

					<Tooltip
						content={$i18n.t('Leave empty to use the default prompt, or enter a custom prompt')}
						placement="top-start"
					>
						<Textarea
							bind:value={taskConfig.QUERY_GENERATION_PROMPT_TEMPLATE}
							placeholder={$i18n.t(
								'Leave empty to use the default prompt, or enter a custom prompt'
							)}
						/>
					</Tooltip>
				</div>

				<div class="mb-2.5 flex w-full items-center justify-between">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Autocomplete Generation')}
					</div>

					<Tooltip content={$i18n.t('Enable autocomplete generation for chat messages')}>
						<Switch bind:state={taskConfig.ENABLE_AUTOCOMPLETE_GENERATION} />
					</Tooltip>
				</div>

				{#if taskConfig.ENABLE_AUTOCOMPLETE_GENERATION}
					<div class="mb-2.5">
						<div class=" mb-1 text-xs font-medium">
							{$i18n.t('Autocomplete Generation Input Max Length')}
						</div>

						<Tooltip
							content={$i18n.t('Character limit for autocomplete generation input')}
							placement="top-start"
						>
							<input
								class="w-full outline-hidden bg-transparent"
								bind:value={taskConfig.AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH}
								placeholder={$i18n.t('-1 for no limit, or a positive integer for a specific limit')}
							/>
						</Tooltip>
					</div>
				{/if}

				<div class="mb-2.5">
					<div class=" mb-1 text-xs font-medium">{$i18n.t('Image Prompt Generation Prompt')}</div>

					<Tooltip
						content={$i18n.t('Leave empty to use the default prompt, or enter a custom prompt')}
						placement="top-start"
					>
						<Textarea
							bind:value={taskConfig.IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE}
							placeholder={$i18n.t(
								'Leave empty to use the default prompt, or enter a custom prompt'
							)}
						/>
					</Tooltip>
				</div>

				<div class="mb-2.5">
					<div class=" mb-1 text-xs font-medium">{$i18n.t('Tools Function Calling Prompt')}</div>

					<Tooltip
						content={$i18n.t('Leave empty to use the default prompt, or enter a custom prompt')}
						placement="top-start"
					>
						<Textarea
							bind:value={taskConfig.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE}
							placeholder={$i18n.t(
								'Leave empty to use the default prompt, or enter a custom prompt'
							)}
						/>
					</Tooltip>
				</div>
			</div>

			<div class="mb-3.5">
				<div class=" mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('UI')}</div>

				<hr class=" border-gray-100 dark:border-gray-850 my-2" />

				<div class="mb-2.5">
					<div class="flex w-full justify-between">
						<div class=" self-center text-xs">
							{$i18n.t('Banners')}
						</div>

						<button
							class="p-1 px-3 text-xs flex rounded-sm transition"
							type="button"
							on:click={() => {
								if (banners.length === 0 || banners.at(-1).content !== '') {
									banners = [
										...banners,
										{
											id: uuidv4(),
											type: '',
											title: '',
											content: '',
											dismissible: true,
											timestamp: Math.floor(Date.now() / 1000)
										}
									];
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

					<Banners bind:banners />
				</div>

				<div class="mb-2.5">
					<div class="flex flex-col space-y-2">
						<button
							class="flex items-center justify-between w-full px-4 py-2.5 text-sm bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 rounded-lg transition"
							type="button"
							on:click={() => {
								showInterfaceDefaultsModal = true;
							}}
						>
							<div class="flex items-center space-x-2">
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="w-4 h-4"
								>
									<path
										fill-rule="evenodd"
										d="M7.84 1.804A1 1 0 018.82 1h2.36a1 1 0 01.98.804l.331 1.652a6.993 6.993 0 011.929 1.115l1.598-.54a1 1 0 011.186.447l1.18 2.044a1 1 0 01-.205 1.251l-1.267 1.113a7.047 7.047 0 010 2.228l1.267 1.113a1 1 0 01.206 1.25l-1.18 2.045a1 1 0 01-1.187.447l-1.598-.54a6.993 6.993 0 01-1.929 1.115l-.33 1.652a1 1 0 01-.98.804H8.82a1 1 0 01-.98-.804l-.331-1.652a6.993 6.993 0 01-1.929-1.115l-1.598.54a1 1 0 01-1.186-.447l-1.18-2.044a1 1 0 01.205-1.251l1.267-1.114a7.05 7.05 0 010-2.227L1.821 7.773a1 1 0 01-.206-1.25l1.18-2.045a1 1 0 011.187-.447l1.598.54A6.993 6.993 0 017.51 3.456l.33-1.652zM10 13a3 3 0 100-6 3 3 0 000 6z"
										clip-rule="evenodd"
									/>
								</svg>
								<span>{$i18n.t('Configure Global Interface Defaults')}</span>
							</div>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="w-4 h-4"
							>
								<path
									fill-rule="evenodd"
									d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
									clip-rule="evenodd"
								/>
							</svg>
						</button>

						<div class="text-xs text-gray-500 dark:text-gray-400">
							{$i18n.t(
								'Set default interface settings that will be applied to all users who haven\'t customized their settings.'
							)}
						</div>
					</div>
				</div>

				<hr class=" border-gray-100 dark:border-gray-850 my-3" />

				<div class="mb-2.5">
					<div class="flex flex-col space-y-2">
						<div class="text-sm font-medium text-red-600 dark:text-red-500">
							{$i18n.t('Danger Zone')}
						</div>

						<button
							class="flex items-center justify-between w-full px-4 py-2.5 text-sm bg-red-50 hover:bg-red-100 dark:bg-red-950 dark:hover:bg-red-900 text-red-700 dark:text-red-300 rounded-lg transition border border-red-200 dark:border-red-800"
							type="button"
							on:click={() => {
								showResetConfirmDialog = true;
							}}
							disabled={resettingUsers}
						>
							<div class="flex items-center space-x-2">
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="w-4 h-4"
								>
									<path
										fill-rule="evenodd"
										d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
										clip-rule="evenodd"
									/>
								</svg>
								<span>
									{resettingUsers
										? $i18n.t('Resetting...')
										: $i18n.t('Reset All Users to Defaults')}
								</span>
							</div>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="w-4 h-4"
							>
								<path
									fill-rule="evenodd"
									d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z"
									clip-rule="evenodd"
								/>
							</svg>
						</button>

						<div class="text-xs text-red-600 dark:text-red-400">
							{$i18n.t(
								'Warning: This will permanently delete all users\' custom interface settings and force them to use the admin-configured defaults. This action is irreversible.'
							)}
						</div>
					</div>
				</div>

				<hr class=" border-gray-100 dark:border-gray-850 my-3" />

				{#if $user?.role === 'admin'}
					<div class=" space-y-3">
						<div class="flex w-full justify-between mb-2">
							<div class=" self-center text-xs">
								{$i18n.t('Default Prompt Suggestions')}
							</div>

							<button
								class="p-1 px-3 text-xs flex rounded-sm transition"
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
						<div class="grid lg:grid-cols-2 flex-col gap-1.5">
							{#each promptSuggestions as prompt, promptIdx}
								<div
									class=" flex border rounded-xl border-gray-50 dark:border-none dark:bg-gray-850 py-1.5"
								>
									<div class="flex flex-col flex-1 pl-1">
										<div class="py-1 gap-1">
											<input
												class="px-3 text-sm font-medium w-full bg-transparent outline-hidden"
												placeholder={$i18n.t('Title (e.g. Tell me a fun fact)')}
												bind:value={prompt.title[0]}
											/>

											<input
												class="px-3 text-xs w-full bg-transparent outline-hidden text-gray-600 dark:text-gray-400"
												placeholder={$i18n.t('Subtitle (e.g. about the Roman Empire)')}
												bind:value={prompt.title[1]}
											/>
										</div>

										<hr class="border-gray-50 dark:border-gray-850 my-1" />

										<textarea
											class="px-3 py-1.5 text-xs w-full bg-transparent outline-hidden resize-none"
											placeholder={$i18n.t(
												'Prompt (e.g. Tell me a fun fact about the Roman Empire)'
											)}
											rows="3"
											bind:value={prompt.content}
										/>
									</div>

									<div class="">
										<button
											class="p-3"
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
								</div>
							{/each}
						</div>

						{#if promptSuggestions.length > 0}
							<div class="text-xs text-left w-full mt-2">
								{$i18n.t('Adjusting these settings will apply changes universally to all users.')}
							</div>
						{/if}

						<div class="flex items-center justify-end space-x-2 mt-2">
							<input
								id="prompt-suggestions-import-input"
								type="file"
								accept=".json"
								hidden
								on:change={(e) => {
									const files = e.target.files;
									if (!files || files.length === 0) {
										return;
									}

									console.log(files);

									let reader = new FileReader();
									reader.onload = async (event) => {
										try {
											let suggestions = JSON.parse(event.target.result);

											suggestions = suggestions.map((s) => {
												if (typeof s.title === 'string') {
													s.title = [s.title, ''];
												} else if (!Array.isArray(s.title)) {
													s.title = ['', ''];
												}

												return s;
											});

											promptSuggestions = [...promptSuggestions, ...suggestions];
										} catch (error) {
											toast.error($i18n.t('Invalid JSON file'));
											return;
										}
									};

									reader.readAsText(files[0]);

									e.target.value = ''; // Reset the input value
								}}
							/>

							<button
								class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-200 transition"
								type="button"
								on:click={() => {
									const input = document.getElementById('prompt-suggestions-import-input');
									if (input) {
										input.click();
									}
								}}
							>
								<div class=" self-center mr-2 font-medium line-clamp-1">
									{$i18n.t('Import Prompt Suggestions')}
								</div>

								<div class=" self-center">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 16 16"
										fill="currentColor"
										class="w-3.5 h-3.5"
									>
										<path
											fill-rule="evenodd"
											d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 9.5a.75.75 0 0 1-.75-.75V8.06l-.72.72a.75.75 0 0 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0l2 2a.75.75 0 1 1-1.06 1.06l-.72-.72v2.69a.75.75 0 0 1-.75.75Z"
											clip-rule="evenodd"
										/>
									</svg>
								</div>
							</button>

							{#if promptSuggestions.length}
								<button
									class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-200 transition"
									type="button"
									on:click={async () => {
										let blob = new Blob([JSON.stringify(promptSuggestions)], {
											type: 'application/json'
										});
										saveAs(blob, `prompt-suggestions-export-${Date.now()}.json`);
									}}
								>
									<div class=" self-center mr-2 font-medium line-clamp-1">
										{$i18n.t('Export Prompt Suggestions')} ({promptSuggestions.length})
									</div>

									<div class=" self-center">
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 16 16"
											fill="currentColor"
											class="w-3.5 h-3.5"
										>
											<path
												fill-rule="evenodd"
												d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 3.5a.75.75 0 0 1 .75.75v2.69l.72-.72a.75.75 0 1 1 1.06 1.06l-2 2a.75.75 0 0 1-1.06 0l-2-2a.75.75 0 0 1 1.06-1.06l.72.72V6.25A.75.75 0 0 1 8 5.5Z"
												clip-rule="evenodd"
											/>
										</svg>
									</div>
								</button>
							{/if}
						</div>
					</div>
				{/if}
			</div>
		</div>

		<div class="flex justify-end text-sm font-medium">
			<button
				class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
				type="submit"
			>
				{$i18n.t('Save')}
			</button>
		</div>
	</form>
{:else}
	<div class=" h-full w-full flex justify-center items-center">
		<Spinner className="size-5" />
	</div>
{/if}
