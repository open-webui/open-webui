<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext<any>('i18n');

	import { verifyImageConnection } from '$lib/apis/images';

	import Modal from '$lib/components/common/Modal.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Minus from '$lib/components/icons/Minus.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import AccessButton from '$lib/components/common/AccessButton.svelte';
	import AccessControlModal from '$lib/components/workspace/common/AccessControlModal.svelte';
	import ComfyUIWorkflow from './ComfyUIWorkflow.svelte';
	import {
		getSupportedImageCapabilities,
		type ImageCapabilities,
		type ImageCapability
	} from '$lib/utils/images';

	type ConnectionType = 'openai' | 'gemini' | 'comfyui' | 'automatic1111';
	type WorkflowNode = { type: string; key: string; node_ids: string };

	export let onSubmit: Function = () => {};
	export let onDelete: Function = () => {};

	export let show = false;
	export let edit = false;

	export let connection: any = null;

	const GENERATION_WORKFLOW_NODES: WorkflowNode[] = [
		{ type: 'prompt', key: 'text', node_ids: '' },
		{ type: 'model', key: 'ckpt_name', node_ids: '' },
		{ type: 'width', key: 'width', node_ids: '' },
		{ type: 'height', key: 'height', node_ids: '' },
		{ type: 'steps', key: 'steps', node_ids: '' },
		{ type: 'seed', key: 'seed', node_ids: '' }
	];
	const EDIT_WORKFLOW_NODES: WorkflowNode[] = [
		{ type: 'image', key: 'image', node_ids: '' },
		{ type: 'prompt', key: 'prompt', node_ids: '' },
		{ type: 'model', key: 'unet_name', node_ids: '' },
		{ type: 'width', key: 'width', node_ids: '' },
		{ type: 'height', key: 'height', node_ids: '' }
	];

	let connectionType: ConnectionType = 'openai';
	let name = '';
	let url = '';
	let key = '';
	let auth_type = 'bearer';
	let enable = true;
	let capabilities: ImageCapabilities = { image_generation: true, image_edit: true };
	let accessGrants: any[] = [];

	let modelId = '';
	let modelIds: string[] = [];
	let availableModelIds: string[] = [];

	let size = '';
	let editSize = '';
	let steps = '';
	let apiVersion = '';
	let params = '';
	let headers = '';
	let endpointMethod = '';
	let workflow = '';
	let nodes: WorkflowNode[] = [];
	let editWorkflow = '';
	let editNodes: WorkflowNode[] = [];

	let loading = false;
	let showDeleteConfirmDialog = false;
	let showAccessControlModal = false;
	let showAdvanced = false;

	const inputClass =
		'bg-transparent outline-hidden placeholder:text-base-300 dark:placeholder:text-base-700';
	const selectClass =
		'bg-transparent pr-5 outline-hidden placeholder:text-base-300 dark:placeholder:text-base-700';

	$: typeLabel = {
		openai: $i18n.t('OpenAI compatible'),
		gemini: $i18n.t('Gemini'),
		comfyui: $i18n.t('ComfyUI'),
		automatic1111: $i18n.t('AUTOMATIC1111')
	}[connectionType];

	// Only OpenAI compatible connections authenticate the way chat model connections do.
	$: if (connectionType !== 'openai' && !['none', 'bearer'].includes(auth_type)) {
		auth_type = 'bearer';
	}

	$: supportedCapabilities = getSupportedImageCapabilities(connectionType, {
		workflow,
		edit_workflow: editWorkflow
	});

	$: capabilityOptions = [
		{ value: 'image_generation', label: $i18n.t('Generate') },
		{ value: 'image_edit', label: $i18n.t('Edit') }
	] as { value: ImageCapability; label: string }[];

	const unsupportedCapabilityHint = (capability: ImageCapability) => {
		if (connectionType === 'automatic1111') return $i18n.t('AUTOMATIC1111 cannot edit images');
		return capability === 'image_generation'
			? $i18n.t('Upload a generation workflow to generate images')
			: $i18n.t('Upload an edit workflow to edit images');
	};

	const mapNodes = (defaults: WorkflowNode[], saved: any[] = []) =>
		defaults.map((node) => {
			const match = saved.find((n) => n.type === node.type) ?? node;
			return {
				type: match.type,
				key: match.key,
				node_ids: Array.isArray(match.node_ids) ? match.node_ids.join(',') : (match.node_ids ?? '')
			};
		});

	const toNodeConfig = (workflowNodes: WorkflowNode[]) =>
		workflowNodes.map((node) => ({
			...node,
			node_ids: node.node_ids
				.split(',')
				.map((id) => id.trim())
				.filter(Boolean)
		}));

	const formatJSON = (value: any) => {
		if (!value) return '';
		if (typeof value === 'object') {
			return Object.keys(value).length ? JSON.stringify(value, null, 2) : '';
		}
		try {
			return JSON.stringify(JSON.parse(value), null, 2);
		} catch {
			return value;
		}
	};

	const isJSONObject = (value: string) => {
		try {
			const parsed = JSON.parse(value);
			return parsed !== null && typeof parsed === 'object' && !Array.isArray(parsed);
		} catch {
			return false;
		}
	};

	const validate = () => {
		if (!url) {
			toast.error($i18n.t('URL is required'));
			return false;
		}
		if (headers.trim() && !isJSONObject(headers)) {
			showAdvanced = true;
			toast.error($i18n.t('Headers must be a valid JSON object'));
			return false;
		}
		if (params.trim() && !isJSONObject(params)) {
			showAdvanced = true;
			toast.error($i18n.t('Invalid JSON format for Parameters'));
			return false;
		}
		if (workflow.trim() && !isJSONObject(workflow)) {
			toast.error($i18n.t('Invalid JSON format for ComfyUI Workflow.'));
			return false;
		}
		if (editWorkflow.trim() && !isJSONObject(editWorkflow)) {
			toast.error($i18n.t('Invalid JSON format for ComfyUI Edit Workflow.'));
			return false;
		}
		if (steps !== '' && !(Number.isInteger(Number(steps)) && Number(steps) >= 0)) {
			showAdvanced = true;
			toast.error($i18n.t('Enter Number of Steps (e.g. 50)'));
			return false;
		}
		return true;
	};

	const buildConnection = () => ({
		...(connection?.id ? { id: connection.id } : {}),
		name: name.trim() || typeLabel,
		type: connectionType,
		url,
		key: connectionType !== 'openai' && auth_type === 'none' ? '' : key,
		config: {
			enable,
			capabilities,
			model_ids: modelIds,
			access_grants: accessGrants,
			size: size.trim(),
			edit_size: editSize.trim(),
			steps: steps === '' ? null : Number(steps),
			api_version: apiVersion.trim(),
			auth_type,
			headers: connectionType === 'openai' && headers.trim() ? JSON.parse(headers) : {},
			params: params.trim() ? JSON.parse(params) : {},
			endpoint_method: endpointMethod,
			workflow: workflow.trim(),
			nodes: toNodeConfig(nodes),
			edit_workflow: editWorkflow.trim(),
			edit_nodes: toNodeConfig(editNodes)
		}
	});

	const verifyHandler = async () => {
		availableModelIds = [];
		// remove trailing slash from url
		url = url.replace(/\/$/, '');

		if (!validate()) return;

		const res = await verifyImageConnection(localStorage.token, buildConnection()).catch(
			(error) => {
				toast.error(`${error}`);
			}
		);

		if (show && Array.isArray(res)) {
			// LiteLLM labels its image models; suggest only those when it does.
			const imageModels = res.some((model) => model.image !== undefined)
				? res.filter((model) => model.image)
				: res;
			availableModelIds = [...new Set<string>(imageModels.map((model) => model.id))];
		}

		if (res) {
			toast.success($i18n.t('Server connection verified'));
		}
	};

	const addModelHandler = () => {
		const newModelId = modelId.trim();

		if (!newModelId) {
			return;
		}

		if (modelIds.includes(newModelId)) {
			toast.error($i18n.t('Model ID is already added'));
			return;
		}

		modelIds = [...modelIds, newModelId];
		modelId = '';
	};

	const submitHandler = async () => {
		loading = true;

		// remove trailing slash from url
		url = url.replace(/\/$/, '');

		if (!validate()) {
			loading = false;
			return;
		}

		await onSubmit(buildConnection());

		loading = false;
		show = false;
	};

	const init = () => {
		const config = connection?.config ?? {};
		availableModelIds = [];
		showAdvanced = false;
		modelId = '';

		connectionType = connection?.type ?? 'openai';
		name = connection?.name ?? '';
		url = connection?.url ?? '';
		key = connection?.key ?? '';
		auth_type = config.auth_type ?? (connection && !connection.key ? 'none' : 'bearer');
		enable = config.enable ?? true;
		capabilities = {
			image_generation: config.capabilities?.image_generation ?? true,
			image_edit: config.capabilities?.image_edit ?? true
		};
		accessGrants = structuredClone(config.access_grants ?? []);
		modelIds = [...new Set<string>(config.model_ids ?? [])];

		size = config.size ?? '';
		editSize = config.edit_size ?? '';
		steps = config.steps === null || config.steps === undefined ? '' : `${config.steps}`;
		apiVersion = config.api_version ?? '';
		params = formatJSON(config.params);
		headers = formatJSON(config.headers);
		endpointMethod = config.endpoint_method ?? '';
		workflow = formatJSON(config.workflow);
		nodes = mapNodes(GENERATION_WORKFLOW_NODES, config.nodes);
		editWorkflow = formatJSON(config.edit_workflow);
		editNodes = mapNodes(EDIT_WORKFLOW_NODES, config.edit_nodes);
	};

	$: if (show) {
		init();
	}

	onMount(() => {
		init();
	});
