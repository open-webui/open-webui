<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext('i18n') as Writable<i18nType>;

	import { verifyOpenAIConnection } from '$lib/apis/openai';
	import { verifyOllamaConnection } from '$lib/apis/ollama';
	import { verifyGeminiConnection } from '$lib/apis/gemini';

	import Modal from '$lib/components/common/Modal.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tags from './common/Tags.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Textarea from './common/Textarea.svelte';
	import CollapsibleSection from '$lib/components/common/CollapsibleSection.svelte';
	import ModelSelectorModal from '$lib/components/common/ModelSelectorModal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	interface ConnectionConfig {
		enable?: boolean;
		tags?: Array<{ name: string }>;
		prefix_id?: string;
		remark?: string;
		model_ids?: string[];
		connection_type?: string;
		auth_type?: string;
		headers?: Record<string, string>;
		azure?: boolean;
		api_version?: string;
		use_responses_api?: boolean;
		responses_api_exclude_patterns?: string[];
	}

	interface Connection {
		url: string;
		key: string;
		config: ConnectionConfig;
	}

	export let onSubmit: Function = () => {};
	export let onDelete: Function = () => {};

	export let show = false;
	export let edit = false;

	export let ollama = false;
	export let gemini = false;
	export let direct = false;

	export let connection: Connection | null = null;

	let url = '';
	let key = '';
	let auth_type = 'bearer';

	let connectionType = 'external';
	let azure = false;
	$: azure =
		(url.includes('azure.') || url.includes('cognitive.microsoft.com')) && !direct ? true : false;

	let prefixId = '';
	let remark = '';
	let enable = true;
	let apiVersion = '';

	let headers = '';

	let tags: Array<{ name: string }> = [];

	let modelIds: string[] = [];

	let useResponsesApi = false;
	let responsesApiExcludePatterns: Array<{ name: string }> = [{ name: 'gemini' }];

	let loading = false;
	let showModelSelector = false;
	let showNoModelsConfirm = false;

	// 检测是否为强制模式（URL 以 # 结尾）
	$: isForceMode = url.trim().endsWith('#');

	// 智能规范化 URL，确保以正确的版本路径结尾
	const normalizeUrl = (inputUrl: string, versionPath: string): string => {
		if (!inputUrl) return '';

		let normalized = inputUrl.trim();

		// 如果以 # 结尾，移除 # 并跳过自动规范化
		if (normalized.endsWith('#')) {
			return normalized.slice(0, -1).replace(/\/+$/, '');
		}

		// 移除末尾的斜杠
		normalized = normalized.replace(/\/+$/, '');

		// 移除可能存在的 chat/completions 等路径
		normalized = normalized.replace(/\/chat\/completions$/, '');
		normalized = normalized.replace(/\/models$/, '');
		normalized = normalized.replace(/\/completions$/, '');
		normalized = normalized.replace(/\/+$/, '');

		// 检查是否已经以版本路径结尾
		if (!normalized.endsWith(versionPath)) {
			// 如果以部分版本路径结尾（如 /v1/ 变成了 /v1），不需要再添加
			// 检查是否有重复的版本路径
			const versionRegex = new RegExp(`${versionPath.replace('/', '\\/')}$`);
			if (!versionRegex.test(normalized)) {
				// 移除可能存在的不完整版本路径
				normalized = normalized.replace(/\/v1beta$/, '');
				normalized = normalized.replace(/\/v1$/, '');
				normalized = normalized.replace(/\/+$/, '');
				// 添加版本路径
				normalized = normalized + versionPath;
			}
		}

		return normalized;
	};

	// 获取规范化后的 URL
	$: normalizedUrl = gemini
		? normalizeUrl(url, '/v1beta')
		: ollama
			? url.trim().endsWith('#')
				? url.trim().slice(0, -1).replace(/\/+$/, '')
				: url.replace(/\/+$/, '')
			: normalizeUrl(url, '/v1');

	// 预览完整的 API 端点
	$: previewEndpoint = (() => {
		if (!url) return '';
		if (isForceMode) {
			// 强制模式下直接显示用户输入（去掉 #）
			return url.trim().slice(0, -1).replace(/\/+$/, '');
		}
		if (gemini) {
			return `${normalizedUrl}/models`;
		} else if (ollama) {
			return `${normalizedUrl}/api/chat`;
		} else {
			return `${normalizedUrl}/chat/completions`;
		}
	})();

	const verifyOllamaHandler = async () => {
		const verifyUrl = normalizedUrl;

		const res = await verifyOllamaConnection(localStorage.token, {
			url: verifyUrl,
			key
		}).catch((error) => {
			toast.error(`${error}`);
		});

		if (res) {
			toast.success($i18n.t('Server connection verified'));
		}
	};

	const verifyOpenAIHandler = async () => {
		const verifyUrl = normalizedUrl;

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
				url: verifyUrl,
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

	const verifyGeminiHandler = async () => {
		const verifyUrl = normalizedUrl;

		const res = await verifyGeminiConnection(localStorage.token, {
			url: verifyUrl,
			key
		}).catch((error) => {
			toast.error(`${error}`);
		});

		if (res) {
			toast.success($i18n.t('Server connection verified'));
		}
	};

	const verifyHandler = () => {
		if (ollama) {
			verifyOllamaHandler();
		} else if (gemini) {
			verifyGeminiHandler();
		} else {
			verifyOpenAIHandler();
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

		// Confirm if no models selected (except Azure which already requires models)
		if (!azure && modelIds.length === 0) {
			loading = false;
			showNoModelsConfirm = true;
			return;
		}

		await doSubmit();
	};

	const doSubmit = async () => {
		loading = true;

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

		// 使用规范化后的 URL
		const submitUrl = normalizedUrl;

		const connection = {
			url: submitUrl,
			key,
			config: {
				enable: enable,
				tags: tags,
				prefix_id: prefixId,
				remark: remark,
				model_ids: modelIds,
				connection_type: connectionType,
				auth_type,
				headers: headers ? JSON.parse(headers) : undefined,
				...(!ollama && azure ? { azure: true, api_version: apiVersion } : {}),
				...(!ollama && !gemini && useResponsesApi ? {
					use_responses_api: true,
					responses_api_exclude_patterns: responsesApiExcludePatterns.map(p => p.name).filter(p => p.trim())
				} : {})
			}
		};

		await onSubmit(connection);

		loading = false;
		show = false;

		url = '';
		key = '';
		auth_type = 'bearer';
		prefixId = '';
		remark = '';
		tags = [];
		modelIds = [];
		useResponsesApi = false;
		responsesApiExcludePatterns = [{ name: 'gemini' }];
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
			remark = connection.config?.remark ?? '';
			modelIds = connection.config?.model_ids ?? [];

			if (ollama) {
				connectionType = connection.config?.connection_type ?? 'local';
			} else {
				connectionType = connection.config?.connection_type ?? 'external';
				azure = connection.config?.azure ?? false;
				apiVersion = connection.config?.api_version ?? '';
				useResponsesApi = connection.config?.use_responses_api ?? false;
				responsesApiExcludePatterns = (connection.config?.responses_api_exclude_patterns ?? ['gemini']).map(p => ({ name: p }));
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

<ModelSelectorModal
	bind:show={showModelSelector}
	bind:modelIds
	{url}
	{key}
	{ollama}
	{gemini}
/>

<ConfirmDialog
	bind:show={showNoModelsConfirm}
	title={$i18n.t('No Models Added')}
	message={$i18n.t('No models added yet. Are you sure you want to save?')}
	confirmLabel={$i18n.t('Save Anyway')}
	on:confirm={doSubmit}
/>

<Modal size="sm" bind:show dismissible={false}>
	<div class="select-text">
		<div class="flex items-center justify-between dark:text-gray-100 px-5 pt-4 pb-3">
			<div class="flex items-center gap-3">
				<h1 class="text-lg font-medium font-primary">
					{#if edit}
						{$i18n.t('Edit Connection')}
					{:else}
						{$i18n.t('Add Connection')}
					{/if}
				</h1>
				<!-- 启用开关移到标题旁边 -->
				<div class="flex items-center gap-2 px-2.5 py-1 rounded-full {enable ? 'bg-emerald-50 dark:bg-emerald-900/30' : 'bg-gray-100 dark:bg-gray-800'}">
					<span class="text-xs font-medium {enable ? 'text-emerald-600 dark:text-emerald-400' : 'text-gray-500'}">{enable ? $i18n.t('Enabled') : $i18n.t('Disabled')}</span>
					<Switch bind:state={enable} />
				</div>
				<!-- Responses API 状态指示器 -->
				{#if !ollama && !gemini && !direct && !azure}
					<div class="flex items-center gap-1.5 px-2.5 py-1 rounded-full {useResponsesApi ? 'bg-blue-50 dark:bg-blue-900/30' : 'bg-gray-100 dark:bg-gray-800'}">
						<span class="text-xs font-medium {useResponsesApi ? 'text-blue-600 dark:text-blue-400' : 'text-gray-500'}">
							Responses API {useResponsesApi ? $i18n.t('Enabled') : $i18n.t('Disabled')}
						</span>
					</div>
				{/if}
			</div>
			<button
				class="self-center p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
				aria-label={$i18n.t('Close modal')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="flex flex-col w-full px-4 pb-4 dark:text-gray-200">
			<form
				class="flex flex-col w-full gap-3"
				on:submit={(e) => {
					e.preventDefault();
					submitHandler();
				}}
			>
				<!-- 基础设置 -->
				<CollapsibleSection title={$i18n.t('Basic Settings')} open={true}>
					<div class="flex flex-col gap-3">
						<!-- API 地址 -->
						<div class="flex flex-col">
							<div class="flex items-center gap-1 mb-1">
								<label for="url-input" class="text-xs text-gray-500">
									{$i18n.t('API Address')}
								</label>
								<Tooltip content={$i18n.t('URL will be auto-normalized (e.g. auto-append /v1). Add # at the end to disable auto-normalization and use exact URL.')}>
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-3.5 text-gray-400 hover:text-gray-500 cursor-help">
										<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM8.94 6.94a.75.75 0 11-1.061-1.061 3 3 0 112.871 5.026v.345a.75.75 0 01-1.5 0v-.5c0-.72.57-1.172 1.081-1.287A1.5 1.5 0 108.94 6.94zM10 15a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
									</svg>
								</Tooltip>
								{#if isForceMode}
									<span class="text-xs text-amber-600 dark:text-amber-400 ml-1">({$i18n.t('Force mode')})</span>
								{/if}
							</div>
							<div class="flex gap-2">
								<input
									id="url-input"
									class="flex-1 px-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg focus:outline-none"
									type="text"
									bind:value={url}
									placeholder={$i18n.t('Enter API address')}
									autocomplete="off"
									required
								/>
								<Tooltip content={$i18n.t('Test Connection')}>
									<button
										type="button"
										class="p-2 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
										on:click={verifyHandler}
										aria-label={$i18n.t('Test Connection')}
									>
										<!-- 心跳/脉冲检测图标 -->
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="size-4">
											<path d="M22 12h-4l-3 9L9 3l-3 9H2" />
										</svg>
									</button>
								</Tooltip>
							</div>
							<div class="text-xs text-gray-400 mt-1">
								<span class="text-gray-500">{$i18n.t('Preview')}:</span>
								{#if url && previewEndpoint}
									<span class="text-gray-600 dark:text-gray-300 break-all">{previewEndpoint}</span>
								{:else if gemini}
									<span class="break-all">https://generativelanguage.googleapis.com/v1beta/models</span>
								{:else if ollama}
									<span class="break-all">http://localhost:11434/api/chat</span>
								{:else}
									<span class="break-all">https://api.openai.com/v1/chat/completions</span>
								{/if}
							</div>
						</div>

						<!-- API Key -->
						<div class="flex flex-col">
							<label for="api-key-input" class="text-xs text-gray-500 mb-1">
								{$i18n.t('API Key')}
							</label>
							<SensitiveInput
								bind:value={key}
								placeholder={$i18n.t('Enter API key, usually starts with sk')}
								required={false}
								outerClassName="flex flex-1 px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg"
								inputClassName="w-full text-sm bg-transparent outline-none"
							/>
						</div>

						<!-- 备注名称和分组标签（同一行） -->
						<div class="flex gap-3">
							<div class="flex flex-col flex-1">
								<label for="remark-input" class="text-xs text-gray-500 mb-1">
									{$i18n.t('Remark Name')}
								</label>
								<input
									id="remark-input"
									class="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg focus:outline-none"
									type="text"
									bind:value={remark}
									placeholder={$i18n.t('e.g. Claude API')}
									autocomplete="off"
								/>
							</div>
							<div class="flex flex-col flex-1">
								<span class="text-xs text-gray-500 mb-1">{$i18n.t('Group Tag')}</span>
								<Tags
									bind:tags
									placeholder={$i18n.t('Add tags for model classification')}
									on:add={(e) => {
										tags = [...tags, { name: e.detail }];
									}}
									on:delete={(e) => {
										tags = tags.filter((tag) => tag.name !== e.detail);
									}}
								/>
							</div>
						</div>
					</div>
				</CollapsibleSection>

				<!-- 模型管理 -->
				<CollapsibleSection title={$i18n.t('Model Management')} open={true}>
					<div class="flex flex-col gap-3">
						<div class="flex items-center justify-between">
							<div class="text-sm">
								{#if modelIds.length > 0}
									<span class="text-gray-700 dark:text-gray-300">{$i18n.t('{{count}} models selected', { count: modelIds.length })}</span>
								{:else}
									<span class="text-gray-500">{$i18n.t('Please add models in Model Management')}</span>
								{/if}
							</div>
							<button
								type="button"
								class="px-3 py-1.5 text-sm font-medium bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition"
								on:click={() => (showModelSelector = true)}
							>
								{$i18n.t('Manage Models')}
							</button>
						</div>

						{#if modelIds.length > 0}
							<div class="flex flex-wrap gap-1.5">
								{#each modelIds.slice(0, 5) as modelId}
									<span class="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-800 rounded-md truncate max-w-32">
										{modelId}
									</span>
								{/each}
								{#if modelIds.length > 5}
									<span class="px-2 py-1 text-xs text-gray-500">
										{$i18n.t('+{{count}} more', { count: modelIds.length - 5 })}
									</span>
								{/if}
							</div>
						{:else if azure}
							<div class="text-xs text-amber-600 dark:text-amber-400">
								{$i18n.t('Deployment names are required for Azure OpenAI')}
							</div>
						{/if}
					</div>
				</CollapsibleSection>

				<!-- 高级设置 -->
				<CollapsibleSection title={$i18n.t('Advanced Settings')} open={false}>
					<div class="flex flex-col gap-3">
						{#if !direct}
							<!-- 连接类型 -->
							<div class="flex items-center justify-between">
								<span class="text-sm">{$i18n.t('Connection Type')}</span>
								<button
									type="button"
									class="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-800 rounded-lg"
									on:click={() => (connectionType = connectionType === 'local' ? 'external' : 'local')}
								>
									{connectionType === 'local' ? $i18n.t('Local') : $i18n.t('External')}
								</button>
							</div>
						{/if}

						{#if !ollama && !direct}
							<!-- Provider Type -->
							<div class="flex items-center justify-between">
								<span class="text-sm">{$i18n.t('Provider Type')}</span>
								<button
									type="button"
									class="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-800 rounded-lg"
									on:click={() => (azure = !azure)}
								>
									{azure ? $i18n.t('Azure OpenAI') : $i18n.t('OpenAI')}
								</button>
							</div>
						{/if}

						{#if azure}
							<!-- API Version -->
							<div class="flex flex-col">
								<label for="api-version" class="text-xs text-gray-500 mb-1">
									{$i18n.t('API Version')}
								</label>
								<input
									id="api-version"
									class="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg focus:outline-none"
									type="text"
									bind:value={apiVersion}
									placeholder={$i18n.t('API Version')}
									required
								/>
							</div>
						{/if}

						{#if !ollama && !direct && !gemini && !azure}
							<!-- Use Responses API -->
							<div class="flex flex-col gap-2">
								<div class="flex items-center justify-between">
									<div>
										<span class="text-sm">{$i18n.t('Use Responses API')}</span>
										{#if useResponsesApi}
											<div class="text-xs text-amber-600 dark:text-amber-400 mt-0.5">
												{$i18n.t('Ensure the API supports Responses format')}
											</div>
										{/if}
									</div>
									<Switch bind:state={useResponsesApi} />
								</div>

								{#if useResponsesApi}
									<!-- Responses API Exclude Patterns -->
									<div class="flex flex-col mt-1">
										<label for="responses-exclude" class="text-xs text-gray-500 mb-1">
											{$i18n.t('Exclude Models')}
										</label>
										<Tags
											bind:tags={responsesApiExcludePatterns}
											placeholder={$i18n.t('Add model keyword to exclude')}
											on:add={(e) => {
												responsesApiExcludePatterns = [...responsesApiExcludePatterns, { name: e.detail }];
											}}
											on:delete={(e) => {
												responsesApiExcludePatterns = responsesApiExcludePatterns.filter((p) => p.name !== e.detail);
											}}
										/>
										<div class="text-xs text-gray-400 mt-1">
											{$i18n.t('Models containing these keywords will use Chat Completions API instead')}
										</div>
									</div>
								{/if}
							</div>
						{/if}

						<!-- Prefix ID -->
						<div class="flex flex-col">
							<label for="prefix-id" class="text-xs text-gray-500 mb-1">
								{$i18n.t('Prefix ID')}
							</label>
							<input
								id="prefix-id"
								class="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg focus:outline-none"
								type="text"
								bind:value={prefixId}
								placeholder={$i18n.t('Optional prefix for model IDs')}
							/>
						</div>

						{#if !ollama && !direct}
							<!-- Headers -->
							<div class="flex flex-col">
								<label for="headers" class="text-xs text-gray-500 mb-1">
									{$i18n.t('Custom Headers (JSON)')}
								</label>
								<Textarea
									className="w-full text-sm"
									bind:value={headers}
									placeholder={$i18n.t('{"X-Custom-Header": "value"}')}
									required={false}
									minSize={60}
								/>
							</div>
						{/if}
					</div>
				</CollapsibleSection>

				<!-- 按钮 -->
				<div class="flex justify-end pt-2 gap-2">
					{#if edit}
						<button
							type="button"
							class="px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/40 border border-red-200 dark:border-red-800 rounded-full transition"
							on:click={() => {
								onDelete();
								show = false;
							}}
						>
							{$i18n.t('Delete')}
						</button>
					{/if}

					<button
						type="submit"
						class="px-4 py-2 text-sm font-medium bg-black dark:bg-white text-white dark:text-black hover:bg-gray-800 dark:hover:bg-gray-100 rounded-full transition flex items-center gap-2"
						disabled={loading}
					>
						{$i18n.t('Save')}
						{#if loading}
							<Spinner className="size-4" />
						{/if}
					</button>
				</div>
			</form>
		</div>
	</div>
</Modal>
