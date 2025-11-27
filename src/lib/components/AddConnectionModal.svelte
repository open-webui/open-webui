<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { settings } from '$lib/stores';
	import { verifyOpenAIConnection } from '$lib/apis/openai';
	import { verifyOllamaConnection } from '$lib/apis/ollama';

	import Modal from '$lib/components/common/Modal.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Minus from '$lib/components/icons/Minus.svelte';
	import PencilSolid from '$lib/components/icons/PencilSolid.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tags from './common/Tags.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Textarea from './common/Textarea.svelte';

	export let onSubmit: Function = () => {};
	export let onDelete: Function = () => {};

	export let show = false;
	export let edit = false;

	export let ollama = false;
	export let direct = false;

	export let connection = null;

	let url = '';
	let key = '';
	let auth_type = 'bearer';

	let connectionType = 'external';
	let azure = false;
	$: azure =
		(url.includes('azure.') || url.includes('cognitive.microsoft.com')) && !direct ? true : false;

	let prefixId = '';
	let enable = true;
	let apiVersion = '';

	let headers = '';

	let tags = [];

	let modelId = '';
	let modelIds = [];

	let loading = false;

	const verifyOllamaHandler = async () => {
		// remove trailing slash from url
		url = url.replace(/\/$/, '');

		const res = await verifyOllamaConnection(localStorage.token, {
			url,
			key
		}).catch((error) => {
			toast.error(`${error}`);
		});

		if (res) {
			toast.success($i18n.t('Server connection verified'));
		}
	};

	const verifyOpenAIHandler = async () => {
		// remove trailing slash from url
		url = url.replace(/\/$/, '');

		let _headers = null;

		if (headers) {
			try {
				_headers = JSON.parse(headers);
				if (typeof _headers !== 'object' || Array.isArray(_headers)) {
					_headers = null;
					throw new Error('Headers must be a valid JSON object');
				}
				headers = JSON.stringify(_headers, null, 2);
			} catch (error) {
				toast.error($i18n.t('Headers must be a valid JSON object'));
				return;
			}
		}

		const res = await verifyOpenAIConnection(
			localStorage.token,
			{
				url,
				key,
				config: {
					auth_type,
					azure: azure,
					api_version: apiVersion,
					...(_headers ? { headers: _headers } : {})
				}
			},
			direct
		).catch((error) => {
			toast.error(`${error}`);
		});

		if (res) {
			toast.success($i18n.t('Server connection verified'));
		}
	};

	const verifyHandler = () => {
		if (ollama) {
			verifyOllamaHandler();
		} else {
			verifyOpenAIHandler();
		}
	};

	const addModelHandler = () => {
		if (modelId) {
			modelIds = [...modelIds, modelId];
			modelId = '';
		}
	};

	const submitHandler = async () => {
		loading = true;

		if (!ollama && !url) {
			loading = false;
			toast.error($i18n.t('URL is required'));
			return;
		}

		if (azure) {
			if (!apiVersion) {
				loading = false;

				toast.error($i18n.t('API Version is required'));
				return;
			}

			if (!key && !['azure_ad', 'microsoft_entra_id'].includes(auth_type)) {
				loading = false;

				toast.error($i18n.t('Key is required'));
				return;
			}

			if (modelIds.length === 0) {
				loading = false;
				toast.error($i18n.t('Deployment names are required for Azure OpenAI'));
				return;
			}
		}

		if (headers) {
			try {
				const _headers = JSON.parse(headers);
				if (typeof _headers !== 'object' || Array.isArray(_headers)) {
					throw new Error('Headers must be a valid JSON object');
				}
				headers = JSON.stringify(_headers, null, 2);
			} catch (error) {
				toast.error($i18n.t('Headers must be a valid JSON object'));
				return;
			}
		}

		// remove trailing slash from url
		url = url.replace(/\/$/, '');

		const connection = {
			url,
			key,
			config: {
				enable: enable,
				tags: tags,
				prefix_id: prefixId,
				model_ids: modelIds,
				connection_type: connectionType,
				auth_type,
				headers: headers ? JSON.parse(headers) : undefined,
				...(!ollama && azure ? { azure: true, api_version: apiVersion } : {})
			}
		};

		await onSubmit(connection);

		loading = false;
		show = false;

		url = '';
		key = '';
		auth_type = 'bearer';
		prefixId = '';
		tags = [];
		modelIds = [];
	};

	const init = () => {
		if (connection) {
			url = connection.url;
			key = connection.key;

			auth_type = connection.config.auth_type ?? 'bearer';
			headers = connection.config?.headers
				? JSON.stringify(connection.config.headers, null, 2)
				: '';

			enable = connection.config?.enable ?? true;
			tags = connection.config?.tags ?? [];
			prefixId = connection.config?.prefix_id ?? '';
			modelIds = connection.config?.model_ids ?? [];

			if (ollama) {
				connectionType = connection.config?.connection_type ?? 'local';
			} else {
				connectionType = connection.config?.connection_type ?? 'external';
				azure = connection.config?.azure ?? false;
				apiVersion = connection.config?.api_version ?? '';
			}
		}
	};

	$: if (show) {
		init();
	}

	onMount(() => {
		init();
	});