</script>

<Modal
	ariaLabel={edit ? $i18n.t('Edit Connection') : $i18n.t('Add Connection')}
	size="sm"
	bind:show
>
	<div>
		<div class=" flex justify-between dark:text-base-100 px-4 pt-3 pb-1.5">
			<h1 class="text-sm font-medium self-center">
				{#if edit}
					{$i18n.t('Edit Connection')}
				{:else}
					{$i18n.t('Add Connection')}
				{/if}
			</h1>
			<button
				class="self-center"
				aria-label={$i18n.t('Close modal')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-4'} />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-4 pb-4 md:space-x-4 dark:text-base-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit={(e) => {
						e.preventDefault();
						submitHandler();
					}}
				>
					<div>
						<div class="flex flex-row justify-between items-center w-full">
							<label for="image-connection-type-select" class="text-xs text-base-500"
								>{$i18n.t('Connection Type')}</label
							>

							<div>
								<select
									id="image-connection-type-select"
									bind:value={connectionType}
									on:change={() => {
										availableModelIds = [];
									}}
									class="text-xs text-base-700 dark:text-base-300 bg-transparent pr-5 outline-hidden"
								>
									<option value="openai">{$i18n.t('OpenAI compatible')}</option>
									<option value="gemini">{$i18n.t('Gemini')}</option>
									<option value="comfyui">{$i18n.t('ComfyUI')}</option>
									<option value="automatic1111">{$i18n.t('AUTOMATIC1111')}</option>
								</select>
							</div>
						</div>

						<div class="flex flex-row justify-between items-center w-full mt-1">
							<div class="text-xs text-base-500">{$i18n.t('Capabilities')}</div>

							<div class="flex items-center gap-1.5 text-xs">
								{#each capabilityOptions as option, optionIdx (option.value)}
									{#if optionIdx > 0}
										<span class="text-base-300 dark:text-base-700" aria-hidden="true">·</span>
									{/if}

									<Tooltip
										content={supportedCapabilities[option.value]
											? ''
											: unsupportedCapabilityHint(option.value)}
									>
										<button
											type="button"
											aria-pressed={supportedCapabilities[option.value] &&
												capabilities[option.value]}
											disabled={!supportedCapabilities[option.value]}
											class="transition disabled:cursor-not-allowed {supportedCapabilities[
												option.value
											] && capabilities[option.value]
												? 'text-base-700 dark:text-base-300'
												: 'text-base-400 dark:text-base-600'}"
											on:click={() => {
												capabilities = {
													...capabilities,
													[option.value]: !capabilities[option.value]
												};
											}}
										>
											{option.label}
										</button>
									</Tooltip>
								{/each}
							</div>
						</div>

						<div class="flex gap-2 mt-1.5">
							<div class="flex flex-col w-full">
								<label for="image-connection-name" class="mb-0.5 text-xs text-base-500"
									>{$i18n.t('Name')}</label
								>

								<div class="flex-1">
									<input
										id="image-connection-name"
										class={`w-full text-sm ${inputClass}`}
										type="text"
										bind:value={name}
										placeholder={$i18n.t('Enter name')}
										autocomplete="off"
									/>
								</div>
							</div>
						</div>

						<div class="flex gap-2 mt-2">
							<div class="flex flex-col w-full">
								<label for="image-connection-url" class="mb-0.5 text-xs text-base-500"
									>{$i18n.t('URL')}</label
								>

								<div class="flex-1">
									<input
										id="image-connection-url"
										class={`w-full text-sm ${inputClass}`}
										type="text"
										bind:value={url}
										placeholder={connectionType === 'openai' || connectionType === 'gemini'
											? $i18n.t('API Base URL')
											: $i18n.t('Enter URL (e.g. http://127.0.0.1:7860/)')}
										autocomplete="off"
										list={connectionType === 'openai'
											? 'image-connection-openai-urls'
											: connectionType === 'gemini'
												? 'image-connection-gemini-urls'
												: undefined}
										required
									/>

									<datalist id="image-connection-openai-urls">
										<option value="https://api.openai.com/v1" />
									</datalist>
									<datalist id="image-connection-gemini-urls">
										<option value="https://generativelanguage.googleapis.com/v1beta" />
									</datalist>
								</div>
							</div>

							<Tooltip content={$i18n.t('Verify Connection')} className="self-end -mb-1">
								<button
									class="self-center p-1 bg-transparent hover:bg-base-100 dark:hover:bg-base-850 rounded-lg transition"
									on:click={() => {
										verifyHandler();
									}}
									type="button"
									aria-label={$i18n.t('Verify Connection')}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 20 20"
										fill="currentColor"
										aria-hidden="true"
										class="w-4 h-4"
									>
										<path
											fill-rule="evenodd"
											d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
											clip-rule="evenodd"
										/>
									</svg>
								</button>
							</Tooltip>

							<div class="flex flex-col shrink-0 self-end">
								<label class="sr-only" for="toggle-image-connection"
									>{$i18n.t('Toggle whether current connection is active.')}</label
								>
								<Tooltip content={enable ? $i18n.t('Enabled') : $i18n.t('Disabled')}>
									<Switch id="toggle-image-connection" bind:state={enable} />
								</Tooltip>
							</div>
						</div>

						<div class="flex gap-2 mt-2">
							<div class="flex flex-col w-full">
								<label for="image-connection-auth" class="text-xs text-base-500"
									>{$i18n.t('Auth')}</label
								>

								<div class="flex gap-2">
									<div class="flex-shrink-0 self-start">
										<select
											id="image-connection-auth"
											class={`w-full text-sm ${selectClass}`}
											bind:value={auth_type}
										>
											<option value="none">{$i18n.t('None')}</option>
											<option value="bearer">
												{connectionType === 'automatic1111' ? $i18n.t('Basic') : $i18n.t('Bearer')}
											</option>

											{#if connectionType === 'openai'}
												<option value="session">{$i18n.t('Session')}</option>
												<option value="system_oauth">{$i18n.t('OAuth')}</option>
												<option value="microsoft_entra_id">{$i18n.t('Entra ID')}</option>
											{/if}
										</select>
									</div>

									<div class="flex flex-1 items-center">
										{#if auth_type === 'bearer'}
											<SensitiveInput
												bind:value={key}
												placeholder={connectionType === 'automatic1111'
													? $i18n.t('Enter api auth string (e.g. username:password)')
													: $i18n.t('API Key')}
												required={false}
											/>
										{:else if auth_type === 'none'}
											<div class={`text-xs self-center translate-y-[1px] text-base-500`}>
												{$i18n.t('No authentication')}
											</div>
										{:else if auth_type === 'session'}
											<div class={`text-xs self-center translate-y-[1px] text-base-500`}>
												{$i18n.t('Forwards system user session credentials to authenticate')}
											</div>
										{:else if auth_type === 'system_oauth'}
											<div class={`text-xs self-center translate-y-[1px] text-base-500`}>
												{$i18n.t('Forwards system user OAuth access token to authenticate')}
											</div>
										{:else if auth_type === 'microsoft_entra_id'}
											<div class={`text-xs self-center translate-y-[1px] text-base-500`}>
												{$i18n.t('Uses DefaultAzureCredential to authenticate')}
											</div>
										{/if}
									</div>
								</div>
							</div>
						</div>

						<div class="flex flex-col w-full mt-2">
							<div class="mb-1 flex justify-between">
								<div class="mb-0.5 text-xs text-base-500">
									{$i18n.t('Model IDs')}
								</div>
							</div>

							{#if modelIds.length > 0}
								<ul class="flex flex-col">
									{#each modelIds as modelId, modelIdx}
										<li class=" flex gap-2 w-full justify-between items-center">
											<div class=" text-sm flex-1 py-1 rounded-lg">
												{modelId}
											</div>
											<div class="shrink-0">
												<button
													aria-label={$i18n.t(`Remove {{MODELID}} from list.`, {
														MODELID: modelId
													})}
													type="button"
													on:click={() => {
														modelIds = modelIds.filter((_, idx) => idx !== modelIdx);
													}}
												>
													<Minus strokeWidth="2" className="size-3.5" />
												</button>
											</div>
										</li>
									{/each}
								</ul>

								{#if connectionType === 'automatic1111'}
									<div class="text-xs text-base-500 pt-1">
										{$i18n.t(
											'Switching between these models changes the loaded checkpoint for everyone using this server.'
										)}
									</div>
								{/if}
							{:else}
								<div class={`text-base-500 text-xs text-center py-2 px-10`}>
									{#if connectionType === 'openai'}
										{$i18n.t(
											'Leave empty to include all image models from "{{url}}/models" endpoint, or {{model}} if it does not mark which models make images',
											{ url, model: 'gpt-image-2' }
										)}
									{:else if connectionType === 'gemini'}
										{$i18n.t('Leave empty to use {{model}}', { model: 'imagen-3.0-generate-002' })}
									{:else if connectionType === 'comfyui'}
										{$i18n.t('Leave empty to use the model set in the workflow')}
									{:else}
										{$i18n.t('Leave empty to use the checkpoint loaded in AUTOMATIC1111')}
									{/if}
								</div>
							{/if}
						</div>

						<div class="flex items-center">
							<label class="sr-only" for="add-image-model-id-input"
								>{$i18n.t('Add a model ID')}</label
							>
							<input
								class={`w-full text-sm ${inputClass} ${modelId ? '' : 'text-base-500'}`}
								bind:value={modelId}
								id="add-image-model-id-input"
								placeholder={$i18n.t('Add a model ID')}
								list={availableModelIds.length ? 'image-model-id-suggestions' : undefined}
								on:keydown={(event) => {
									if (event.key === 'Enter') {
										event.preventDefault();
										addModelHandler();
									}
								}}
							/>
							{#if availableModelIds.length}
								<datalist id="image-model-id-suggestions">
									{#each availableModelIds.filter((id) => !modelIds.includes(id)) as id}
										<option value={id}></option>
									{/each}
								</datalist>
							{/if}

							<div>
								<button
									type="button"
									aria-label={$i18n.t('Add')}
									on:click={() => {
										addModelHandler();
									}}
								>
									<Plus className="size-3.5" strokeWidth="2" />
								</button>
							</div>
						</div>

						{#if connectionType === 'comfyui'}
							<ComfyUIWorkflow
								id="image-connection-generation-workflow"
								label={$i18n.t('Generation Workflow')}
								description={$i18n.t(
									'Upload a workflow.json file exported as API format from ComfyUI.'
								)}
								bind:workflow
								bind:nodes
								requiredTypes={['prompt']}
							/>

							<ComfyUIWorkflow
								id="image-connection-edit-workflow"
								label={$i18n.t('Edit Workflow')}
								description={$i18n.t('Leave empty if this server does not edit images.')}
								bind:workflow={editWorkflow}
								bind:nodes={editNodes}
								requiredTypes={['prompt', 'image']}
							/>
						{/if}

						<div class="flex items-center justify-between">
							<button
								type="button"
								class="flex items-center gap-1 text-xs text-base-500 dark:text-base-400 hover:text-base-700 dark:hover:text-base-200 transition mt-2"
								on:click={() => (showAdvanced = !showAdvanced)}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="w-3 h-3 transition-transform {showAdvanced ? 'rotate-90' : ''}"
								>
									<path
										fill-rule="evenodd"
										d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
										clip-rule="evenodd"
									/>
								</svg>
								{$i18n.t('Advanced')}
							</button>

							<AccessButton
								className="mt-2"
								on:click={() => {
									showAccessControlModal = true;
								}}
								label={$i18n.t('Access Control')}
							/>
						</div>

						{#if showAdvanced}
							<div class="flex gap-2 mt-2">
								<div class="flex flex-col w-full">
									<label for="image-connection-size" class="mb-0.5 text-xs text-base-500"
										>{$i18n.t('Image Size')}</label
									>
									<input
										id="image-connection-size"
										class={`w-full text-sm ${inputClass}`}
										type="text"
										bind:value={size}
										placeholder={$i18n.t('Enter Image Size (e.g. 512x512)')}
										autocomplete="off"
									/>
								</div>

								{#if connectionType !== 'automatic1111'}
									<div class="flex flex-col w-full">
										<label for="image-connection-edit-size" class="mb-0.5 text-xs text-base-500"
											>{$i18n.t('Edit Image Size')}</label
										>
										<input
											id="image-connection-edit-size"
											class={`w-full text-sm ${inputClass}`}
											type="text"
											bind:value={editSize}
											placeholder={$i18n.t('Enter Image Size (e.g. 512x512)')}
											autocomplete="off"
										/>
									</div>
								{/if}
							</div>

							{#if connectionType === 'comfyui' || connectionType === 'automatic1111'}
								<div class="flex gap-2 mt-2">
									<div class="flex flex-col w-full">
										<label for="image-connection-steps" class="mb-0.5 text-xs text-base-500"
											>{$i18n.t('Steps')}</label
										>
										<input
											id="image-connection-steps"
											class={`w-full text-sm ${inputClass}`}
											type="text"
											bind:value={steps}
											placeholder={$i18n.t('Enter Number of Steps (e.g. 50)')}
											autocomplete="off"
										/>
									</div>
								</div>
							{/if}

							{#if connectionType === 'openai'}
								<div class="flex gap-2 mt-2">
									<div class="flex flex-col w-full">
										<label for="image-connection-api-version" class="mb-0.5 text-xs text-base-500"
											>{$i18n.t('API Version')}</label
										>
										<input
											id="image-connection-api-version"
											class={`w-full text-sm ${inputClass}`}
											type="text"
											bind:value={apiVersion}
											placeholder={$i18n.t('API Version')}
											autocomplete="off"
										/>
									</div>
								</div>
							{/if}

							{#if connectionType === 'gemini'}
								<div class="flex flex-row justify-between items-center w-full mt-2">
									<label for="image-connection-endpoint-method" class="mb-0.5 text-xs text-base-500"
										>{$i18n.t('Endpoint Method')}</label
									>

									<div>
										<select
											id="image-connection-endpoint-method"
											bind:value={endpointMethod}
											class="text-xs text-base-700 dark:text-base-300 bg-transparent pr-5 outline-hidden"
										>
											<option value="">predict</option>
											<option value="generateContent">generateContent</option>
										</select>
									</div>
								</div>
							{/if}

							{#if connectionType === 'openai'}
								<div class="flex gap-2 mt-2">
									<div class="flex flex-col w-full">
										<label for="image-connection-headers" class="mb-0.5 text-xs text-base-500"
											>{$i18n.t('Headers')}</label
										>

										<div class="flex-1">
											<Tooltip
												content={$i18n.t(
													'Enter additional headers in JSON format (e.g. {"X-Custom-Header": "value"}'
												)}
											>
												<Textarea
													id="image-connection-headers"
													className="w-full text-sm outline-hidden"
													bind:value={headers}
													maxSize={200}
													placeholder={$i18n.t('Enter additional headers in JSON format')}
													required={false}
													minSize={30}
												/>
											</Tooltip>
										</div>
									</div>
								</div>
							{/if}

							{#if connectionType === 'openai' || connectionType === 'automatic1111'}
								<div class="flex gap-2 mt-2">
									<div class="flex flex-col w-full">
										<label for="image-connection-params" class="mb-0.5 text-xs text-base-500"
											>{$i18n.t('Additional Parameters')}</label
										>

										<div class="flex-1">
											<Textarea
												id="image-connection-params"
												className="w-full text-sm outline-hidden"
												bind:value={params}
												maxSize={200}
												placeholder={$i18n.t('Enter additional parameters in JSON format')}
												required={false}
												minSize={30}
											/>
										</div>
									</div>
								</div>
							{/if}
						{/if}
					</div>

					<div class="flex justify-between items-center pt-3 text-xs">
						<div>
							{#if edit}
								<button
									class="px-1 py-1.5 text-xs text-base-500 hover:text-base-700 dark:text-base-400 dark:hover:text-base-200 hover:underline transition"
									type="button"
									on:click={() => {
										showDeleteConfirmDialog = true;
									}}
								>
									{$i18n.t('Delete')}
								</button>
							{/if}
						</div>

						<button
							class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-base-900 px-2.5 text-xs font-normal text-white transition hover:bg-black disabled:opacity-60 dark:bg-base-100 dark:text-base-900 dark:hover:bg-white disabled:cursor-not-allowed"
							type="submit"
							disabled={loading}
						>
							{$i18n.t('Save')}

							{#if loading}
								<span class="shrink-0">
									<Spinner className="size-3" />
								</span>
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>

<AccessControlModal bind:show={showAccessControlModal} bind:accessGrants />

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	message={$i18n.t(
		'Are you sure you want to delete this connection? This action cannot be undone.'
	)}
	confirmLabel={$i18n.t('Delete')}
	on:confirm={() => {
		onDelete();
		show = false;
	}}
/>
