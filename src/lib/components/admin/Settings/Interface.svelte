<script lang="ts">
	import { v4 as uuidv4 } from 'uuid';
	import { toast } from 'svelte-sonner';

	import { getBackendConfig, getTaskConfig, updateTaskConfig } from '$lib/apis';
	import { setDefaultPromptSuggestions } from '$lib/apis/configs';
	import { config, models, settings, user } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext } from 'svelte';

	import { banners as _banners } from '$lib/stores';
	import type { Banner } from '$lib/types';

	import { getBanners, setBanners } from '$lib/apis/configs';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';

	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	let taskConfig = {
		TASK_MODEL: '',
		TASK_MODEL_EXTERNAL: '',
		ENABLE_TITLE_GENERATION: true,
		TITLE_GENERATION_PROMPT_TEMPLATE: '',
		IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE: '',
		ENABLE_AUTOCOMPLETE_GENERATION: true,
		AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH: -1,
		TAGS_GENERATION_PROMPT_TEMPLATE: '',
		ENABLE_TAGS_GENERATION: true,
		ENABLE_SEARCH_QUERY_GENERATION: true,
		ENABLE_RETRIEVAL_QUERY_GENERATION: true,
		QUERY_GENERATION_PROMPT_TEMPLATE: '',
		TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE: ''
	};

	let promptSuggestions = [];
	let banners: Banner[] = [];

	const updateInterfaceHandler = async () => {
		taskConfig = await updateTaskConfig(localStorage.token, taskConfig);

		promptSuggestions = await setDefaultPromptSuggestions(localStorage.token, promptSuggestions);
		await updateBanners();

		await config.set(await getBackendConfig());
	};

	onMount(async () => {
		taskConfig = await getTaskConfig(localStorage.token);

		promptSuggestions = $config?.default_prompt_suggestions ?? [];
		banners = await getBanners(localStorage.token);
	});

	const updateBanners = async () => {
		_banners.set(await setBanners(localStorage.token, banners));
	};
</script>

