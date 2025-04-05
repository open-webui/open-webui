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
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	let loading = false;

	let config = null;
	let imageGenerationConfig = null;

	let models = null;

	let samplers = [
		'DPM++ 2M',
		'DPM++ SDE',
		'DPM++ 2M SDE',
		'DPM++ 2M SDE Heun',
		'DPM++ 2S a',
		'DPM++ 3M SDE',
		'Euler a',
		'Euler',
		'LMS',
		'Heun',
		'DPM2',
		'DPM2 a',
		'DPM fast',
		'DPM adaptive',
		'Restart',
		'DDIM',
		'DDIM CFG++',
		'PLMS',
		'UniPC'
	];

	let schedulers = [
		'Automatic',
		'Uniform',
		'Karras',
		'Exponential',
		'Polyexponential',
		'SGM Uniform',
		'KL Optimal',
		'Align Your Steps',
		'Simple',
		'Normal',
		'DDIM',
		'Beta'
	];

	// This will hold the dynamically generated node configurations
	let workflowNodesConfig = [];
	let isDraggingOver = false; // State for drag-and-drop visual feedback

	const getModels = async () => {
		models = await getImageGenerationModels(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
	};

	const updateConfigHandler = async () => {
		const res = await updateConfig(localStorage.token, config)
			.catch((error) => {
				toast.error(`${error}`);
				return null;
			})
			.catch((error) => {
				toast.error(`${error}`);
				return null;
			});

		if (res) {
			config = res;
		}

		if (config.enabled) {
			backendConfig.set(await getBackendConfig());
			getModels();
		}
	};

	const validateJSON = (json) => {
		try {
			const obj = JSON.parse(json);

			if (obj && typeof obj === 'object') {
				// Basic check for ComfyUI API format (presence of nodes with class_type)
				if (
					Object.values(obj).some(
						(node: any) => node && typeof node === 'object' && node.class_type && node.inputs
					)
				) {
					return true;
				}
			}
		} catch (e) {}
		return false;
	};

	// Parses the workflow and populates workflowNodesConfig based on discovered primitive inputs
	// Added 'showToast' parameter to control notifications
	function parseAndPopulateWorkflowNodes(workflow, savedNodesConfig = [], showToast = false) {
		if (!workflow || typeof workflow !== 'object') {
			if (showToast) toast.error('Invalid workflow data provided for parsing.');
			workflowNodesConfig = []; // Clear existing config
			return;
		}

		// Map to group nodes by class_type and input_key
		const nodeGroups = new Map<
			string,
			{ type: string; key: string; node_ids: string[]; class_type: string }
		>();
		let discoveredPrimitiveCount = 0;

		try {
			for (const nodeId in workflow) {
				if (Object.prototype.hasOwnProperty.call(workflow, nodeId)) {
					const node = workflow[nodeId];
					// Ensure node is valid and has inputs
					if (node && typeof node === 'object' && node.inputs && typeof node.inputs === 'object') {
						for (const inputKey in node.inputs) {
							if (Object.prototype.hasOwnProperty.call(node.inputs, inputKey)) {
								const inputValue = node.inputs[inputKey];
								const valueType = typeof inputValue;

								// Identify primitive inputs (string, number, boolean)
								// These are the most likely candidates for dynamic control
								if (valueType === 'string' || valueType === 'number' || valueType === 'boolean') {
									discoveredPrimitiveCount++;
									const groupKey = `${node.class_type}::${inputKey}`; // Unique identifier for the input type

									// Find if this specific input was previously saved/configured
									const savedNode = savedNodesConfig.find(
										(s) => s.type === groupKey && s.key === inputKey
									);

									if (nodeGroups.has(groupKey)) {
										// Add node ID to existing group
										const group = nodeGroups.get(groupKey);
										// Only add the auto-discovered ID if this group wasn't explicitly saved before
										// If it was saved, we rely solely on the saved IDs for this group.
										if (!savedNode) {
											group.node_ids.push(nodeId);
											// Ensure uniqueness within auto-discovered IDs for the group
											group.node_ids = [...new Set(group.node_ids)];
										}
									} else {
										// Create a new group for this input type
										// Use saved node_ids if available, otherwise use the current nodeId
										const initialNodeIds = savedNode
											? Array.isArray(savedNode.node_ids)
												? savedNode.node_ids // Use saved array
												: [savedNode.node_ids.toString()] // Convert saved single ID to array
											: [nodeId]; // Start with the newly discovered ID

										nodeGroups.set(groupKey, {
											type: groupKey, // Store the unique identifier as 'type'
											key: inputKey,
											node_ids: [...new Set(initialNodeIds)], // Ensure initial IDs are unique
											class_type: node.class_type
										});
									}
								}
							}
						}
					}
				}
			}
		} catch (error) {
			console.error('Error parsing workflow nodes:', error);
			if (showToast) toast.error(`Error occurred during workflow parsing: ${error.message}`);
			workflowNodesConfig = []; // Clear on error
			return;
		}

		// Convert map values to array
		const newConfig = Array.from(nodeGroups.values());

		// Update the component state, converting node_ids array to comma-separated string for input fields
		workflowNodesConfig = newConfig.map((node) => ({
			...node,
			node_ids: node.node_ids.join(',') // Join for display/editing in input field
		}));

		// Provide feedback only if requested
		if (showToast) {
			if (workflowNodesConfig.length > 0) {
				if (savedNodesConfig.length > 0 && discoveredPrimitiveCount > 0) {
					toast.success(
						`Workflow parsed. ${workflowNodesConfig.length} configurable inputs found/updated based on workflow and saved settings. Please review.`
					);
				} else if (discoveredPrimitiveCount > 0) {
					toast.success(
						`Workflow parsed. ${workflowNodesConfig.length} configurable inputs found. Please review the Node IDs.`
					);
				} else {
					// Workflow parsed, but only previously saved nodes are shown (no new primitives found)
					// Avoid toast if only saved nodes are shown after user action
					// toast.info(
					// 	`Workflow parsed. Displaying ${workflowNodesConfig.length} previously saved configurations. No new primitive inputs were found in this workflow.`
					// );
				}
			} else if (discoveredPrimitiveCount === 0 && Object.keys(workflow).length > 0) {
				toast.info(
					'Workflow parsed, but no primitive input nodes (like text fields, numbers, booleans) were automatically found to configure.'
				);
			}
		}
	}

	const saveHandler = async () => {
		loading = true;

		// Validate Workflow JSON if present
		if (config?.comfyui?.COMFYUI_WORKFLOW && config.comfyui.COMFYUI_WORKFLOW.trim() !== '') {
			if (!validateJSON(config.comfyui.COMFYUI_WORKFLOW)) {
				toast.error(
					'Invalid JSON format for ComfyUI Workflow. Please ensure it is valid API format JSON.'
				);
				loading = false;
				return;
			}
		} else if (config?.engine === 'comfyui') {
			// Clear node configs if workflow is removed
			config.comfyui.COMFYUI_WORKFLOW_NODES = [];
			workflowNodesConfig = [];
		}

		// Format the node data for saving if engine is ComfyUI
		if (
			config?.engine === 'comfyui' &&
			config?.comfyui?.COMFYUI_WORKFLOW &&
			config.comfyui.COMFYUI_WORKFLOW.trim() !== ''
		) {
			try {
				config.comfyui.COMFYUI_WORKFLOW_NODES = workflowNodesConfig.map((node) => {
					// Validate node_ids format (comma-separated numbers)
					const nodeIdsString = node.node_ids.trim(); // Value from the input field
					let nodeIdsArray = [];
					if (nodeIdsString !== '') {
						const potentialIds = nodeIdsString.split(',').map((id) => id.trim());
						// Check if all parts are non-empty and numeric
						if (potentialIds.every((id) => id !== '' && /^\d+$/.test(id))) {
							nodeIdsArray = potentialIds; // Store as array of strings
						} else {
							toast.warning(
								`Invalid format for Node IDs for '${node.type}'. Please use comma-separated numbers (e.g., 6 or 6,10). Saving with potentially incorrect IDs.`
							);
							// Save non-empty parts even if invalid, but warn user
							nodeIdsArray = potentialIds.filter((id) => id !== '');
						}
					}

					// Basic check for key and type (should always be present from parsing)
					if (!node.key || node.key.trim() === '') {
						toast.error(`Key cannot be empty for node type '${node.type}'. Save failed.`);
						throw new Error(`Missing key for node type '${node.type}'`);
					}
					if (!node.type || node.type.trim() === '') {
						toast.error(
							`Type identifier cannot be empty for node with key '${node.key}'. Save failed.`
						);
						throw new Error(`Missing type for node with key '${node.key}'`);
					}

					return {
						type: node.type, // The unique identifier (class_type::key)
						key: node.key.trim(),
						node_ids: nodeIdsArray // Save as array of strings
					};
				});
			} catch (error) {
				// Error already toasted, just ensure loading is false and return
				loading = false;
				console.error('Error formatting workflow nodes for saving:', error);
				return; // Stop the save handler
			}
		} else if (config?.engine === 'comfyui') {
			// If ComfyUI engine is selected but workflow is empty, ensure nodes are cleared
			config.comfyui.COMFYUI_WORKFLOW_NODES = [];
		}

		// Proceed with saving main config and image config
		try {
			await updateConfig(localStorage.token, config).catch((error) => {
				toast.error(`Error saving main config: ${error}`);
				loading = false;
				throw error; // Re-throw to stop execution
			});

			await updateImageGenerationConfig(localStorage.token, imageGenerationConfig).catch(
				(error) => {
					toast.error(`Error saving image generation config: ${error}`);
					loading = false;
					throw error; // Re-throw to stop execution
				}
			);

			getModels(); // Refresh models list if applicable
			dispatch('save');
		} catch (error) {
			// Errors are handled and toasted within the catch blocks above
			console.error('Save handler failed:', error);
		} finally {
			loading = false;
		}
	};

	// Function to handle parsing when the textarea loses focus (blur event)
	const handleWorkflowBlur = () => {
		if (config.comfyui.COMFYUI_WORKFLOW && config.comfyui.COMFYUI_WORKFLOW.trim() !== '') {
			try {
				const parsedWorkflow = JSON.parse(config.comfyui.COMFYUI_WORKFLOW);
				if (validateJSON(config.comfyui.COMFYUI_WORKFLOW)) {
					// Parse and show toast on blur if content is valid API format
					parseAndPopulateWorkflowNodes(parsedWorkflow, [], true); // Pass true for showToast
				} else {
					// JSON is valid structure but not API format
					workflowNodesConfig = []; // Clear nodes
					toast.warning(
						'Pasted content is not a valid ComfyUI API Workflow JSON format. No inputs parsed.'
					);
				}
			} catch (error) {
				// JSON is invalid syntax
				workflowNodesConfig = []; // Clear nodes
				toast.error('Invalid JSON syntax in ComfyUI Workflow. Please correct it.');
			}
		} else {
			workflowNodesConfig = []; // Clear nodes if text area is empty
		}
	};

	// Function to process a file (used by both upload and drop)
	const processWorkflowFile = (file: File) => {
		if (!file) return;

		// Check if the file is JSON
		if (!file.type.includes('json') && !file.name.endsWith('.json')) {
			toast.error('Invalid file type. Please upload a .json file.');
			return;
		}

		const reader = new FileReader();
		reader.onload = (event) => {
			try {
				if (!event.target?.result || typeof event.target.result !== 'string') {
					throw new Error('FileReader did not return a string result.');
				}
				const rawJson = event.target.result;
				const parsedWorkflow = JSON.parse(rawJson);

				// Validate format using our function
				if (validateJSON(rawJson)) {
					config.comfyui.COMFYUI_WORKFLOW = JSON.stringify(parsedWorkflow, null, 2); // Pretty print
					// Parse the newly uploaded workflow, clearing previous node configs, SHOW TOAST
					parseAndPopulateWorkflowNodes(parsedWorkflow, [], true);
					toast.success('Workflow JSON loaded and parsed successfully.');
				} else {
					toast.error(
						'Invalid ComfyUI API Workflow JSON format. Ensure it was exported as API format.'
					);
					// Display the raw text but clear parsed nodes
					config.comfyui.COMFYUI_WORKFLOW = rawJson;
					workflowNodesConfig = [];
				}
			} catch (error) {
				toast.error(`Error reading or parsing workflow file: ${error.message}`);
				if (event.target?.result && typeof event.target.result === 'string') {
					config.comfyui.COMFYUI_WORKFLOW = event.target.result; // Show raw text on error
				} else {
					config.comfyui.COMFYUI_WORKFLOW = '';
				}
				workflowNodesConfig = []; // Clear nodes on error
			}
		};
		reader.onerror = (error) => {
			toast.error(`Error reading file: ${error}`);
		};
		reader.readAsText(file);
	};

	// Drag and Drop Handlers for Textarea
	const handleDragOver = (event: DragEvent) => {
		event.preventDefault(); // Necessary to allow drop
		isDraggingOver = true;
	};

	const handleDragLeave = (event: DragEvent) => {
		event.preventDefault();
		isDraggingOver = false;
	};

	const handleDrop = (event: DragEvent) => {
		event.preventDefault();
		isDraggingOver = false;

		if (event.dataTransfer?.files) {
			if (event.dataTransfer.files.length > 1) {
				toast.error('Please drop only one file.');
				return;
			}
			const file = event.dataTransfer.files[0];
			processWorkflowFile(file);
		}
	};

	onMount(async () => {
		if ($user?.role === 'admin') {
			const res = await getConfig(localStorage.token).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (res) {
				config = res;
				// Ensure nested comfyui structure exists
				if (!config.comfyui) {
					config.comfyui = {
						COMFYUI_BASE_URL: '',
						COMFYUI_API_KEY: '',
						COMFYUI_WORKFLOW: '',
						COMFYUI_WORKFLOW_NODES: []
					};
				}
				// Ensure properties exist and are correct type
				config.comfyui.COMFYUI_BASE_URL = config.comfyui.COMFYUI_BASE_URL ?? '';
				config.comfyui.COMFYUI_API_KEY = config.comfyui.COMFYUI_API_KEY ?? '';
				config.comfyui.COMFYUI_WORKFLOW = config.comfyui.COMFYUI_WORKFLOW ?? '';
				config.comfyui.COMFYUI_WORKFLOW_NODES = Array.isArray(config.comfyui.COMFYUI_WORKFLOW_NODES)
					? config.comfyui.COMFYUI_WORKFLOW_NODES
					: [];
			} else {
				// Handle case where config fetch failed - provide default structure
				config = {
					enabled: false,
					engine: 'openai',
					prompt_generation: false,
					openai: { OPENAI_API_BASE_URL: '', OPENAI_API_KEY: '' },
					automatic1111: {
						AUTOMATIC1111_BASE_URL: '',
						AUTOMATIC1111_API_AUTH: '',
						AUTOMATIC1111_SAMPLER: '',
						AUTOMATIC1111_SCHEDULER: '',
						AUTOMATIC1111_CFG_SCALE: ''
					},
					comfyui: {
						COMFYUI_BASE_URL: '',
						COMFYUI_API_KEY: '',
						COMFYUI_WORKFLOW: '',
						COMFYUI_WORKFLOW_NODES: []
					},
					gemini: { GEMINI_API_BASE_URL: '', GEMINI_API_KEY: '' }
				};
			}

			if (config.enabled) {
				getModels();
			}

			// Load saved node configurations
			let savedNodes = config.comfyui.COMFYUI_WORKFLOW_NODES;

			// Try to parse the stored workflow BUT DO NOT show toast on initial mount
			if (config.comfyui.COMFYUI_WORKFLOW && config.comfyui.COMFYUI_WORKFLOW.trim() !== '') {
				try {
					const parsedWorkflow = JSON.parse(config.comfyui.COMFYUI_WORKFLOW);
					// Pretty print for display
					config.comfyui.COMFYUI_WORKFLOW = JSON.stringify(parsedWorkflow, null, 2);
					// Parse workflow and reconcile with saved node configurations, NO TOAST on mount
					parseAndPopulateWorkflowNodes(parsedWorkflow, savedNodes, false); // Pass false for showToast
				} catch (e) {
					console.warn('Stored ComfyUI workflow is not valid JSON:', e);
					// Don't show toast on mount for invalid stored JSON either
					// Attempt to load saved nodes directly into the UI state
					workflowNodesConfig = savedNodes.map((n) => ({
						type: n.type ?? 'unknown',
						key: n.key ?? 'unknown',
						node_ids: Array.isArray(n.node_ids)
							? n.node_ids.join(',')
							: (n.node_ids?.toString() ?? ''),
						class_type: n.type?.split('::')[0] ?? 'Unknown'
					}));
				}
			} else {
				// No workflow stored, just load saved nodes configurations if any exist
				workflowNodesConfig = savedNodes.map((n) => ({
					type: n.type ?? 'unknown',
					key: n.key ?? 'unknown',
					node_ids: Array.isArray(n.node_ids)
						? n.node_ids.join(',')
						: (n.node_ids?.toString() ?? ''),
					class_type: n.type?.split('::')[0] ?? 'Unknown'
				}));
			}

			const imageConfigRes = await getImageGenerationConfig(localStorage.token).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (imageConfigRes) {
				imageGenerationConfig = imageConfigRes;
			} else {
				// Provide default image config if fetch fails
				imageGenerationConfig = { MODEL: '', IMAGE_SIZE: '1024x1024', IMAGE_STEPS: 30 };
			}
		}
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={saveHandler}
>
	<div class=" space-y-3 overflow-y-scroll scrollbar-hidden pr-2">
		{#if config && imageGenerationConfig}
			<div>
				<div class=" mb-1 text-sm font-medium">{$i18n.t('Image Settings')}</div>

				<div>
					<div class=" py-1 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Image Generation (Experimental)')}
						</div>

						<div class="px-1">
							<Switch
								bind:state={config.enabled}
								on:change={async (e) => {
									const enabled = e.detail;
									let proceed = true;

									if (enabled) {
										const engine = config.engine;
										if (
											engine === 'automatic1111' &&
											!config.automatic1111?.AUTOMATIC1111_BASE_URL
										) {
											toast.error($i18n.t('AUTOMATIC1111 Base URL is required.'));
											proceed = false;
										} else if (engine === 'comfyui' && !config.comfyui?.COMFYUI_BASE_URL) {
											toast.error($i18n.t('ComfyUI Base URL is required.'));
											proceed = false;
										} else if (engine === 'openai' && !config.openai?.OPENAI_API_KEY) {
											toast.error($i18n.t('OpenAI API Key is required.'));
											proceed = false;
										} else if (engine === 'gemini' && !config.gemini?.GEMINI_API_KEY) {
											toast.error($i18n.t('Gemini API Key is required.'));
											proceed = false;
										}
									}

									if (!proceed) {
										await new Promise((resolve) => setTimeout(resolve, 50));
										config.enabled = false;
										config = config;
									} else {
										await updateConfigHandler();
									}
								}}
							/>
						</div>
					</div>
				</div>

				{#if config.enabled}
					<div class=" py-1 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">{$i18n.t('Image Prompt Generation')}</div>
						<div class="px-1">
							<Switch bind:state={config.prompt_generation} />
						</div>
					</div>
				{/if}

				<div class=" py-1 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">{$i18n.t('Image Generation Engine')}</div>
					<div class="flex items-center relative">
						<select
							class=" dark:bg-gray-900 w-fit pr-8 cursor-pointer rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-right"
							bind:value={config.engine}
							placeholder={$i18n.t('Select Engine')}
							on:change={async () => {
								await updateConfigHandler();
							}}
						>
							<option value="openai">{$i18n.t('Default (Open AI)')}</option>
							<option value="comfyui">{$i18n.t('ComfyUI')}</option>
							<option value="automatic1111">{$i18n.t('Automatic1111')}</option>
							<option value="gemini">{$i18n.t('Gemini')}</option>
						</select>
					</div>
				</div>
			</div>
			<hr class=" border-gray-100 dark:border-gray-850" />

			<div class="flex flex-col gap-2">
				{#if (config?.engine ?? 'automatic1111') === 'automatic1111'}
					<!-- AUTOMATIC1111 Settings -->
					<div>
						<div class=" mb-2 text-sm font-medium">{$i18n.t('AUTOMATIC1111 Base URL')}</div>
						<div class="flex w-full">
							<div class="flex-1 mr-2">
								<input
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									placeholder={$i18n.t('Enter URL (e.g. http://127.0.0.1:7860/)')}
									bind:value={config.automatic1111.AUTOMATIC1111_BASE_URL}
								/>
							</div>
							<button
								class="px-2.5 bg-gray-50 hover:bg-gray-100 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition"
								type="button"
								on:click={async () => {
									await updateConfig(localStorage.token, config).catch((err) =>
										toast.error(`Failed to save URL: ${err}`)
									);
									const res = await verifyConfigUrl(localStorage.token).catch((error) => {
										toast.error(`${error}`);
										return null;
									});
									if (res) toast.success($i18n.t('Server connection verified'));
								}}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="w-4 h-4"
									><path
										fill-rule="evenodd"
										d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
										clip-rule="evenodd"
									/></svg
								>
							</button>
						</div>
						<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
							{$i18n.t('Include `--api` flag when running stable-diffusion-webui')}
							<a
								class=" text-gray-300 font-medium"
								href="https://github.com/AUTOMATIC1111/stable-diffusion-webui/discussions/3734"
								target="_blank">{$i18n.t('(e.g. `sh webui.sh --api`)')}</a
							>
						</div>
					</div>
					<div>
						<div class=" mb-2 text-sm font-medium">{$i18n.t('AUTOMATIC1111 Api Auth String')}</div>
						<SensitiveInput
							placeholder={$i18n.t('Enter api auth string (e.g. username:password)')}
							bind:value={config.automatic1111.AUTOMATIC1111_API_AUTH}
							required={false}
						/>
						<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
							{$i18n.t('Include `--api-auth` flag when running stable-diffusion-webui')}
							<a
								class=" text-gray-300 font-medium"
								href="https://github.com/AUTOMATIC1111/stable-diffusion-webui/discussions/13993"
								target="_blank"
								>{$i18n
									.t('(e.g. `sh webui.sh --api --api-auth username_password`)')
									.replace('_', ':')}
							</a>
						</div>
					</div>
					<div>
						<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Set Sampler')}</div>
						<div class="flex w-full">
							<div class="flex-1 mr-2">
								<Tooltip content={$i18n.t('Enter Sampler (e.g. Euler a)')} placement="top-start">
									<input
										list="sampler-list"
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
										placeholder={$i18n.t('Enter Sampler (e.g. Euler a)')}
										bind:value={config.automatic1111.AUTOMATIC1111_SAMPLER}
									/>
									<datalist id="sampler-list"
										>{#each samplers ?? [] as sampler}<option value={sampler}>{sampler}</option
											>{/each}</datalist
									>
								</Tooltip>
							</div>
						</div>
					</div>
					<div>
						<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Set Scheduler')}</div>
						<div class="flex w-full">
							<div class="flex-1 mr-2">
								<Tooltip content={$i18n.t('Enter Scheduler (e.g. Karras)')} placement="top-start">
									<input
										list="scheduler-list"
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
										placeholder={$i18n.t('Enter Scheduler (e.g. Karras)')}
										bind:value={config.automatic1111.AUTOMATIC1111_SCHEDULER}
									/>
									<datalist id="scheduler-list"
										>{#each schedulers ?? [] as scheduler}<option value={scheduler}
												>{scheduler}</option
											>{/each}</datalist
									>
								</Tooltip>
							</div>
						</div>
					</div>
					<div>
						<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Set CFG Scale')}</div>
						<div class="flex w-full">
							<div class="flex-1 mr-2">
								<Tooltip content={$i18n.t('Enter CFG Scale (e.g. 7.0)')} placement="top-start">
									<input
										type="number"
										step="0.1"
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
										placeholder={$i18n.t('Enter CFG Scale (e.g. 7.0)')}
										bind:value={config.automatic1111.AUTOMATIC1111_CFG_SCALE}
									/>
								</Tooltip>
							</div>
						</div>
					</div>
				{:else if config?.engine === 'comfyui'}
					<!-- ComfyUI Settings -->
					<div class="">
						<div class=" mb-2 text-sm font-medium">{$i18n.t('ComfyUI Base URL')}</div>
						<div class="flex w-full">
							<div class="flex-1 mr-2">
								<input
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									placeholder={$i18n.t('Enter URL (e.g. http://127.0.0.1:8188/)')}
									bind:value={config.comfyui.COMFYUI_BASE_URL}
								/>
							</div>
							<button
								class="px-2.5 bg-gray-50 hover:bg-gray-100 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition"
								type="button"
								on:click={async () => {
									await updateConfig(localStorage.token, config).catch((err) =>
										toast.error(`Failed to save URL: ${err}`)
									);
									const res = await verifyConfigUrl(localStorage.token).catch((error) => {
										toast.error(`${error}`);
										return null;
									});
									if (res) toast.success($i18n.t('Server connection verified'));
								}}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="w-4 h-4"
									><path
										fill-rule="evenodd"
										d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
										clip-rule="evenodd"
									/></svg
								>
							</button>
						</div>
					</div>

					<div class="">
						<div class=" mb-2 text-sm font-medium">{$i18n.t('ComfyUI API Key')}</div>
						<div class="flex w-full">
							<div class="flex-1 mr-2">
								<SensitiveInput
									placeholder={$i18n.t('Optional API Key')}
									bind:value={config.comfyui.COMFYUI_API_KEY}
									required={false}
								/>
							</div>
						</div>
					</div>

					<div class="">
						<div class=" mb-2 text-sm font-medium">{$i18n.t('ComfyUI Workflow (API Format)')}</div>

						{#if config.comfyui.COMFYUI_WORKFLOW !== undefined}
							<textarea
								class="w-full rounded-lg mb-1 py-2 px-4 text-xs bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden disabled:text-gray-600 resize-none font-mono transition-colors {isDraggingOver
									? 'border-2 border-dashed border-blue-500 dark:border-blue-400 bg-blue-50 dark:bg-gray-800'
									: 'border border-transparent'}"
								rows="10"
								bind:value={config.comfyui.COMFYUI_WORKFLOW}
								placeholder={$i18n.t(
									'Upload, drag & drop, or paste your ComfyUI API format workflow JSON here.'
								)}
								on:blur={handleWorkflowBlur}
								on:dragover={handleDragOver}
								on:dragleave={handleDragLeave}
								on:drop={handleDrop}
							/>
						{/if}

						<div class="flex w-full">
							<div class="flex-1">
								<input
									id="upload-comfyui-workflow-input"
									hidden
									type="file"
									accept=".json,application/json"
									on:change={(e) => {
										const target = e.target;
										if (!(target instanceof HTMLInputElement) || !target.files) {
											console.error('Event target is not an HTMLInputElement or has no files');
											if (target instanceof HTMLInputElement) {
												target.value = null;
											}
											return;
										}
										const file = target.files[0];
										processWorkflowFile(file);
										// Reset the input value so the same file can be uploaded again
										target.value = null;
									}}
								/>
								<button
									class="w-full text-sm font-medium py-2 bg-transparent hover:bg-gray-100 border border-dashed dark:border-gray-850 dark:hover:bg-gray-850 text-center rounded-xl"
									type="button"
									on:click={() => {
										document.getElementById('upload-comfyui-workflow-input')?.click();
									}}
								>
									{$i18n.t('Click here to upload workflow_api.json')}
								</button>
							</div>
						</div>
						<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
							{$i18n.t(
								'Make sure to export your workflow as API format from ComfyUI ("Save (API format)"). Uploading or dropping will discover primitive inputs (text, numbers, etc.) and populate the list below.'
							)}
						</div>
					</div>

					<!-- Dynamic Workflow Nodes Configuration -->
					{#if workflowNodesConfig.length > 0}
						<div class="">
							<div class=" mb-2 text-sm font-medium">{$i18n.t('ComfyUI Workflow Node Inputs')}</div>
							<div class="text-xs flex flex-col gap-1.5">
								{#each workflowNodesConfig as node, i (node.type)}
									<div class="flex w-full items-center border dark:border-gray-850 rounded-lg">
										<!-- Node Class Type (Readonly) -->
										<div class="shrink-0">
											<Tooltip content={`Node Type: ${node.class_type}`}>
												<div
													class="font-mono text-[10px] px-2 py-1 w-32 text-center truncate bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded-l-lg"
												>
													{node.class_type}
												</div>
											</Tooltip>
										</div>
										<!-- Input Key (Readonly) -->
										<div class="shrink-0">
											<Tooltip content={`Input Key: ${node.key}`}>
												<div
													class="font-mono text-xs font-medium px-3 py-1 w-24 text-center truncate border-x dark:border-gray-800"
												>
													{node.key}
												</div>
											</Tooltip>
										</div>
										<!-- Node IDs (Editable) -->
										<div class="w-full">
											<Tooltip
												content="Comma separated Node IDs (e.g. 6 or 6,7). Auto-filled on upload/paste. Edit to override which node(s) this input applies to."
												placement="top-start"
											>
												<input
													class="w-full py-1 px-4 rounded-r-lg text-xs bg-transparent outline-hidden"
													placeholder="Node IDs (e.g. 6 or 6,10)"
													bind:value={workflowNodesConfig[i].node_ids}
													pattern="^(\d+)?(,\s*\d+)*$"
													title="Enter comma-separated numbers (e.g., 6 or 6, 10)"
												/>
											</Tooltip>
										</div>
									</div>
								{/each}
							</div>
							<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
								{$i18n.t(
									'Discovered primitive inputs from the workflow. Verify or edit the Node ID(s) for each input you want the backend to control.'
								)}
								{$i18n.t(
									'The backend will use the Type (Node Type::Input Key) and Key to map incoming generation parameters (like prompt, seed, steps, model, etc.) to these nodes.'
								)}
							</div>
						</div>
					{:else if config.comfyui.COMFYUI_WORKFLOW && config.comfyui.COMFYUI_WORKFLOW.trim() !== ''}
						<div
							class="mt-2 text-xs text-center text-gray-400 dark:text-gray-500 p-2 border dark:border-gray-850 rounded-lg"
						>
							{$i18n.t(
								'No configurable primitive inputs (text, numbers, booleans) were found in the provided workflow JSON.'
							)}
						</div>
					{/if}
				{:else if config?.engine === 'openai'}
					<!-- OpenAI Settings -->
					<div>
						<div class=" mb-1.5 text-sm font-medium">{$i18n.t('OpenAI API Config')}</div>
						<div class="flex gap-2 mb-1">
							<input
								class="flex-1 w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
								placeholder={$i18n.t('API Base URL (Default: https://api.openai.com/v1)')}
								bind:value={config.openai.OPENAI_API_BASE_URL}
							/>
							<SensitiveInput
								placeholder={$i18n.t('API Key')}
								bind:value={config.openai.OPENAI_API_KEY}
							/>
						</div>
					</div>
				{:else if config?.engine === 'gemini'}
					<!-- Gemini Settings -->
					<div>
						<div class=" mb-1.5 text-sm font-medium">{$i18n.t('Gemini API Config')}</div>
						<div class="flex gap-2 mb-1">
							<input
								class="flex-1 w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
								placeholder={$i18n.t(
									'API Base URL (Default: https://generativelanguage.googleapis.com/v1beta)'
								)}
								bind:value={config.gemini.GEMINI_API_BASE_URL}
							/>
							<SensitiveInput
								placeholder={$i18n.t('API Key')}
								bind:value={config.gemini.GEMINI_API_KEY}
							/>
						</div>
					</div>
				{/if}
			</div>

			<!-- Common Image Generation Settings (Model, Size, Steps) -->
			{#if config?.enabled}
				<hr class=" border-gray-100 dark:border-gray-850" />
				<div>
					<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Set Default Model')}</div>
					<div class="flex w-full">
						<div class="flex-1 mr-2">
							<Tooltip content={$i18n.t('Enter Model ID or Name')} placement="top-start">
								<input
									list="model-list"
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									bind:value={imageGenerationConfig.MODEL}
									placeholder="Enter a model name/ID"
									required
								/>
								<datalist id="model-list">
									{#each models ?? [] as model}
										<option value={model.id}>{model.name}</option>
									{/each}
								</datalist>
							</Tooltip>
						</div>
					</div>
				</div>
				<div>
					<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Set Image Size')}</div>
					<div class="flex w-full">
						<div class="flex-1 mr-2">
							<Tooltip content={$i18n.t('Enter Image Size (e.g. 1024x1024)')} placement="top-start">
								<input
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									placeholder={$i18n.t('Enter Image Size (e.g. 1024x1024)')}
									bind:value={imageGenerationConfig.IMAGE_SIZE}
									pattern="^\d+x\d+$"
									title="Format must be widthxheight (e.g., 1024x1024)"
									required
								/>
							</Tooltip>
						</div>
					</div>
				</div>
				<div>
					<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Set Steps')}</div>
					<div class="flex w-full">
						<div class="flex-1 mr-2">
							<Tooltip content={$i18n.t('Enter Number of Steps (e.g. 30)')} placement="top-start">
								<input
									type="number"
									min="1"
									max="150"
									step="1"
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									placeholder={$i18n.t('Enter Number of Steps (e.g. 30)')}
									bind:value={imageGenerationConfig.IMAGE_STEPS}
									required
								/>
							</Tooltip>
						</div>
					</div>
				</div>
			{/if}
		{:else}
			<div class="text-center p-4">{$i18n.t('Loading image settings...')}</div>
		{/if}
	</div>

	<!-- Save Button -->
	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center {loading
				? ' cursor-not-allowed opacity-50'
				: ''}"
			type="submit"
			disabled={loading || !config || !imageGenerationConfig}
		>
			{$i18n.t('Save')}
			{#if loading}
				<div class="ml-2 self-center">
					<svg
						class=" w-4 h-4 animate-spin"
						viewBox="0 0 24 24"
						fill="currentColor"
						xmlns="http://www.w3.org/2000/svg"
						><path
							d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z"
							opacity=".25"
						/><path
							d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"
							fill="currentColor"
						/></svg
					>
				</div>
			{/if}
		</button>
	</div>
</form>
