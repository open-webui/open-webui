<script lang="ts">
	import { getModels, getTaskConfig, updateTaskConfig } from '$lib/apis';
	import { getChatConfig, updateChatConfig } from '$lib/apis/chats';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getBaseModels } from '$lib/apis/models';

	import Switch from '$lib/components/common/Switch.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';
	import AdminSettingField from './AdminSettingField.svelte';
	import AdminSettingRow from './AdminSettingRow.svelte';
	import AdminSettingSection from './AdminSettingSection.svelte';
	import { config as appConfig } from '$lib/stores';

	const dispatch = createEventDispatcher();

	const i18n: any = getContext('i18n');

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
		AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE: '',
		TAGS_GENERATION_PROMPT_TEMPLATE: '',
		ENABLE_TAGS_GENERATION: true,
		ENABLE_SEARCH_QUERY_GENERATION: true,
		ENABLE_RETRIEVAL_QUERY_GENERATION: true,
		QUERY_GENERATION_PROMPT_TEMPLATE: '',
		TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE: '',
		ENABLE_VOICE_MODE_PROMPT: true,
		VOICE_MODE_PROMPT_TEMPLATE: ''
	};

	let chatConfig = {
		ENABLE_CONTEXT_COMPACTION: false,
		CONTEXT_COMPACTION_TOKEN_THRESHOLD: 80000,
		CONTEXT_COMPACTION_TOKEN_CAP: 80000,
		CONTEXT_COMPACTION_RETAINED_MESSAGES_PERCENTAGE: 20,
		CONTEXT_COMPACTION_PROMPT_TEMPLATE: ''
	};

	const updateInterfaceHandler = async () => {
		[taskConfig, chatConfig] = await Promise.all([
			updateTaskConfig(localStorage.token, taskConfig),
			updateChatConfig(localStorage.token, chatConfig)
		]);
		appConfig.update((current) =>
			current
				? {
						...current,
						features: {
							...current.features,
							enable_context_compaction: chatConfig.ENABLE_CONTEXT_COMPACTION
						}
					}
				: current
		);
	};

	let workspaceModels: any[] = [];
	let baseModels: any[] = [];

	let models: any[] | null = null;
	$: modelOptions = models ?? [];
	const inputClass =
		'w-full h-7 rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';
	const textareaClass =
		'w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';

	const init = async () => {
		try {
			[taskConfig, chatConfig] = await Promise.all([
				getTaskConfig(localStorage.token),
				getChatConfig(localStorage.token)
			]);

			workspaceModels = await getBaseModels(localStorage.token);
			baseModels = await getModels(localStorage.token, null, false);

			models = baseModels.map((m: any) => {
				const workspaceModel = workspaceModels.find((wm: any) => wm.id === m.id);

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
		} catch (err) {
			const error = err as { detail?: string; message?: string };
			console.error('Failed to initialize Interface settings:', err);
			toast.error(error?.detail ?? error?.message ?? $i18n.t('Failed to load Interface settings'));
			models = [];
		}
	};

	onMount(async () => {
		await init();
	});
</script>

{#if models !== null && taskConfig && chatConfig}
	<form
		class="flex h-full flex-col justify-between text-sm"
		on:submit|preventDefault={() => {
			updateInterfaceHandler();
			dispatch('save');
		}}
	>
		<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">
			{$i18n.t('Interface')}
		</h2>

		<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
			<AdminSettingSection title={$i18n.t('Tasks')} first>
				<div>
					<div class="mb-2">
						<div class="text-xs text-gray-600 dark:text-gray-400">{$i18n.t('Task Model')}</div>
						<div class="mt-1.5 text-[0.6875rem] text-gray-400 dark:text-gray-600">
							{$i18n.t(
								'Choose fallback models for background tasks. Current Model follows the active chat model.'
							)}
						</div>
					</div>

					<div class="grid w-full grid-cols-1 gap-2.5 sm:grid-cols-2">
						<AdminSettingField label={$i18n.t('Local Task Model')}>
							<SettingsSelect
								bind:value={taskConfig.TASK_MODEL}
								className="w-full"
								placeholder={$i18n.t('Select a model')}
								on:change={() => {
									if (taskConfig.TASK_MODEL) {
										const model = modelOptions.find((m: any) => m.id === taskConfig.TASK_MODEL);
										if (model) {
											if (
												model?.access_grants &&
												!model.access_grants.some(
													(g: any) =>
														g.principal_type === 'user' &&
														g.principal_id === '*' &&
														g.permission === 'read'
												)
											) {
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
								{#each modelOptions as model}
									<option value={model.id} class="bg-gray-100 dark:bg-gray-700">
										{model.name}
										{model?.connection_type === 'local' ? `(${$i18n.t('Local')})` : ''}
									</option>
								{/each}
							</SettingsSelect>
						</AdminSettingField>

						<AdminSettingField label={$i18n.t('External Task Model')}>
							<SettingsSelect
								bind:value={taskConfig.TASK_MODEL_EXTERNAL}
								className="w-full"
								placeholder={$i18n.t('Select a model')}
								on:change={() => {
									if (taskConfig.TASK_MODEL_EXTERNAL) {
										const model = modelOptions.find(
											(m: any) => m.id === taskConfig.TASK_MODEL_EXTERNAL
										);
										if (model) {
											if (
												model?.access_grants &&
												!model.access_grants.some(
													(g: any) =>
														g.principal_type === 'user' &&
														g.principal_id === '*' &&
														g.permission === 'read'
												)
											) {
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
								{#each modelOptions as model}
									<option value={model.id} class="bg-gray-100 dark:bg-gray-700">
										{model.name}
										{model?.connection_type === 'local' ? `(${$i18n.t('Local')})` : ''}
									</option>
								{/each}
							</SettingsSelect>
						</AdminSettingField>
					</div>
				</div>
			</AdminSettingSection>

			<AdminSettingSection title={$i18n.t('Chat')}>
				<AdminSettingRow
					label={$i18n.t('Context Compaction')}
					description={$i18n.t(
						'Summarize older chat history when the conversation context grows large.'
					)}
				>
					<Switch bind:state={chatConfig.ENABLE_CONTEXT_COMPACTION} />
				</AdminSettingRow>

				{#if chatConfig.ENABLE_CONTEXT_COMPACTION}
					<AdminSettingField
						label={$i18n.t('Token Threshold')}
						description={$i18n.t(
							'Older messages are summarized when estimated context exceeds this token limit.'
						)}
					>
						<input
							type="number"
							min="1"
							step="1"
							class={inputClass}
							bind:value={chatConfig.CONTEXT_COMPACTION_TOKEN_THRESHOLD}
						/>
					</AdminSettingField>

					<AdminSettingField
						label={$i18n.t('Token Cap')}
						description={$i18n.t(
							'Model-specific context compaction thresholds cannot exceed this token limit.'
						)}
					>
						<input
							type="number"
							min="1"
							step="1"
							class={inputClass}
							bind:value={chatConfig.CONTEXT_COMPACTION_TOKEN_CAP}
						/>
					</AdminSettingField>

					<AdminSettingField
						label={$i18n.t('Retained Message Percentage')}
						description={$i18n.t(
							'Percentage (10–50%) of the most recent messages to retain after context compaction.'
						)}
					>
						<div class="relative">
							<input
								type="number"
								min="10"
								max="50"
								step="1"
								class={inputClass}
								bind:value={chatConfig.CONTEXT_COMPACTION_RETAINED_MESSAGES_PERCENTAGE}
							/>
							<span class="absolute inset-y-0 right-4 flex items-center text-sm text-gray-500">%</span>
						</div>
					</AdminSettingField>

					<AdminSettingField
						label={$i18n.t('Context Compaction Prompt')}
						description={$i18n.t(
							'Controls how older messages are rewritten into a running summary.'
						)}
					>
						<Textarea
							className={textareaClass}
							bind:value={chatConfig.CONTEXT_COMPACTION_PROMPT_TEMPLATE}
							placeholder={$i18n.t(
								'Leave empty to use the default prompt, or enter a custom prompt'
							)}
						/>
						<div class="mt-1 text-[0.6875rem] text-gray-400 dark:text-gray-600">
							{$i18n.t('Available variables')}:
							<code>{'{{PREVIOUS_SUMMARY}}'}</code>,
							<code>{'{{COMPACTED_MESSAGES}}'}</code>,
							<code>{'{{RECENT_MESSAGES}}'}</code>,
							<code>{'{{MESSAGES}}'}</code>,
							<code>{'{{CURRENT_DATE}}'}</code>
						</div>
					</AdminSettingField>
				{/if}
			</AdminSettingSection>

			<AdminSettingSection title={$i18n.t('Generation')}>
				<AdminSettingRow
					label={$i18n.t('Title Generation')}
					description={$i18n.t('Allow automatic names for new chats.')}
				>
					<Switch bind:state={taskConfig.ENABLE_TITLE_GENERATION} />
				</AdminSettingRow>

				{#if taskConfig.ENABLE_TITLE_GENERATION}
					<AdminSettingField
						label={$i18n.t('Title Generation Prompt')}
						description={$i18n.t('Shapes the short label generated for each chat.')}
					>
						<Textarea
							className={textareaClass}
							bind:value={taskConfig.TITLE_GENERATION_PROMPT_TEMPLATE}
							placeholder={$i18n.t(
								'Leave empty to use the default prompt, or enter a custom prompt'
							)}
						/>
					</AdminSettingField>
				{/if}

				<AdminSettingRow
					label={$i18n.t('Voice Mode Prompt')}
					description={$i18n.t('Apply voice-specific instructions while voice mode is active.')}
				>
					<Switch bind:state={taskConfig.ENABLE_VOICE_MODE_PROMPT} />
				</AdminSettingRow>

				{#if taskConfig.ENABLE_VOICE_MODE_PROMPT}
					<AdminSettingField
						label={$i18n.t('Prompt Template')}
						description={$i18n.t('Defines the behavior used for spoken conversations.')}
					>
						<Textarea
							className={textareaClass}
							bind:value={taskConfig.VOICE_MODE_PROMPT_TEMPLATE}
							placeholder={$i18n.t(
								'Leave empty to use the default prompt, or enter a custom prompt'
							)}
						/>
					</AdminSettingField>
				{/if}

				<AdminSettingRow
					label={$i18n.t('Follow Up Generation')}
					description={$i18n.t('Show suggested next questions after assistant responses.')}
				>
					<Switch bind:state={taskConfig.ENABLE_FOLLOW_UP_GENERATION} />
				</AdminSettingRow>

				{#if taskConfig.ENABLE_FOLLOW_UP_GENERATION}
					<AdminSettingField
						label={$i18n.t('Follow Up Generation Prompt')}
						description={$i18n.t('Guides the suggestions shown after an assistant response.')}
					>
						<Textarea
							className={textareaClass}
							bind:value={taskConfig.FOLLOW_UP_GENERATION_PROMPT_TEMPLATE}
							placeholder={$i18n.t(
								'Leave empty to use the default prompt, or enter a custom prompt'
							)}
						/>
					</AdminSettingField>
				{/if}

				<AdminSettingRow
					label={$i18n.t('Tags Generation')}
					description={$i18n.t('Create chat tags from conversation content.')}
				>
					<Switch bind:state={taskConfig.ENABLE_TAGS_GENERATION} />
				</AdminSettingRow>

				{#if taskConfig.ENABLE_TAGS_GENERATION}
					<AdminSettingField
						label={$i18n.t('Tags Generation Prompt')}
						description={$i18n.t('Controls how chat tags are inferred.')}
					>
						<Textarea
							className={textareaClass}
							bind:value={taskConfig.TAGS_GENERATION_PROMPT_TEMPLATE}
							placeholder={$i18n.t(
								'Leave empty to use the default prompt, or enter a custom prompt'
							)}
						/>
					</AdminSettingField>
				{/if}

				<AdminSettingRow
					label={$i18n.t('Retrieval Query Generation')}
					description={$i18n.t('Rewrite user requests for knowledge retrieval.')}
				>
					<Switch bind:state={taskConfig.ENABLE_RETRIEVAL_QUERY_GENERATION} />
				</AdminSettingRow>

				<AdminSettingRow
					label={$i18n.t('Web Search Query Generation')}
					description={$i18n.t('Rewrite user requests into web-search queries.')}
				>
					<Switch bind:state={taskConfig.ENABLE_SEARCH_QUERY_GENERATION} />
				</AdminSettingRow>

				<AdminSettingField
					label={$i18n.t('Query Generation Prompt')}
					description={$i18n.t('Shared prompt for retrieval and web-search query rewriting.')}
				>
					<Textarea
						className={textareaClass}
						bind:value={taskConfig.QUERY_GENERATION_PROMPT_TEMPLATE}
						placeholder={$i18n.t('Leave empty to use the default prompt, or enter a custom prompt')}
					/>
				</AdminSettingField>

				<AdminSettingRow
					label={$i18n.t('Autocomplete Generation')}
					description={$i18n.t('Suggest completions while users type chat messages.')}
				>
					<Switch bind:state={taskConfig.ENABLE_AUTOCOMPLETE_GENERATION} />
				</AdminSettingRow>

				{#if taskConfig.ENABLE_AUTOCOMPLETE_GENERATION}
					<AdminSettingField
						label={$i18n.t('Autocomplete Generation Input Max Length')}
						description={$i18n.t('Limit how much draft text is sent for suggestion generation.')}
					>
						<input
							type="number"
							min="-1"
							step="1"
							class={inputClass}
							bind:value={taskConfig.AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH}
							placeholder={$i18n.t('-1 for no limit, or a positive integer for a specific limit')}
						/>
					</AdminSettingField>

					<AdminSettingField
						label={$i18n.t('Autocomplete Generation Prompt')}
						description={$i18n.t('Guides inline completions while users type a message.')}
					>
						<Textarea
							className={textareaClass}
							bind:value={taskConfig.AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE}
							placeholder={$i18n.t(
								'Leave empty to use the default prompt, or enter a custom prompt'
							)}
						/>
					</AdminSettingField>
				{/if}

				<AdminSettingField
					label={$i18n.t('Image Prompt Generation Prompt')}
					description={$i18n.t('Rewrites user intent into an image-generation prompt.')}
				>
					<Textarea
						className={textareaClass}
						bind:value={taskConfig.IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE}
						placeholder={$i18n.t('Leave empty to use the default prompt, or enter a custom prompt')}
					/>
				</AdminSettingField>

				<AdminSettingField
					label={$i18n.t('Tools Function Calling Prompt')}
					description={$i18n.t('Guides how the assistant formats tool and function calls.')}
				>
					<Textarea
						className={textareaClass}
						bind:value={taskConfig.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE}
						placeholder={$i18n.t('Leave empty to use the default prompt, or enter a custom prompt')}
					/>
				</AdminSettingField>
			</AdminSettingSection>
		</div>

		<div class="flex justify-end pt-6 text-sm font-normal">
			<button
				class="px-3.5 py-1.5 text-sm font-normal bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
				type="submit"
			>
				{$i18n.t('Save')}
			</button>
		</div>
	</form>
{:else}
	<div class="flex h-full w-full items-center justify-center">
		<Spinner className="size-5" />
	</div>
{/if}
