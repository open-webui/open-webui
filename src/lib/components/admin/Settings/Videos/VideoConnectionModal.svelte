<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext<any>('i18n');

	import { verifyVideoConnection } from '$lib/apis/videos';

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

	export let onSubmit: Function = () => {};
	export let onDelete: Function = () => {};

	export let show = false;
	export let edit = false;

	export let connection: any = null;

	let name = '';
	let url = '';
	let key = '';
	let auth_type = 'bearer';
	let enable = true;
	let accessGrants: any[] = [];

	let modelId = '';
	let modelIds: string[] = [];
	let availableModelIds: string[] = [];

	let size = '';
	let seconds = '';
	let apiVersion = '';
	let params = '';
	let headers = '';

	let loading = false;
	let showDeleteConfirmDialog = false;
	let showAccessControlModal = false;
	let showAdvanced = false;

	const inputClass =
		'bg-transparent outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700';
	const selectClass =
		'bg-transparent pr-5 outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700';

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
		if (seconds !== '' && !(Number.isInteger(Number(seconds)) && Number(seconds) > 0)) {
			showAdvanced = true;
			toast.error($i18n.t('Enter Video Length in seconds (e.g. 8)'));
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
		return true;
	};

	const buildConnection = () => ({
		...(connection?.id ? { id: connection.id } : {}),
		name: name.trim() || $i18n.t('OpenAI compatible'),
		type: 'openai',
		url,
		key,
		config: {
			enable,
			model_ids: modelIds,
			access_grants: accessGrants,
			size: size.trim(),
			seconds: seconds === '' ? null : Number(seconds),
			api_version: apiVersion.trim(),
			auth_type,
			headers: headers.trim() ? JSON.parse(headers) : {},
			params: params.trim() ? JSON.parse(params) : {}
		}
	});

	const verifyHandler = async () => {
		availableModelIds = [];
		// remove trailing slash from url
		url = url.replace(/\/$/, '');

		if (!validate()) return;

		const res = await verifyVideoConnection(localStorage.token, buildConnection()).catch(
			(error) => {
				toast.error(`${error}`);
			}
		);

		if (show && Array.isArray(res)) {
			// LiteLLM labels its video models; suggest only those when it does.
			const videoModels = res.some((model) => model.video !== undefined)
				? res.filter((model) => model.video)
				: res;
			availableModelIds = [...new Set<string>(videoModels.map((model) => model.id))];
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

		name = connection?.name ?? '';
		url = connection?.url ?? '';
		key = connection?.key ?? '';
		auth_type = config.auth_type ?? (connection && !connection.key ? 'none' : 'bearer');
		enable = config.enable ?? true;
		accessGrants = structuredClone(config.access_grants ?? []);
		modelIds = [...new Set<string>(config.model_ids ?? [])];

		size = config.size ?? '';
		seconds = config.seconds === null || config.seconds === undefined ? '' : `${config.seconds}`;
		apiVersion = config.api_version ?? '';
		params = formatJSON(config.params);
		headers = formatJSON(config.headers);
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
		<div class=" flex justify-between dark:text-gray-100 px-5 pt-4 pb-1.5">
			<h1 class="text-lg font-medium self-center font-primary">
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
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-4 pb-4 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit={(e) => {
						e.preventDefault();
						submitHandler();
					}}
				>
					<div class="px-1">
						<div class="flex gap-2">
							<div class="flex flex-col w-full">
								<label for="video-connection-name" class="mb-0.5 text-xs text-gray-500"
									>{$i18n.t('Name')}</label
								>

								<div class="flex-1">
									<input
										id="video-connection-name"
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
								<label for="video-connection-url" class="mb-0.5 text-xs text-gray-500"
									>{$i18n.t('URL')}</label
								>

								<div class="flex-1">
									<input
										id="video-connection-url"
										class={`w-full text-sm ${inputClass}`}
										type="text"
										bind:value={url}
										placeholder={$i18n.t('API Base URL')}
										autocomplete="off"
										list="video-connection-openai-urls"
										required
									/>

									<datalist id="video-connection-openai-urls">
										<option value="https://api.openai.com/v1" />
									</datalist>
								</div>
							</div>

							<Tooltip content={$i18n.t('Verify Connection')} className="self-end -mb-1">
								<button
									class="self-center p-1 bg-transparent hover:bg-gray-100 dark:hover:bg-gray-850 rounded-lg transition"
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
								<label class="sr-only" for="toggle-video-connection"
									>{$i18n.t('Toggle whether current connection is active.')}</label
								>
								<Tooltip content={enable ? $i18n.t('Enabled') : $i18n.t('Disabled')}>
									<Switch id="toggle-video-connection" bind:state={enable} />
								</Tooltip>
							</div>
						</div>

						<div class="flex gap-2 mt-2">
							<div class="flex flex-col w-full">
								<label for="video-connection-auth" class="text-xs text-gray-500"
									>{$i18n.t('Auth')}</label
								>

								<div class="flex gap-2">
									<div class="flex-shrink-0 self-start">
										<select
											id="video-connection-auth"
											class={`w-full text-sm ${selectClass}`}
											bind:value={auth_type}
										>
											<option value="none">{$i18n.t('None')}</option>
											<option value="bearer">{$i18n.t('Bearer')}</option>
											<option value="session">{$i18n.t('Session')}</option>
											<option value="system_oauth">{$i18n.t('OAuth')}</option>
											<option value="microsoft_entra_id">{$i18n.t('Entra ID')}</option>
										</select>
									</div>

									<div class="flex flex-1 items-center">
										{#if auth_type === 'bearer'}
											<SensitiveInput
												bind:value={key}
												placeholder={$i18n.t('API Key')}
												required={false}
											/>
										{:else if auth_type === 'none'}
											<div class={`text-xs self-center translate-y-[1px] text-gray-500`}>
												{$i18n.t('No authentication')}
											</div>
										{:else if auth_type === 'session'}
											<div class={`text-xs self-center translate-y-[1px] text-gray-500`}>
												{$i18n.t('Forwards system user session credentials to authenticate')}
											</div>
										{:else if auth_type === 'system_oauth'}
											<div class={`text-xs self-center translate-y-[1px] text-gray-500`}>
												{$i18n.t('Forwards system user OAuth access token to authenticate')}
											</div>
										{:else if auth_type === 'microsoft_entra_id'}
											<div class={`text-xs self-center translate-y-[1px] text-gray-500`}>
												{$i18n.t('Uses DefaultAzureCredential to authenticate')}
											</div>
										{/if}
									</div>
								</div>
							</div>
						</div>

						<div class="flex flex-col w-full mt-2">
							<div class="mb-1 flex justify-between">
								<div class="mb-0.5 text-xs text-gray-500">
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
							{:else}
								<div class={`text-gray-500 text-xs text-center py-2 px-10`}>
									{$i18n.t(
										'Leave empty to include all video models from "{{url}}/models" endpoint, or the server\'s default model if it does not mark which models make videos',
										{ url }
									)}
								</div>
							{/if}
						</div>

						<div class="flex items-center">
							<label class="sr-only" for="add-video-model-id-input"
								>{$i18n.t('Add a model ID')}</label
							>
							<input
								class={`w-full text-sm ${inputClass} ${modelId ? '' : 'text-gray-500'}`}
								bind:value={modelId}
								id="add-video-model-id-input"
								placeholder={$i18n.t('Add a model ID')}
								list={availableModelIds.length ? 'video-model-id-suggestions' : undefined}
								on:keydown={(event) => {
									if (event.key === 'Enter') {
										event.preventDefault();
										addModelHandler();
									}
								}}
							/>
							{#if availableModelIds.length}
								<datalist id="video-model-id-suggestions">
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

						<div class="flex items-center justify-between">
							<button
								type="button"
								class="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition mt-2"
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
									<label for="video-connection-size" class="mb-0.5 text-xs text-gray-500"
										>{$i18n.t('Video Size')}</label
									>
									<input
										id="video-connection-size"
										class={`w-full text-sm ${inputClass}`}
										type="text"
										bind:value={size}
										placeholder={$i18n.t('Enter Video Size (e.g. 1280x720)')}
										autocomplete="off"
									/>
								</div>

								<div class="flex flex-col w-full">
									<label for="video-connection-seconds" class="mb-0.5 text-xs text-gray-500"
										>{$i18n.t('Video Length')}</label
									>
									<input
										id="video-connection-seconds"
										class={`w-full text-sm ${inputClass}`}
										type="text"
										bind:value={seconds}
										placeholder={$i18n.t('Enter Video Length in seconds (e.g. 8)')}
										autocomplete="off"
									/>
								</div>
							</div>

							<div class="flex gap-2 mt-2">
								<div class="flex flex-col w-full">
									<label for="video-connection-api-version" class="mb-0.5 text-xs text-gray-500"
										>{$i18n.t('API Version')}</label
									>
									<input
										id="video-connection-api-version"
										class={`w-full text-sm ${inputClass}`}
										type="text"
										bind:value={apiVersion}
										placeholder={$i18n.t('API Version')}
										autocomplete="off"
									/>
								</div>
							</div>

							<div class="flex gap-2 mt-2">
								<div class="flex flex-col w-full">
									<label for="video-connection-headers" class="mb-0.5 text-xs text-gray-500"
										>{$i18n.t('Headers')}</label
									>

									<div class="flex-1">
										<Tooltip
											content={$i18n.t(
												'Enter additional headers in JSON format (e.g. {"X-Custom-Header": "value"}'
											)}
										>
											<Textarea
												id="video-connection-headers"
												className="w-full text-sm outline-hidden"
												bind:value={headers}
												placeholder={$i18n.t('Enter additional headers in JSON format')}
												required={false}
												minSize={30}
											/>
										</Tooltip>
									</div>
								</div>
							</div>

							<div class="flex gap-2 mt-2">
								<div class="flex flex-col w-full">
									<label for="video-connection-params" class="mb-0.5 text-xs text-gray-500"
										>{$i18n.t('Additional Parameters')}</label
									>

									<div class="flex-1">
										<Textarea
											id="video-connection-params"
											className="w-full text-sm outline-hidden"
											bind:value={params}
											placeholder={$i18n.t('Enter additional parameters in JSON format')}
											required={false}
											minSize={30}
										/>
									</div>
								</div>
							</div>
						{/if}
					</div>

					<div class="flex justify-between items-center pt-3 text-sm font-medium">
						<div>
							{#if edit}
								<button
									class="px-1 py-1.5 text-sm font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:underline transition"
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
							class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs font-normal text-white transition hover:bg-black disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white disabled:cursor-not-allowed"
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