</script>

<Modal size="sm" bind:show>
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
						{#if !direct}
							<div class="flex gap-2">
								<div class="flex w-full justify-between items-center">
									<div class=" text-xs text-gray-500">{$i18n.t('Connection Type')}</div>

									<div class="">
										<button
											on:click={() => {
												connectionType = connectionType === 'local' ? 'external' : 'local';
											}}
											type="button"
											class=" text-xs text-gray-700 dark:text-gray-300"
										>
											{#if connectionType === 'local'}
												{$i18n.t('Local')}
											{:else}
												{$i18n.t('External')}
											{/if}
										</button>
									</div>
								</div>
							</div>
						{/if}

						<div class="flex gap-2 mt-1.5">
							<div class="flex flex-col w-full">
								<label
									for="url-input"
									class={`mb-0.5 text-xs text-gray-500
								${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : ''}`}
									>{$i18n.t('URL')}</label
								>

								<div class="flex-1">
									<input
										id="url-input"
										class={`w-full text-sm bg-transparent ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
										type="text"
										bind:value={url}
										placeholder={$i18n.t('API Base URL')}
										autocomplete="off"
										required
									/>
								</div>
							</div>

							<Tooltip content={$i18n.t('Verify Connection')} className="self-end -mb-1">
								<button
									class="self-center p-1 bg-transparent hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-850 rounded-lg transition"
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
								<label class="sr-only" for="toggle-connection"
									>{$i18n.t('Toggle whether current connection is active.')}</label
								>
								<Tooltip content={enable ? $i18n.t('Enabled') : $i18n.t('Disabled')}>
									<Switch id="toggle-connection" bind:state={enable} />
								</Tooltip>
							</div>
						</div>

						<div class="flex gap-2 mt-2">
							<div class="flex flex-col w-full">
								<label
									for="select-bearer-or-session"
									class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
									>{$i18n.t('Auth')}</label
								>

								<div class="flex gap-2">
									<div class="flex-shrink-0 self-start">
										<select
											id="select-bearer-or-session"
											class={`w-full text-sm bg-transparent pr-5 ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
											bind:value={auth_type}
										>
											<option value="none">{$i18n.t('None')}</option>
											<option value="bearer">{$i18n.t('Bearer')}</option>

											{#if !ollama}
												<option value="session">{$i18n.t('Session')}</option>
												{#if !direct}
													<option value="system_oauth">{$i18n.t('OAuth')}</option>
													{#if azure}
														<option value="microsoft_entra_id">{$i18n.t('Entra ID')}</option>
													{/if}
												{/if}
											{/if}
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
											<div
												class={`text-xs self-center translate-y-[1px] ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
											>
												{$i18n.t('No authentication')}
											</div>
										{:else if auth_type === 'session'}
											<div
												class={`text-xs self-center translate-y-[1px] ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
											>
												{$i18n.t('Forwards system user session credentials to authenticate')}
											</div>
										{:else if auth_type === 'system_oauth'}
											<div
												class={`text-xs self-center translate-y-[1px] ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
											>
												{$i18n.t('Forwards system user OAuth access token to authenticate')}
											</div>
										{:else if ['azure_ad', 'microsoft_entra_id'].includes(auth_type)}
											<div
												class={`text-xs self-center translate-y-[1px] ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
											>
												{$i18n.t('Uses DefaultAzureCredential to authenticate')}
											</div>
										{/if}
									</div>
								</div>
							</div>
						</div>

						{#if !ollama && !direct}
							<div class="flex gap-2 mt-2">
								<div class="flex flex-col w-full">
									<label
										for="headers-input"
										class={`mb-0.5 text-xs text-gray-500
								${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : ''}`}
										>{$i18n.t('Headers')}</label
									>

									<div class="flex-1">
										<Tooltip
											content={$i18n.t(
												'Enter additional headers in JSON format (e.g. {"X-Custom-Header": "value"}'
											)}
										>
											<Textarea
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
						{/if}

						<div class="flex gap-2 mt-2">
							<div class="flex flex-col w-full">
								<label
									for="prefix-id-input"
									class={`mb-0.5 text-xs text-gray-500
								${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : ''}`}
									>{$i18n.t('Prefix ID')}</label
								>

								<div class="flex-1">
									<Tooltip
										content={$i18n.t(
											'Prefix ID is used to avoid conflicts with other connections by adding a prefix to the model IDs - leave empty to disable'
										)}
									>
										<input
											class={`w-full text-sm bg-transparent ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
											type="text"
											id="prefix-id-input"
											bind:value={prefixId}
											placeholder={$i18n.t('Prefix ID')}
											autocomplete="off"
										/>
									</Tooltip>
								</div>
							</div>
						</div>

						{#if !ollama && !direct}
							<div class="flex flex-row justify-between items-center w-full mt-2">
								<label
									for="prefix-id-input"
									class={`mb-0.5 text-xs text-gray-500
								${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : ''}`}
									>{$i18n.t('Provider Type')}</label
								>

								<div>
									<button
										on:click={() => {
											azure = !azure;
										}}
										type="button"
										class=" text-xs text-gray-700 dark:text-gray-300"
									>
										{azure ? $i18n.t('Azure OpenAI') : $i18n.t('OpenAI')}
									</button>
								</div>
							</div>
						{/if}

						{#if azure}
							<div class="flex gap-2 mt-2">
								<div class="flex flex-col w-full">
									<label
										for="api-version-input"
										class={`mb-0.5 text-xs text-gray-500
								${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : ''}`}
										>{$i18n.t('API Version')}</label
									>

									<div class="flex-1">
										<input
											id="api-version-input"
											class={`w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
											type="text"
											bind:value={apiVersion}
											placeholder={$i18n.t('API Version')}
											autocomplete="off"
											required
										/>
									</div>
								</div>
							</div>
						{/if}

						<div class="flex flex-col w-full mt-2">
							<div class="mb-1 flex justify-between">
								<div
									class={`mb-0.5 text-xs text-gray-500
								${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : ''}`}
								>
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
								<div
									class={`text-gray-500 text-xs text-center py-2 px-10
								${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : ''}`}
								>
									{#if ollama}
										{$i18n.t('Leave empty to include all models from "{{url}}/api/tags" endpoint', {
											url: url
										})}
									{:else if azure}
										{$i18n.t('Deployment names are required for Azure OpenAI')}
										<!-- {$i18n.t('Leave empty to include all models from "{{url}}" endpoint', {
											url: `${url}/openai/deployments`
										})} -->
									{:else}
										{$i18n.t('Leave empty to include all models from "{{url}}/models" endpoint', {
											url: url
										})}
									{/if}
								</div>
							{/if}
						</div>

						<div class="flex items-center">
							<label class="sr-only" for="add-model-id-input">{$i18n.t('Add a model ID')}</label>
							<input
								class="w-full py-1 text-sm rounded-lg bg-transparent {modelId
									? ''
									: 'text-gray-500'} {($settings?.highContrastMode ?? false)
									? 'dark:placeholder:text-gray-100 placeholder:text-gray-700'
									: 'placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden'}"
								bind:value={modelId}
								id="add-model-id-input"
								placeholder={$i18n.t('Add a model ID')}
							/>

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
					</div>

					<div class="flex gap-2 mt-2">
						<div class="flex flex-col w-full">
							<div
								class={`mb-0.5 text-xs text-gray-500
								${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : ''}`}
							>
								{$i18n.t('Tags')}
							</div>

							<div class="flex-1 mt-0.5">
								<Tags
									bind:tags
									on:add={(e) => {
										tags = [
											...tags,
											{
												name: e.detail
											}
										];
									}}
									on:delete={(e) => {
										tags = tags.filter((tag) => tag.name !== e.detail);
									}}
								/>
							</div>
						</div>
					</div>

					<div class="flex justify-end pt-3 text-sm font-medium gap-1.5">
						{#if edit}
							<button
								class="px-3.5 py-1.5 text-sm font-medium dark:bg-black dark:hover:bg-gray-900 dark:text-white bg-white text-black hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center"
								type="button"
								on:click={() => {
									onDelete();
									show = false;
								}}
							>
								{$i18n.t('Delete')}
							</button>
						{/if}

						<button
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center {loading
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={loading}
						>
							{$i18n.t('Save')}

							{#if loading}
								<div class="ml-2 self-center">
									<Spinner />
								</div>
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>
