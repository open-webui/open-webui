<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { config as backendConfig, user } from '$lib/stores';

	import { getBackendConfig } from '$lib/apis';
	import {
		getImageGenerationModels,
		getImageGenerationConfig,
		updateImageGenerationConfig,
		getConfig,
		updateConfig,
		verifyConfigUrl
	} from '$lib/apis/images';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import CodeEditorModal from '$lib/components/common/CodeEditorModal.svelte';
	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';
	import AdminSettingField from './AdminSettingField.svelte';
	import AdminSettingRow from './AdminSettingRow.svelte';
	import AdminSettingSection from './AdminSettingSection.svelte';

	const dispatch = createEventDispatcher();

	const i18n: any = getContext('i18n');

	let loading = false;

	let models = null;
	let config = null;
	const inputClass =
		'w-full h-7 rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';
	const textareaClass =
		'w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';

	let showComfyUIWorkflowEditor = false;

	// Dynamic workflow node config — populated automatically by parseAndPopulateWorkflowNodes()
	let workflowNodesConfig: { type: string; key: string; node_ids: string; class_type: string }[] =
		[];
	let lastKnownWorkflowString: string | null = null;

	/**
	 * Scans every node in the parsed ComfyUI API workflow object and builds a configurable
	 * row for each primitive input (string / number / boolean). Array-valued inputs are
	 * wires/links and are intentionally skipped.
	 *
	 * @param workflow       - Parsed JSON object (ComfyUI API format).
	 * @param savedNodes     - Previously-saved node configs used for reconciliation on load.
	 * @param showToast      - Whether to surface success/warning toasts to the user.
	 */
	function parseAndPopulateWorkflowNodes(
		workflow: Record<string, any>,
		savedNodes: { type: string; key: string; node_ids: string[] | string }[] = [],
		showToast = false
	): boolean {
		if (!workflow || typeof workflow !== 'object') {
			if (showToast) toast.error($i18n.t('Invalid workflow data provided for parsing.'));
			workflowNodesConfig = [];
			return false;
		}

		// Each entry is keyed by "nodeId::class_type::inputKey" so that nodes
		// sharing the same class and input (e.g. positive vs negative CLIPTextEncode)
		// are always kept as separate rows rather than merged together.
		const nodeGroups = new Map<
			string,
			{ type: string; key: string; node_ids: string[]; class_type: string }
		>();
		let discoveredPrimitiveCount = 0;

		try {
			for (const nodeId of Object.keys(workflow)) {
				const node = workflow[nodeId];
				if (!node || typeof node !== 'object' || !node.inputs || typeof node.inputs !== 'object')
					continue;

				for (const inputKey of Object.keys(node.inputs)) {
					const val = node.inputs[inputKey];
					const valType = typeof val;

					// Only expose primitive (non-link) inputs
					if (valType !== 'string' && valType !== 'number' && valType !== 'boolean') continue;

					discoveredPrimitiveCount++;

					// Unique key per node+input — never merges across different node IDs
					const entryKey = `${nodeId}::${node.class_type}::${inputKey}`;
					// The "type" stored in COMFYUI_WORKFLOW_NODES uses class_type::inputKey
					const semanticType = `${node.class_type}::${inputKey}`;

					// Check if this entry had saved node IDs the user configured
					const saved = savedNodes.find(
						(s) =>
							s.type === semanticType &&
							s.key === inputKey &&
							Array.isArray(s.node_ids) &&
							s.node_ids.length > 0 &&
							(s.node_ids as string[]).includes(nodeId)
					);

					if (!nodeGroups.has(entryKey)) {
						// Keys that map to payload.prompt in _apply_workflow_nodes are ambiguous
						// when multiple nodes share the same key (e.g. positive vs negative
						// CLIPTextEncode both have key 'text'). Leave node_ids empty for
						// these so the admin explicitly picks which nodes receive the prompt.
						const ambiguousKeys = new Set(['text', 'prompt', 'positive']);
						const autoAssign = !ambiguousKeys.has(inputKey);

						nodeGroups.set(entryKey, {
							type: semanticType,
							key: inputKey,
							node_ids: autoAssign ? [nodeId] : [],
							class_type: node.class_type
						});
					}
				}
			}
		} catch (err) {
			console.error('Error parsing workflow nodes:', err);
			if (showToast) toast.error($i18n.t('Error occurred during workflow parsing.'));
			workflowNodesConfig = [];
			return false;
		}

		// Convert map → array, joining node_ids to comma-separated string for the UI input fields
		workflowNodesConfig = Array.from(nodeGroups.values()).map((n) => ({
			...n,
			node_ids: n.node_ids.join(',')
		}));

		if (showToast) {
			if (workflowNodesConfig.length > 0) {
				toast.success(
					$i18n.t(
						`Workflow parsed. {{count}} configurable input(s) found. Please review the Node IDs.`,
						{ count: workflowNodesConfig.length }
					)
				);
			} else if (discoveredPrimitiveCount === 0 && Object.keys(workflow).length > 0) {
				toast.info(
					$i18n.t(
						'Workflow parsed, but no configurable primitive inputs were found. Ensure you exported in API format.'
					)
				);
			}
		}
		return true;
	}

	/**
	 * Reads config.COMFYUI_WORKFLOW, validates it, and triggers node auto-detection.
	 * @param showToast   - Surface toasts to the user.
	 * @param isNewImport - When true, ignore previously-saved node IDs (fresh import).
	 */
	const parseWorkflowAndUpdateNodes = (showToast = false, isNewImport = false) => {
		const wfString: string = config.COMFYUI_WORKFLOW ?? '';

		// Skip if nothing changed (unless it's an explicit new import)
		if (showToast && wfString === lastKnownWorkflowString && !isNewImport) return;

		if (wfString.trim() === '') {
			workflowNodesConfig = [];
			lastKnownWorkflowString = wfString;
			return;
		}

		try {
			const parsed = JSON.parse(wfString);
			const isValidApiFormat = Object.values(parsed).some(
				(n: any) => n && typeof n === 'object' && n.class_type && n.inputs
			);

			if (!isValidApiFormat) {
				workflowNodesConfig = [];
				if (showToast)
					toast.warning(
						$i18n.t(
							'Not a valid ComfyUI API Workflow JSON format. Make sure to export as API format from ComfyUI.'
						)
					);
				return;
			}

			const reconcileWith = isNewImport ? [] : (config.COMFYUI_WORKFLOW_NODES ?? []);
			const ok = parseAndPopulateWorkflowNodes(parsed, reconcileWith, showToast);
			if (ok) lastKnownWorkflowString = wfString;
		} catch {
			workflowNodesConfig = [];
			if (showToast) toast.error($i18n.t('Invalid JSON syntax in ComfyUI Workflow.'));
		}
	};

	let showComfyUIEditWorkflowEditor = false;

	// Dynamic edit-workflow node config
	let editWorkflowNodesConfig: {
		type: string;
		key: string;
		node_ids: string;
		class_type: string;
	}[] = [];
	let lastKnownEditWorkflowString: string | null = null;

	/**
	 * Same as parseWorkflowAndUpdateNodes but operates on the edit-workflow config.
	 */
	const parseEditWorkflowAndUpdateNodes = (showToast = false, isNewImport = false) => {
		const wfString: string = config.IMAGES_EDIT_COMFYUI_WORKFLOW ?? '';

		if (showToast && wfString === lastKnownEditWorkflowString && !isNewImport) return;

		if (wfString.trim() === '') {
			editWorkflowNodesConfig = [];
			lastKnownEditWorkflowString = wfString;
			return;
		}

		try {
			const parsed = JSON.parse(wfString);
			const isValidApiFormat = Object.values(parsed).some(
				(n: any) => n && typeof n === 'object' && n.class_type && n.inputs
			);

			if (!isValidApiFormat) {
				editWorkflowNodesConfig = [];
				if (showToast)
					toast.warning(
						$i18n.t(
							'Not a valid ComfyUI API Workflow JSON format. Make sure to export as API format from ComfyUI.'
						)
					);
				return;
			}

			const reconcileWith = isNewImport ? [] : (config.IMAGES_EDIT_COMFYUI_WORKFLOW_NODES ?? []);
			// Re-use the same parsing function, writing to editWorkflowNodesConfig
			const savedNodes = reconcileWith;
			if (!parsed || typeof parsed !== 'object') {
				editWorkflowNodesConfig = [];
				return;
			}
			const nodeGroups = new Map<
				string,
				{ type: string; key: string; node_ids: string[]; class_type: string }
			>();
			for (const nodeId of Object.keys(parsed)) {
				const node = parsed[nodeId];
				if (!node || typeof node !== 'object' || !node.inputs || typeof node.inputs !== 'object')
					continue;
				for (const inputKey of Object.keys(node.inputs)) {
					const val = node.inputs[inputKey];
					const valType = typeof val;
					if (valType !== 'string' && valType !== 'number' && valType !== 'boolean') continue;

					// Unique key per node+input — never merges across different node IDs
					const entryKey = `${nodeId}::${node.class_type}::${inputKey}`;
					const semanticType = `${node.class_type}::${inputKey}`;

					if (!nodeGroups.has(entryKey)) {
						// Same ambiguous-key logic as parseAndPopulateWorkflowNodes
						const ambiguousKeys = new Set(['text', 'prompt', 'positive']);
						const autoAssign = !ambiguousKeys.has(inputKey);

						nodeGroups.set(entryKey, {
							type: semanticType,
							key: inputKey,
							node_ids: autoAssign ? [nodeId] : [],
							class_type: node.class_type
						});
					}
				}
			}
			editWorkflowNodesConfig = Array.from(nodeGroups.values()).map((n) => ({
				...n,
				node_ids: n.node_ids.join(',')
			}));

			if (showToast && editWorkflowNodesConfig.length > 0) {
				toast.success(
					$i18n.t(
						`Workflow parsed. {{count}} configurable input(s) found. Please review the Node IDs.`,
						{ count: editWorkflowNodesConfig.length }
					)
				);
			}
			lastKnownEditWorkflowString = wfString;
		} catch {
			editWorkflowNodesConfig = [];
			if (showToast) toast.error($i18n.t('Invalid JSON syntax in ComfyUI Workflow.'));
		}
	};

	const getModels = async () => {
		models = await getImageGenerationModels(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
	};

	const updateConfigHandler = async () => {
		if (
			config.IMAGE_GENERATION_ENGINE === 'automatic1111' &&
			config.AUTOMATIC1111_BASE_URL === ''
		) {
			toast.error($i18n.t('AUTOMATIC1111 Base URL is required.'));
			config.ENABLE_IMAGE_GENERATION = false;

			return null;
		} else if (config.IMAGE_GENERATION_ENGINE === 'comfyui' && config.COMFYUI_BASE_URL === '') {
			toast.error($i18n.t('ComfyUI Base URL is required.'));
			config.ENABLE_IMAGE_GENERATION = false;

			return null;
		} else if (config.IMAGE_GENERATION_ENGINE === 'openai' && config.IMAGES_OPENAI_API_KEY === '') {
			toast.error($i18n.t('OpenAI API Key is required.'));
			config.ENABLE_IMAGE_GENERATION = false;

			return null;
		} else if (config.IMAGE_GENERATION_ENGINE === 'gemini' && config.IMAGES_GEMINI_API_KEY === '') {
			toast.error($i18n.t('Gemini API Key is required.'));
			config.ENABLE_IMAGE_GENERATION = false;

			return null;
		}

		const res = await updateConfig(localStorage.token, {
			...config,
			AUTOMATIC1111_PARAMS:
				typeof config.AUTOMATIC1111_PARAMS === 'string' && config.AUTOMATIC1111_PARAMS.trim() !== ''
					? JSON.parse(config.AUTOMATIC1111_PARAMS)
					: {},
			IMAGES_OPENAI_API_PARAMS:
				typeof config.IMAGES_OPENAI_API_PARAMS === 'string' &&
				config.IMAGES_OPENAI_API_PARAMS.trim() !== ''
					? JSON.parse(config.IMAGES_OPENAI_API_PARAMS)
					: {}
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			if (res.ENABLE_IMAGE_GENERATION) {
				backendConfig.set(await getBackendConfig());
				getModels();
			}

			return res;
		}

		return null;
	};

	const validateJSON = (json) => {
		try {
			const obj = JSON.parse(json);

			if (obj && typeof obj === 'object') {
				return true;
			}
		} catch (e) {}
		return false;
	};

	const saveHandler = async () => {
		loading = true;

		// Serialize dynamic workflow node configs before saving
		if (config?.COMFYUI_WORKFLOW) {
			if (!validateJSON(config?.COMFYUI_WORKFLOW)) {
				toast.error($i18n.t('Invalid JSON format for ComfyUI Workflow.'));
				loading = false;
				return;
			}
			config.COMFYUI_WORKFLOW_NODES = workflowNodesConfig.map((node) => ({
				type: node.type,
				key: node.key,
				node_ids: node.node_ids.trim() === '' ? [] : node.node_ids.split(',').map((id) => id.trim())
			}));
		}

		if (config?.IMAGES_EDIT_COMFYUI_WORKFLOW) {
			if (!validateJSON(config?.IMAGES_EDIT_COMFYUI_WORKFLOW)) {
				toast.error($i18n.t('Invalid JSON format for ComfyUI Edit Workflow.'));
				loading = false;
				return;
			}
			config.IMAGES_EDIT_COMFYUI_WORKFLOW_NODES = editWorkflowNodesConfig.map((node) => ({
				type: node.type,
				key: node.key,
				node_ids: node.node_ids.trim() === '' ? [] : node.node_ids.split(',').map((id) => id.trim())
			}));
		}

		const res = await updateConfigHandler();
		if (res) {
			dispatch('save');
		}

		loading = false;
	};

	onMount(async () => {
		if ($user?.role === 'admin') {
			const res = await getConfig(localStorage.token).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (res) {
				config = res;
			}

			if (!config) {
				return;
			}

			if (config.ENABLE_IMAGE_GENERATION) {
				getModels();
			}

			// Pretty-print stored workflow JSON for the code editor
			if (config.COMFYUI_WORKFLOW) {
				try {
					config.COMFYUI_WORKFLOW = JSON.stringify(JSON.parse(config.COMFYUI_WORKFLOW), null, 2);
				} catch (e) {
					console.error(e);
				}
				// Auto-parse on load, reconciling with any saved node configs
				parseWorkflowAndUpdateNodes(false, false);
			}

			if (config.IMAGES_EDIT_COMFYUI_WORKFLOW) {
				try {
					config.IMAGES_EDIT_COMFYUI_WORKFLOW = JSON.stringify(
						JSON.parse(config.IMAGES_EDIT_COMFYUI_WORKFLOW),
						null,
						2
					);
				} catch (e) {
					console.error(e);
				}
				parseEditWorkflowAndUpdateNodes(false, false);
			}

			config.IMAGES_OPENAI_API_PARAMS =
				typeof config.IMAGES_OPENAI_API_PARAMS === 'object'
					? JSON.stringify(config.IMAGES_OPENAI_API_PARAMS ?? {}, null, 2)
					: config.IMAGES_OPENAI_API_PARAMS;

			config.AUTOMATIC1111_PARAMS =
				typeof config.AUTOMATIC1111_PARAMS === 'object'
					? JSON.stringify(config.AUTOMATIC1111_PARAMS ?? {}, null, 2)
					: config.AUTOMATIC1111_PARAMS;
		}
	});
</script>

<form
	class="flex h-full flex-col justify-between text-sm"
	on:submit|preventDefault={async () => {
		saveHandler();
	}}
>
	<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">{$i18n.t('Images')}</h2>

	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		{#if config}
			<div class="flex flex-col">
				<AdminSettingSection first>
					<AdminSettingRow
						label={$i18n.t('Image Generation')}
						description={$i18n.t('Allow users to generate images from prompts.')}
					>
						<Switch bind:state={config.ENABLE_IMAGE_GENERATION} />
					</AdminSettingRow>
				</AdminSettingSection>

				<AdminSettingSection title={$i18n.t('Create Image')}>
					<AdminSettingRow
						label={$i18n.t('Image Generation Engine')}
						description={$i18n.t('Choose the provider used for image generation.')}
					>
						<SettingsSelect
							bind:value={config.IMAGE_GENERATION_ENGINE}
							placeholder={$i18n.t('Select Engine')}
						>
							<option value="openai">{$i18n.t('Default (Open AI)')}</option>
							<option value="comfyui">{$i18n.t('ComfyUI')}</option>
							<option value="automatic1111">{$i18n.t('Automatic1111')}</option>
							<option value="gemini">{$i18n.t('Gemini')}</option>
						</SettingsSelect>
					</AdminSettingRow>

					{#if config.ENABLE_IMAGE_GENERATION}
						<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
							<AdminSettingField label={$i18n.t('Model')}>
								<input
									list="model-list"
									class={inputClass}
									bind:value={config.IMAGE_GENERATION_MODEL}
									placeholder={$i18n.t('Select a model')}
									required
								/>

								<datalist id="model-list">
									{#each models ?? [] as model}
										<option value={model.id}>{model.name}</option>
									{/each}
								</datalist>
							</AdminSettingField>

							<AdminSettingField label={$i18n.t('Image Size')}>
								<input
									class={inputClass}
									placeholder={$i18n.t('Enter Image Size (e.g. 512x512)')}
									bind:value={config.IMAGE_SIZE}
								/>
							</AdminSettingField>

							{#if ['comfyui', 'automatic1111', ''].includes(config?.IMAGE_GENERATION_ENGINE)}
								<AdminSettingField label={$i18n.t('Steps')}>
									<input
										class={inputClass}
										placeholder={$i18n.t('Enter Number of Steps (e.g. 50)')}
										bind:value={config.IMAGE_STEPS}
										required
									/>
								</AdminSettingField>
							{/if}
						</div>

						<AdminSettingRow
							label={$i18n.t('Image Prompt Generation')}
							description={$i18n.t('Generate an image prompt before sending the request.')}
						>
							<Switch bind:state={config.ENABLE_IMAGE_PROMPT_GENERATION} />
						</AdminSettingRow>
					{/if}

					{#if config?.IMAGE_GENERATION_ENGINE === 'openai'}
						<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
							<AdminSettingField label={$i18n.t('API Base URL')}>
								<input
									class={inputClass}
									placeholder={$i18n.t('API Base URL')}
									bind:value={config.IMAGES_OPENAI_API_BASE_URL}
								/>
							</AdminSettingField>

							<AdminSettingField label={$i18n.t('API Key')}>
								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('API Key')}
									bind:value={config.IMAGES_OPENAI_API_KEY}
									required={false}
								/>
							</AdminSettingField>
						</div>

						<AdminSettingField label={$i18n.t('API Version')}>
							<input
								class={inputClass}
								placeholder={$i18n.t('API Version')}
								bind:value={config.IMAGES_OPENAI_API_VERSION}
							/>
						</AdminSettingField>

						<AdminSettingField
							label={$i18n.t('Additional Parameters')}
							description={$i18n.t(
								'Send extra JSON parameters with each image generation request.'
							)}
						>
							<Textarea
								className={textareaClass}
								bind:value={config.IMAGES_OPENAI_API_PARAMS}
								placeholder={$i18n.t('Enter additional parameters in JSON format')}
								minSize={100}
							/>
						</AdminSettingField>
					{:else if (config?.IMAGE_GENERATION_ENGINE ?? 'automatic1111') === 'automatic1111'}
						<AdminSettingField
							label={$i18n.t('Base URL')}
							description={$i18n.t(
								'Connect to a stable-diffusion-webui server running with the `--api` flag.'
							)}
						>
							<div class="flex w-full gap-2">
								<input
									class={inputClass}
									placeholder={$i18n.t('Enter URL (e.g. http://127.0.0.1:7860/)')}
									bind:value={config.AUTOMATIC1111_BASE_URL}
								/>
								<button
									class="shrink-0 text-gray-400 transition-colors hover:text-gray-900 dark:text-gray-600 dark:hover:text-white"
									type="button"
									aria-label="verify connection"
									on:click={async () => {
										await updateConfigHandler();
										const res = await verifyConfigUrl(localStorage.token).catch((error) => {
											toast.error(`${error}`);
											return null;
										});

										if (res) {
											toast.success($i18n.t('Server connection verified'));
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
											fill-rule="evenodd"
											d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
											clip-rule="evenodd"
										/>
									</svg>
								</button>
							</div>
						</AdminSettingField>

						<AdminSettingField
							label={$i18n.t('API Auth String')}
							description={$i18n.t('Provide the --api-auth username and password when required.')}
						>
							<SensitiveInput
								variant="settings"
								placeholder={$i18n.t('Enter api auth string (e.g. username:password)')}
								bind:value={config.AUTOMATIC1111_API_AUTH}
								required={false}
							/>
						</AdminSettingField>

						<AdminSettingField
							label={$i18n.t('Additional Parameters')}
							description={$i18n.t('Send extra JSON parameters with each AUTOMATIC1111 request.')}
						>
							<Textarea
								className={textareaClass}
								bind:value={config.AUTOMATIC1111_PARAMS}
								placeholder={$i18n.t('Enter additional parameters in JSON format')}
								minSize={100}
							/>
						</AdminSettingField>
					{:else if config?.IMAGE_GENERATION_ENGINE === 'comfyui'}
						<AdminSettingField
							label={$i18n.t('Base URL')}
							description={$i18n.t('Connect to the ComfyUI server used for generation.')}
						>
							<div class="flex w-full gap-2">
								<input
									class={inputClass}
									placeholder={$i18n.t('Enter URL (e.g. http://127.0.0.1:7860/)')}
									bind:value={config.COMFYUI_BASE_URL}
								/>
								<button
									class="shrink-0 text-gray-400 transition-colors hover:text-gray-900 dark:text-gray-600 dark:hover:text-white"
									type="button"
									aria-label="verify connection"
									on:click={async () => {
										await updateConfigHandler();
										const res = await verifyConfigUrl(localStorage.token).catch((error) => {
											toast.error(`${error}`);
											return null;
										});

										if (res) {
											toast.success($i18n.t('Server connection verified'));
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
											fill-rule="evenodd"
											d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
											clip-rule="evenodd"
										/>
									</svg>
								</button>
							</div>
						</AdminSettingField>

						<AdminSettingField
							label={$i18n.t('API Key')}
							description={$i18n.t('Use an API key when your ComfyUI server requires one.')}
						>
							<SensitiveInput
								variant="settings"
								placeholder={$i18n.t('sk-1234')}
								bind:value={config.COMFYUI_API_KEY}
								required={false}
							/>
						</AdminSettingField>

						<div>
							<input
								id="upload-comfyui-workflow-input"
								hidden
								type="file"
								accept=".json"
								on:change={(e) => {
									const file = e.target.files[0];
									if (!file) return;
									const reader = new FileReader();
									reader.onload = (ev) => {
										config.COMFYUI_WORKFLOW = ev.target.result as string;
										// Auto-detect nodes from fresh import
										parseWorkflowAndUpdateNodes(true, true);
										(e.target as HTMLInputElement).value = '';
									};
									reader.readAsText(file);
								}}
							/>
							<AdminSettingRow
								label={$i18n.t('ComfyUI Workflow')}
								description={$i18n.t(
									'Upload a workflow.json file exported as API format from ComfyUI.'
								)}
							>
								<div class="flex items-center justify-end gap-2">
									{#if config.COMFYUI_WORKFLOW}
										<button
											class="text-xs text-gray-500 transition-colors hover:text-gray-900 hover:underline dark:text-gray-500 dark:hover:text-white"
											type="button"
											aria-label={$i18n.t('Edit workflow.json content')}
											on:click={() => {
												// open code editor modal
												showComfyUIWorkflowEditor = true;
											}}
										>
											{$i18n.t('Edit')}
										</button>
									{/if}

									<Tooltip content={$i18n.t('Click here to upload a workflow.json file.')}>
										<button
											class="text-xs text-gray-500 transition-colors hover:text-gray-900 hover:underline dark:text-gray-500 dark:hover:text-white"
											type="button"
											aria-label={$i18n.t('Click here to upload a workflow.json file.')}
											on:click={() => {
												document.getElementById('upload-comfyui-workflow-input')?.click();
											}}
										>
											{$i18n.t('Upload')}
										</button>
									</Tooltip>
								</div>
							</AdminSettingRow>

							<div>
								<CodeEditorModal
									bind:show={showComfyUIWorkflowEditor}
									value={config.COMFYUI_WORKFLOW}
									lang="json"
									onChange={(e) => {
										config.COMFYUI_WORKFLOW = e;
										// Re-detect nodes as the user edits JSON
										parseWorkflowAndUpdateNodes(false, false);
									}}
									onSave={() => {
										parseWorkflowAndUpdateNodes(true, false);
									}}
								/>
								<!-- {#if config.COMFYUI_WORKFLOW}
								<Textarea
									className="my-1 w-full resize-none rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 disabled:text-gray-600 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500"
									rows="10"
										bind:value={config.COMFYUI_WORKFLOW}
									required
								/>
							{/if} -->
							</div>
						</div>

						{#if config.COMFYUI_WORKFLOW}
							<AdminSettingField
								label={$i18n.t('ComfyUI Workflow Nodes')}
								description={$i18n.t(
									'Node IDs are auto-detected from your workflow. Adjust them if needed.'
								)}
							>
								{#if workflowNodesConfig.length > 0}
									<div class="flex items-center gap-1 text-xs text-green-500 dark:text-green-400">
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 16 16"
											fill="currentColor"
											class="w-3 h-3"
										>
											<path
												fill-rule="evenodd"
												d="M12.416 3.376a.75.75 0 0 1 .208 1.04l-5 7.5a.75.75 0 0 1-1.154.114l-3-3a.75.75 0 0 1 1.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 0 1 1.04-.207Z"
												clip-rule="evenodd"
											/>
										</svg>
										{$i18n.t('Auto-detected')}
									</div>

									<div class="mt-1 flex flex-col gap-1.5 text-xs">
										{#each workflowNodesConfig as node}
											<div class="flex w-full flex-col">
												<div class="shrink-0">
													<div
														class="capitalize line-clamp-1 w-20 text-gray-400 dark:text-gray-500"
														title={node.type}
													>
														{node.class_type}
													</div>
												</div>

												<div class="mt-0.5 flex items-center">
													<div class="">
														<Tooltip content={$i18n.t('Input Key (e.g. text, unet_name, steps)')}>
															<input
																class="{inputClass} w-24"
																placeholder={$i18n.t('Key')}
																bind:value={node.key}
																required
															/>
														</Tooltip>
													</div>

													<div class="px-2 text-gray-400 dark:text-gray-500">:</div>

													<div class="w-full">
														<Tooltip
															content={$i18n.t('Comma separated Node Ids (e.g. 1 or 1,2)')}
															placement="top-start"
														>
															<input
																class={inputClass}
																placeholder={$i18n.t('Node Ids')}
																bind:value={node.node_ids}
															/>
														</Tooltip>
													</div>
												</div>
											</div>
										{/each}
									</div>
								{:else}
									<div class="mt-1 text-xs text-gray-400 dark:text-gray-500">
										{$i18n.t('No configurable inputs detected. Upload a workflow in API format.')}
									</div>
								{/if}
							</AdminSettingField>
						{/if}
					{:else if config?.IMAGE_GENERATION_ENGINE === 'gemini'}
						<AdminSettingField
							label={$i18n.t('Base URL')}
							description={$i18n.t('Override the Gemini image generation endpoint.')}
						>
							<input
								class={inputClass}
								placeholder={$i18n.t('API Base URL')}
								bind:value={config.IMAGES_GEMINI_API_BASE_URL}
							/>
						</AdminSettingField>

						<AdminSettingField
							label={$i18n.t('API Key')}
							description={$i18n.t('Use a Gemini API key for image generation.')}
						>
							<SensitiveInput
								variant="settings"
								placeholder={$i18n.t('API Key')}
								bind:value={config.IMAGES_GEMINI_API_KEY}
								required={true}
							/>
						</AdminSettingField>

						<AdminSettingRow
							label={$i18n.t('Gemini Endpoint Method')}
							description={$i18n.t('Select the Gemini endpoint method to call.')}
						>
							<SettingsSelect
								bind:value={config.IMAGES_GEMINI_ENDPOINT_METHOD}
								placeholder={$i18n.t('Select Method')}
							>
								<option value="predict">predict</option>
								<option value="generateContent">generateContent</option>
							</SettingsSelect>
						</AdminSettingRow>
					{/if}
				</AdminSettingSection>

				<AdminSettingSection title={$i18n.t('Edit Image')}>
					<AdminSettingRow
						label={$i18n.t('Image Edit')}
						description={$i18n.t('Allow users to edit existing images.')}
					>
						<Switch bind:state={config.ENABLE_IMAGE_EDIT} />
					</AdminSettingRow>

					<AdminSettingRow
						label={$i18n.t('Image Edit Engine')}
						description={$i18n.t('Choose the provider used for image edits.')}
					>
						<SettingsSelect
							bind:value={config.IMAGE_EDIT_ENGINE}
							placeholder={$i18n.t('Select Engine')}
						>
							<option value="openai">{$i18n.t('Default (Open AI)')}</option>
							<option value="comfyui">{$i18n.t('ComfyUI')}</option>
							<option value="gemini">{$i18n.t('Gemini')}</option>
						</SettingsSelect>
					</AdminSettingRow>

					{#if config?.ENABLE_IMAGE_GENERATION && config?.ENABLE_IMAGE_EDIT}
						<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
							<AdminSettingField label={$i18n.t('Model')}>
								<input
									list="model-list"
									class={inputClass}
									bind:value={config.IMAGE_EDIT_MODEL}
									placeholder={$i18n.t('Select a model')}
								/>

								<datalist id="model-list">
									{#each models ?? [] as model}
										<option value={model.id}>{model.name}</option>
									{/each}
								</datalist>
							</AdminSettingField>

							<AdminSettingField label={$i18n.t('Image Size')}>
								<input
									class={inputClass}
									placeholder={$i18n.t('Enter Image Size (e.g. 512x512)')}
									bind:value={config.IMAGE_EDIT_SIZE}
								/>
							</AdminSettingField>
						</div>
					{/if}

					{#if config?.IMAGE_EDIT_ENGINE === 'openai'}
						<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
							<AdminSettingField label={$i18n.t('API Base URL')}>
								<input
									class={inputClass}
									placeholder={$i18n.t('API Base URL')}
									bind:value={config.IMAGES_EDIT_OPENAI_API_BASE_URL}
								/>
							</AdminSettingField>

							<AdminSettingField label={$i18n.t('API Key')}>
								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('API Key')}
									bind:value={config.IMAGES_EDIT_OPENAI_API_KEY}
									required={false}
								/>
							</AdminSettingField>
						</div>

						<AdminSettingField label={$i18n.t('API Version')}>
							<input
								class={inputClass}
								placeholder={$i18n.t('API Version')}
								bind:value={config.IMAGES_EDIT_OPENAI_API_VERSION}
							/>
						</AdminSettingField>
					{:else if config?.IMAGE_EDIT_ENGINE === 'comfyui'}
						<AdminSettingField
							label={$i18n.t('Base URL')}
							description={$i18n.t('Connect to the ComfyUI server used for image edits.')}
						>
							<div class="flex w-full gap-2">
								<input
									class={inputClass}
									placeholder={$i18n.t('Enter URL (e.g. http://127.0.0.1:7860/)')}
									bind:value={config.IMAGES_EDIT_COMFYUI_BASE_URL}
								/>
								<button
									class="shrink-0 text-gray-400 transition-colors hover:text-gray-900 dark:text-gray-600 dark:hover:text-white"
									type="button"
									aria-label="verify connection"
									on:click={async () => {
										await updateConfigHandler();
										const res = await verifyConfigUrl(localStorage.token).catch((error) => {
											toast.error(`${error}`);
											return null;
										});

										if (res) {
											toast.success($i18n.t('Server connection verified'));
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
											fill-rule="evenodd"
											d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
											clip-rule="evenodd"
										/>
									</svg>
								</button>
							</div>
						</AdminSettingField>

						<AdminSettingField
							label={$i18n.t('API Key')}
							description={$i18n.t('Use an API key when your ComfyUI server requires one.')}
						>
							<SensitiveInput
								variant="settings"
								placeholder={$i18n.t('sk-1234')}
								bind:value={config.IMAGES_EDIT_COMFYUI_API_KEY}
								required={false}
							/>
						</AdminSettingField>

						<div>
							<input
								id="upload-comfyui-edit-workflow-input"
								hidden
								type="file"
								accept=".json"
								on:change={(e) => {
									const file = e.target.files[0];
									if (!file) return;
									const reader = new FileReader();
									reader.onload = (ev) => {
										config.IMAGES_EDIT_COMFYUI_WORKFLOW = ev.target.result as string;
										// Auto-detect nodes from fresh import
										parseEditWorkflowAndUpdateNodes(true, true);
										(e.target as HTMLInputElement).value = '';
									};
									reader.readAsText(file);
								}}
							/>
							<AdminSettingRow
								label={$i18n.t('ComfyUI Workflow')}
								description={$i18n.t(
									'Upload a workflow.json file exported as API format from ComfyUI.'
								)}
							>
								<div class="flex items-center justify-end gap-2">
									{#if config.IMAGES_EDIT_COMFYUI_WORKFLOW}
										<button
											class="text-xs text-gray-500 transition-colors hover:text-gray-900 hover:underline dark:text-gray-500 dark:hover:text-white"
											type="button"
											aria-label={$i18n.t('Edit workflow.json content')}
											on:click={() => {
												// open code editor modal
												showComfyUIEditWorkflowEditor = true;
											}}
										>
											{$i18n.t('Edit')}
										</button>
									{/if}

									<Tooltip content={$i18n.t('Click here to upload a workflow.json file.')}>
										<button
											class="text-xs text-gray-500 transition-colors hover:text-gray-900 hover:underline dark:text-gray-500 dark:hover:text-white"
											type="button"
											aria-label={$i18n.t('Click here to upload a workflow.json file.')}
											on:click={() => {
												document.getElementById('upload-comfyui-edit-workflow-input')?.click();
											}}
										>
											{$i18n.t('Upload')}
										</button>
									</Tooltip>
								</div>
							</AdminSettingRow>

							<CodeEditorModal
								bind:show={showComfyUIEditWorkflowEditor}
								value={config.IMAGES_EDIT_COMFYUI_WORKFLOW}
								lang="json"
								onChange={(e) => {
									config.IMAGES_EDIT_COMFYUI_WORKFLOW = e;
									// Re-detect nodes as the user edits JSON
									parseEditWorkflowAndUpdateNodes(false, false);
								}}
								onSave={() => {
									parseEditWorkflowAndUpdateNodes(true, false);
								}}
							/>
						</div>

						{#if config.IMAGES_EDIT_COMFYUI_WORKFLOW}
							<AdminSettingField
								label={$i18n.t('ComfyUI Workflow Nodes')}
								description={$i18n.t(
									'Node IDs are auto-detected from your workflow. Adjust them if needed.'
								)}
							>
								{#if editWorkflowNodesConfig.length > 0}
									<div class="flex items-center gap-1 text-xs text-green-500 dark:text-green-400">
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 16 16"
											fill="currentColor"
											class="w-3 h-3"
										>
											<path
												fill-rule="evenodd"
												d="M12.416 3.376a.75.75 0 0 1 .208 1.04l-5 7.5a.75.75 0 0 1-1.154.114l-3-3a.75.75 0 0 1 1.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 0 1 1.04-.207Z"
												clip-rule="evenodd"
											/>
										</svg>
										{$i18n.t('Auto-detected')}
									</div>

									<div class="mt-1 flex flex-col gap-1.5 text-xs">
										{#each editWorkflowNodesConfig as node}
											<div class="flex w-full flex-col">
												<div class="shrink-0">
													<div
														class="capitalize line-clamp-1 w-20 text-gray-400 dark:text-gray-500"
														title={node.type}
													>
														{node.class_type}
													</div>
												</div>

												<div class="mt-0.5 flex items-center">
													<div class="">
														<Tooltip content={$i18n.t('Input Key (e.g. text, unet_name, steps)')}>
															<input
																class="{inputClass} w-24"
																placeholder={$i18n.t('Key')}
																bind:value={node.key}
																required
															/>
														</Tooltip>
													</div>

													<div class="px-2 text-gray-400 dark:text-gray-500">:</div>

													<div class="w-full">
														<Tooltip
															content={$i18n.t('Comma separated Node Ids (e.g. 1 or 1,2)')}
															placement="top-start"
														>
															<input
																class={inputClass}
																placeholder={$i18n.t('Node Ids')}
																bind:value={node.node_ids}
															/>
														</Tooltip>
													</div>
												</div>
											</div>
										{/each}
									</div>
								{:else}
									<div class="mt-1 text-xs text-gray-400 dark:text-gray-500">
										{$i18n.t('No configurable inputs detected. Upload a workflow in API format.')}
									</div>
								{/if}
							</AdminSettingField>
						{/if}
					{:else if config?.IMAGE_EDIT_ENGINE === 'gemini'}
						<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
							<AdminSettingField label={$i18n.t('Base URL')}>
								<input
									class={inputClass}
									placeholder={$i18n.t('API Base URL')}
									bind:value={config.IMAGES_EDIT_GEMINI_API_BASE_URL}
								/>
							</AdminSettingField>

							<AdminSettingField label={$i18n.t('API Key')}>
								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('API Key')}
									bind:value={config.IMAGES_EDIT_GEMINI_API_KEY}
									required={true}
								/>
							</AdminSettingField>
						</div>
					{/if}
				</AdminSettingSection>
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-6 text-sm font-normal">
		<button
			class="px-3.5 py-1.5 text-sm font-normal bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex items-center gap-2 whitespace-nowrap {loading
				? ' cursor-not-allowed'
				: ''}"
			type="submit"
			disabled={loading}
		>
			{$i18n.t('Save')}

			{#if loading}
				<span class="shrink-0">
					<Spinner />
				</span>
			{/if}
		</button>
	</div>
</form>