{#if taskConfig}
	<form
		class="flex flex-col h-full justify-between space-y-3 text-sm"
		on:submit|preventDefault={() => {
			updateInterfaceHandler();
			dispatch('save');
		}}
	>
		<div class="overflow-y-scroll scrollbar-hidden h-full pr-1.5" style="padding-right: 4px;">
			<!-- Tasks Section -->
			<div class="mb-3.5" style="background: linear-gradient(to bottom, rgba(0,0,0,0.02), transparent); border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid rgba(0,0,0,0.05);">
				<div class="mb-4 flex items-center gap-2">
				<div class="w-1 h-6 bg-orange-500 rounded-sm"></div>
				<div class="text-base font-medium text-gray-800 dark:text-gray-200 tracking-tight">
					{$i18n.t('Tasks')}
				</div>
			</div>

				<div class="space-y-3" style="background: white; border-radius: 10px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid rgba(0,0,0,0.06);">
					<!-- Set Task Model -->
					<div style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
						<div class="mb-1 font-medium flex items-center" style="gap: 4px;">
							<div class="text-xs mr-1" style="color: #374151; font-size: 13px; font-weight: 600;">{$i18n.t('Set Task Model')}</div>
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
									style="color: #6b7280;"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z"
									/>
								</svg>
							</Tooltip>
						</div>

						<div class="mb-2.5 flex w-full gap-2" style="gap: 12px; margin-top: 8px;">
							<div class="flex-1">
								<div class="text-xs mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">{$i18n.t('Local Models')}</div>
								<select
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									bind:value={taskConfig.TASK_MODEL}
									placeholder={$i18n.t('Select a model')}
									style="background: #f9fafb; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s; cursor: pointer;"
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
								<div class="text-xs mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">{$i18n.t('External Models')}</div>
								<select
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									bind:value={taskConfig.TASK_MODEL_EXTERNAL}
									placeholder={$i18n.t('Select a model')}
									style="background: #f9fafb; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s; cursor: pointer;"
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
					</div>

					<!-- Title Generation -->
					<div style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
						<div class="flex w-full items-center justify-between">
							<div class="self-center text-xs font-medium" style="color: #374151; font-size: 13px;">
								{$i18n.t('Title Generation')}
							</div>
							<Switch bind:state={taskConfig.ENABLE_TITLE_GENERATION} />
						</div>

						{#if taskConfig.ENABLE_TITLE_GENERATION}
							<div class="mb-2.5" style="margin-top: 12px;">
								<div class="mb-1 text-xs font-medium" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">{$i18n.t('Title Generation Prompt')}</div>

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
					</div>

					<!-- Tags Generation -->
					<div style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
						<div class="flex w-full items-center justify-between">
							<div class="self-center text-xs font-medium" style="color: #374151; font-size: 13px;">
								{$i18n.t('Tags Generation')}
							</div>
							<Switch bind:state={taskConfig.ENABLE_TAGS_GENERATION} />
						</div>

						{#if taskConfig.ENABLE_TAGS_GENERATION}
							<div class="mb-2.5" style="margin-top: 12px;">
								<div class="mb-1 text-xs font-medium" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">{$i18n.t('Tags Generation Prompt')}</div>

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
					</div>

					<!-- Retrieval Query Generation -->
					<div class="flex w-full items-center justify-between" style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
						<div class="self-center text-xs font-medium" style="color: #374151; font-size: 13px;">
							{$i18n.t('Retrieval Query Generation')}
						</div>
						<Switch bind:state={taskConfig.ENABLE_RETRIEVAL_QUERY_GENERATION} />
					</div>

					<!-- Web Search Query Generation -->
					<div class="flex w-full items-center justify-between" style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
						<div class="self-center text-xs font-medium" style="color: #374151; font-size: 13px;">
							{$i18n.t('Web Search Query Generation')}
						</div>
						<Switch bind:state={taskConfig.ENABLE_SEARCH_QUERY_GENERATION} />
					</div>

					<!-- Query Generation Prompt -->
					<div style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
						<div class="mb-1 text-xs font-medium" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">{$i18n.t('Query Generation Prompt')}</div>

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

					<!-- Autocomplete Generation -->
					<div style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
						<div class="flex w-full items-center justify-between">
							<div class="self-center text-xs font-medium" style="color: #374151; font-size: 13px;">
								{$i18n.t('Autocomplete Generation')}
							</div>

							<Tooltip content={$i18n.t('Enable autocomplete generation for chat messages')}>
								<Switch bind:state={taskConfig.ENABLE_AUTOCOMPLETE_GENERATION} />
							</Tooltip>
						</div>

						{#if taskConfig.ENABLE_AUTOCOMPLETE_GENERATION}
							<div class="mb-2.5" style="margin-top: 12px;">
								<div class="mb-1 text-xs font-medium" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
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
										style="background: #f9fafb; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
									/>
								</Tooltip>
							</div>
						{/if}
					</div>

					<!-- Image Prompt Generation Prompt -->
					<div style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
						<div class="mb-1 text-xs font-medium" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">{$i18n.t('Image Prompt Generation Prompt')}</div>

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

					<!-- Tools Function Calling Prompt -->
					<div style="padding: 8px 0;">
						<div class="mb-1 text-xs font-medium" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">{$i18n.t('Tools Function Calling Prompt')}</div>

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
			</div>

			<!-- UI Section -->
			<div class="mb-3.5" style="background: linear-gradient(to bottom, rgba(0,0,0,0.02), transparent); border-radius: 12px; padding: 20px; border: 1px solid rgba(0,0,0,0.05);">
				<div class="mb-4 flex items-center gap-2">
				<div class="w-1 h-6 bg-orange-500 rounded-sm"></div>
				<div class="text-base font-medium text-gray-800 dark:text-gray-200 tracking-tight">
					{$i18n.t('UI')}
				</div>
			</div>

				<!-- Banners -->
				<div class="{banners.length > 0 ? 'mb-3' : ''}" style="background: white; border-radius: 10px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid rgba(0,0,0,0.06); margin-bottom: 16px;">
					<div class="mb-2.5 flex w-full justify-between items-center">
						<div class="self-center text-sm font-semibold" style="color: #374151; font-size: 14px;">
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
							style="background:#3b82f6;; color: white; border-radius: 8px; padding: 6px 12px; transition: all 0.2s; box-shadow: 0 2px 6px rgba(16, 185, 129, 0.25); border: none; display: flex; align-items: center; gap: 4px;"
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

					<div class="flex flex-col space-y-1" style="gap: 10px;">
						{#each banners as banner, bannerIdx}
							<div class="flex justify-between" style="gap: 8px;">
								<div
									class="flex flex-row flex-1 border rounded-xl border-gray-100 dark:border-gray-850"
									style="background: #f9fafb; border: 1px solid rgba(0,0,0,0.08); border-radius: 10px; overflow: hidden;"
								>
									<select
										class="w-fit capitalize rounded-xl py-2 px-4 text-xs bg-transparent outline-hidden"
										bind:value={banner.type}
										required
										style="background: transparent; border: none; border-right: 1px solid rgba(0,0,0,0.08); cursor: pointer; font-weight: 600; padding: 10px 14px;"
									>
										{#if banner.type == ''}
											<option value="" selected disabled class="text-gray-900"
												>{$i18n.t('Type')}</option
											>
										{/if}
										<option value="info" class="text-gray-900">{$i18n.t('Info')}</option>
										<option value="warning" class="text-gray-900">{$i18n.t('Warning')}</option>
										<option value="error" class="text-gray-900">{$i18n.t('Error')}</option>
										<option value="success" class="text-gray-900">{$i18n.t('Success')}</option>
									</select>

									<input
										class="pr-5 py-1.5 text-xs w-full bg-transparent outline-hidden"
										placeholder={$i18n.t('Content')}
										bind:value={banner.content}
										style="padding: 10px 14px; border: none; background: transparent;"
									/>

									<div class="relative top-1.5 -left-2" style="display: flex; align-items: center; padding-right: 8px;">
										<Tooltip content={$i18n.t('Dismissible')} className="flex h-fit items-center">
											<Switch bind:state={banner.dismissible} />
										</Tooltip>
									</div>
								</div>

								<button
									class="px-2"
									type="button"
									on:click={() => {
										banners.splice(bannerIdx, 1);
										banners = banners;
									}}
									style="background: #fee2e2; color: #dc2626; border-radius: 8px; padding: 8px 12px; transition: all 0.2s; border: 1px solid rgba(220, 38, 38, 0.2);"
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
				</div>

				<!-- Default Prompt Suggestions -->
				{#if $user?.role === 'admin'}
					<div class="space-y-3" style="background: white; border-radius: 10px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid rgba(0,0,0,0.06);">
						<div class="flex w-full justify-between mb-2 items-center">
							<div class="self-center text-sm font-semibold" style="color: #374151; font-size: 14px;">
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
								style="background:#3b82f6; color: white; border-radius: 8px; padding: 6px 12px; transition: all 0.2s; box-shadow: 0 2px 6px rgba(16, 185, 129, 0.25); border: none; display: flex; align-items: center; gap: 4px;"
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
						<div class="grid lg:grid-cols-2 flex-col gap-1.5" style="gap: 12px;">
							{#each promptSuggestions as prompt, promptIdx}
								<div
									class="flex border border-gray-100 dark:border-none dark:bg-gray-850 rounded-xl py-1.5"
									style="background: #f9fafb; border: 1px solid rgba(0,0,0,0.08); border-radius: 10px; overflow: hidden;"
								>
									<div class="flex flex-col flex-1 pl-1">
										<div class="flex border-b border-gray-100 dark:border-gray-850 w-full" style="border-bottom: 1px solid rgba(0,0,0,0.08);">
											<input
												class="px-3 py-1.5 text-xs w-full bg-transparent outline-hidden border-r border-gray-100 dark:border-gray-850"
												placeholder={$i18n.t('Title (e.g. Tell me a fun fact)')}
												bind:value={prompt.title[0]}
												style="padding: 10px 14px; border: none; border-right: 1px solid rgba(0,0,0,0.08); background: transparent; font-weight: 500;"
											/>

											<input
												class="px-3 py-1.5 text-xs w-full bg-transparent outline-hidden border-r border-gray-100 dark:border-gray-850"
												placeholder={$i18n.t('Subtitle (e.g. about the Roman Empire)')}
												bind:value={prompt.title[1]}
												style="padding: 10px 14px; border: none; background: transparent; color: #6b7280;"
											/>
										</div>

										<textarea
											class="px-3 py-1.5 text-xs w-full bg-transparent outline-hidden border-r border-gray-100 dark:border-gray-850 resize-none"
											placeholder={$i18n.t(
												'Prompt (e.g. Tell me a fun fact about the Roman Empire)'
											)}
											rows="3"
											bind:value={prompt.content}
											style="padding: 10px 14px; border: none; background: transparent; resize: none; line-height: 1.5;"
										/>
									</div>

									<button
										class="px-3"
										type="button"
										on:click={() => {
											promptSuggestions.splice(promptIdx, 1);
											promptSuggestions = promptSuggestions;
										}}
										style="background: transparent; color: #dc2626; padding: 8px 12px; transition: all 0.2s; display: flex; align-items: center; justify-content: center;"
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
							<div class="text-xs text-left w-full mt-2" style="line-height: 1.5; color: #6b7280; background: #f3f4f6; padding: 10px 14px; border-radius: 8px; border-left: 3px solid #3b82f6; margin-top: 12px;">
								{$i18n.t('Adjusting these settings will apply changes universally to all users.')}
							</div>
						{/if}
					</div>
				{/if}
			</div>
		</div>

		<div class="flex justify-end text-sm font-medium" style="border-top: 1px solid rgba(0,0,0,0.08); padding-top: 16px;">
			<button
				class="px-3.5 py-1.5 text-sm font-medium bg-orange-600 hover:bg-orange-700 text-white transition rounded-lg"
				type="submit"
				
			>
				{$i18n.t('Save')}
			</button>
		</div>
	</form>
{/if}