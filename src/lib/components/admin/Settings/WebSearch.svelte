<script lang="ts">
	import { getRAGConfig, updateRAGConfig } from '$lib/apis/retrieval';
	import Switch from '$lib/components/common/Switch.svelte';

	import { config, models } from '$lib/stores';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';
	import AdminSettingField from './AdminSettingField.svelte';
	import AdminSettingRow from './AdminSettingRow.svelte';
	import AdminSettingSection from './AdminSettingSection.svelte';

	const i18n: any = getContext('i18n');

	export let saveHandler: Function;

	let webSearchEngines = [
		'ollama_cloud',
		'perplexity_search',
		'searxng',
		'yacy',
		'google_pse',
		'brave',
		'brave_llm_context',
		'kagi',
		'mojeek',
		'bocha',
		'serpstack',
		'serper',
		'serphouse',
		'serply',
		'searchapi',
		'serpapi',
		'duckduckgo',
		'tavily',
		'jina',
		'bing',
		'exa',
		'perplexity',
		'microsoft_web_iq',
		'sougou',
		'firecrawl',
		'external',
		'yandex',
		'youcom',
		'linkup',
		'openserp'
	];
	let webLoaderEngines = ['playwright', 'firecrawl', 'tavily', 'microsoft_web_iq', 'external'];

	let webConfig: any = null;
	const inputClass =
		'w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';
	const textareaClass =
		'w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';

	const submitHandler = async () => {
		// Convert domain filter string to array before sending
		if (
			typeof webConfig.WEB_SEARCH_DOMAIN_FILTER_LIST === 'string' &&
			webConfig.WEB_SEARCH_DOMAIN_FILTER_LIST
		) {
			webConfig.WEB_SEARCH_DOMAIN_FILTER_LIST = webConfig.WEB_SEARCH_DOMAIN_FILTER_LIST.split(',')
				.map((domain: string) => domain.trim())
				.filter((domain: string) => domain.length > 0);
		} else if (!Array.isArray(webConfig.WEB_SEARCH_DOMAIN_FILTER_LIST)) {
			webConfig.WEB_SEARCH_DOMAIN_FILTER_LIST = [];
		}

		// Convert Youtube loader language string to array before sending
		if (
			typeof webConfig.YOUTUBE_LOADER_LANGUAGE === 'string' &&
			webConfig.YOUTUBE_LOADER_LANGUAGE
		) {
			webConfig.YOUTUBE_LOADER_LANGUAGE = webConfig.YOUTUBE_LOADER_LANGUAGE.split(',')
				.map((lang: string) => lang.trim())
				.filter((lang: string) => lang.length > 0);
		} else if (!Array.isArray(webConfig.YOUTUBE_LOADER_LANGUAGE)) {
			webConfig.YOUTUBE_LOADER_LANGUAGE = [];
		}

		// Convert numeric timeout values to strings (backend expects strings)
		if (typeof webConfig.FIRECRAWL_TIMEOUT === 'number') {
			webConfig.FIRECRAWL_TIMEOUT = webConfig.FIRECRAWL_TIMEOUT.toString();
		}
		if (typeof webConfig.PLAYWRIGHT_TIMEOUT === 'number') {
			webConfig.PLAYWRIGHT_TIMEOUT = webConfig.PLAYWRIGHT_TIMEOUT.toString();
		}

		// Convert Linkup params JSON string to object before sending
		const linkupParams =
			typeof webConfig.LINKUP_SEARCH_PARAMS === 'string' &&
			webConfig.LINKUP_SEARCH_PARAMS.trim() !== ''
				? JSON.parse(webConfig.LINKUP_SEARCH_PARAMS)
				: (webConfig.LINKUP_SEARCH_PARAMS ?? {});

		const res = await updateRAGConfig(localStorage.token, {
			web: {
				...webConfig,
				EXA_MAX_CONTENT_LENGTH: webConfig.EXA_MAX_CONTENT_LENGTH ?? null,
				LINKUP_SEARCH_PARAMS: linkupParams
			}
		});

		// Convert arrays back to strings for display
		if (Array.isArray(webConfig.WEB_SEARCH_DOMAIN_FILTER_LIST)) {
			webConfig.WEB_SEARCH_DOMAIN_FILTER_LIST = webConfig.WEB_SEARCH_DOMAIN_FILTER_LIST.join(',');
		}
		if (Array.isArray(webConfig.YOUTUBE_LOADER_LANGUAGE)) {
			webConfig.YOUTUBE_LOADER_LANGUAGE = webConfig.YOUTUBE_LOADER_LANGUAGE.join(',');
		}
	};

	onMount(async () => {
		const res = await getRAGConfig(localStorage.token);

		if (res) {
			webConfig = res.web;

			// Convert array back to comma-separated string for display
			if (Array.isArray(webConfig?.WEB_SEARCH_DOMAIN_FILTER_LIST)) {
				webConfig.WEB_SEARCH_DOMAIN_FILTER_LIST = webConfig.WEB_SEARCH_DOMAIN_FILTER_LIST.join(',');
			} else if (!webConfig.WEB_SEARCH_DOMAIN_FILTER_LIST) {
				webConfig.WEB_SEARCH_DOMAIN_FILTER_LIST = '';
			}

			if (Array.isArray(webConfig?.YOUTUBE_LOADER_LANGUAGE)) {
				webConfig.YOUTUBE_LOADER_LANGUAGE = webConfig.YOUTUBE_LOADER_LANGUAGE.join(',');
			} else if (!webConfig.YOUTUBE_LOADER_LANGUAGE) {
				webConfig.YOUTUBE_LOADER_LANGUAGE = '';
			}

			// Convert timeout strings to numbers for number input fields
			if (webConfig.FIRECRAWL_TIMEOUT && typeof webConfig.FIRECRAWL_TIMEOUT === 'string') {
				const parsed = parseInt(webConfig.FIRECRAWL_TIMEOUT);
				if (!isNaN(parsed)) {
					webConfig.FIRECRAWL_TIMEOUT = parsed;
				}
			}
			if (webConfig.PLAYWRIGHT_TIMEOUT && typeof webConfig.PLAYWRIGHT_TIMEOUT === 'string') {
				const parsed = parseInt(webConfig.PLAYWRIGHT_TIMEOUT);
				if (!isNaN(parsed)) {
					webConfig.PLAYWRIGHT_TIMEOUT = parsed;
				}
			}

			// Convert Linkup params object to JSON string for textarea display
			webConfig.LINKUP_SEARCH_PARAMS =
				typeof webConfig.LINKUP_SEARCH_PARAMS === 'object'
					? JSON.stringify(webConfig.LINKUP_SEARCH_PARAMS ?? {}, null, 2)
					: (webConfig.LINKUP_SEARCH_PARAMS ?? '');
		}
	});
</script>

<form
	class="flex h-full flex-col justify-between text-sm"
	on:submit|preventDefault={async () => {
		await submitHandler();
		saveHandler();
	}}
>
	<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">
		{$i18n.t('settings.admin.web.title')}
	</h2>

	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		{#if webConfig}
			<AdminSettingSection first title={$i18n.t('settings.admin.web.sections.search.title')}>
				<AdminSettingRow
					label={$i18n.t('settings.admin.web.webSearch.label')}
					description={$i18n.t('settings.admin.web.webSearch.description')}
					let:labelId
				>
					<Switch bind:state={webConfig.ENABLE_WEB_SEARCH} ariaLabelledbyId={labelId} />
				</AdminSettingRow>

				<AdminSettingRow
					label={$i18n.t('settings.admin.web.webSearchConfirmation.label')}
					description={$i18n.t('settings.admin.web.webSearchConfirmation.description')}
					let:labelId
				>
					<Switch
						bind:state={webConfig.ENABLE_WEB_SEARCH_CONFIRMATION}
						ariaLabelledbyId={labelId}
					/>
				</AdminSettingRow>

				{#if webConfig.ENABLE_WEB_SEARCH_CONFIRMATION}
					<AdminSettingField
						label={$i18n.t('settings.admin.web.webSearchConfirmationContent.label')}
						description={$i18n.t('settings.admin.web.webSearchConfirmationContent.description')}
					>
						<Textarea
							className={textareaClass}
							placeholder={$i18n.t(
								'Your query will be sent to the configured web search provider.'
							)}
							bind:value={webConfig.WEB_SEARCH_CONFIRMATION_CONTENT}
						/>
					</AdminSettingField>
				{/if}

				<AdminSettingRow
					label={$i18n.t('settings.admin.web.webSearchEngine.label')}
					description={$i18n.t('settings.admin.web.webSearchEngine.description')}
				>
					<SettingsSelect
						bind:value={webConfig.WEB_SEARCH_ENGINE}
						placeholder={$i18n.t('Select a engine')}
						required
					>
						<option disabled selected value="">{$i18n.t('Select a engine')}</option>
						{#each webSearchEngines as engine}
							{#if engine === 'duckduckgo' || engine === 'ddgs'}
								<option value={engine} disabled={$config?.features?.slim}>DDGS</option>
							{:else if engine === 'serphouse'}
								<option value={engine}>SERPHouse</option>
							{:else}
								<option value={engine}>{engine}</option>
							{/if}
						{/each}
					</SettingsSelect>
				</AdminSettingRow>

				{#if webConfig.WEB_SEARCH_ENGINE !== ''}
					{#if webConfig.WEB_SEARCH_ENGINE === 'ollama_cloud'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.ollamaCloudApiKey.label')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<SensitiveInput
											variant="settings"
											placeholder={$i18n.t('Enter Ollama Cloud API Key')}
											bind:value={webConfig.OLLAMA_CLOUD_WEB_SEARCH_API_KEY}
										/>
									</div>
								</div>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'perplexity_search'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.perplexitySearchApiUrl.label')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
											type="text"
											placeholder={$i18n.t('Enter Perplexity Search API URL')}
											bind:value={webConfig.PERPLEXITY_SEARCH_API_URL}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>
						</div>

						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.perplexityApiKey.label')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<SensitiveInput
											variant="settings"
											placeholder={$i18n.t('Enter Perplexity API Key')}
											bind:value={webConfig.PERPLEXITY_API_KEY}
										/>
									</div>
								</div>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'searxng'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-left text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.searxngQueryUrl.label')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
											type="text"
											placeholder={$i18n.t('Enter Searxng Query URL')}
											bind:value={webConfig.SEARXNG_QUERY_URL}
											autocomplete="off"
											required
										/>
									</div>
								</div>
							</div>
							<div class="mb-2.5 flex w-full flex-col">
								<div class=" self-left text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.searxngSearchLanguageAllEnEsDeFrEtc.label')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
											type="text"
											placeholder={$i18n.t('Enter Searxng search language')}
											bind:value={webConfig.SEARXNG_LANGUAGE}
											autocomplete="off"
											required
										/>
									</div>
								</div>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'yacy'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.yacyInstanceUrl.label')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
											type="text"
											placeholder={$i18n.t('Enter Yacy URL (e.g. http://yacy.example.com:8090)')}
											bind:value={webConfig.YACY_QUERY_URL}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>
						</div>
						<div class="mb-2.5 flex w-full flex-col">
							<div class="flex gap-2">
								<div class="w-full">
									<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
										{$i18n.t('settings.admin.web.yacyUsername.label')}
									</div>

									<input
										class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
										placeholder={$i18n.t('Enter Yacy Username')}
										bind:value={webConfig.YACY_USERNAME}
										required
									/>
								</div>

								<div class="w-full">
									<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
										{$i18n.t('settings.admin.web.yacyPassword.label')}
									</div>

									<SensitiveInput
										variant="settings"
										placeholder={$i18n.t('Enter Yacy Password')}
										bind:value={webConfig.YACY_PASSWORD}
									/>
								</div>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'google_pse'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.googlePseApiKey.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter Google PSE API Key')}
									bind:value={webConfig.GOOGLE_PSE_API_KEY}
								/>
							</div>
							<div class="mt-1.5">
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.googlePseEngineId.label')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
											type="text"
											placeholder={$i18n.t('Enter Google PSE Engine Id')}
											bind:value={webConfig.GOOGLE_PSE_ENGINE_ID}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'brave'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.braveSearchApiKey.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter Brave Search API Key')}
									bind:value={webConfig.BRAVE_SEARCH_API_KEY}
								/>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'brave_llm_context'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.braveSearchApiKey.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter Brave Search API Key')}
									bind:value={webConfig.BRAVE_SEARCH_API_KEY}
								/>
							</div>
							<div class="mt-1.5">
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.contextTokens.label')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
											type="number"
											min="1024"
											max="32768"
											step="1024"
											placeholder={$i18n.t('Max tokens to retrieve (1024-32768, default 8192)')}
											bind:value={webConfig.BRAVE_SEARCH_CONTEXT_TOKENS}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'kagi'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.kagiSearchApiKey.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter Kagi Search API Key')}
									bind:value={webConfig.KAGI_SEARCH_API_KEY}
								/>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'mojeek'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.mojeekSearchApiKey.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter Mojeek Search API Key')}
									bind:value={webConfig.MOJEEK_SEARCH_API_KEY}
								/>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'bocha'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.bochaSearchApiKey.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter Bocha Search API Key')}
									bind:value={webConfig.BOCHA_SEARCH_API_KEY}
								/>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'serpstack'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.serpstackApiKey.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter Serpstack API Key')}
									bind:value={webConfig.SERPSTACK_API_KEY}
								/>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'serper'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.serperApiKey.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter Serper API Key')}
									bind:value={webConfig.SERPER_API_KEY}
								/>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'serphouse'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.serphouseApiKey.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter SERPHouse API Key')}
									bind:value={webConfig.SERPHOUSE_API_KEY}
								/>
							</div>
							<div class="mt-1.5">
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.serphouseDomain.label')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
											type="text"
											placeholder="google.com"
											bind:value={webConfig.SERPHOUSE_DOMAIN}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'serply'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.serplyApiKey.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter Serply API Key')}
									bind:value={webConfig.SERPLY_API_KEY}
								/>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'tavily'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.tavilyApiKey.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter Tavily API Key')}
									bind:value={webConfig.TAVILY_API_KEY}
								/>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'searchapi'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.searchapiApiKey.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter SearchApi API Key')}
									bind:value={webConfig.SEARCHAPI_API_KEY}
								/>
							</div>
							<div class="mt-1.5">
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.searchapiEngine.label')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
											type="text"
											placeholder={$i18n.t('Enter SearchApi Engine')}
											bind:value={webConfig.SEARCHAPI_ENGINE}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'serpapi'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.serpapiApiKey.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter SerpApi API Key')}
									bind:value={webConfig.SERPAPI_API_KEY}
								/>
							</div>
							<div class="mt-1.5">
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.serpapiEngine.label')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
											type="text"
											placeholder={$i18n.t('Enter SerpApi Engine')}
											bind:value={webConfig.SERPAPI_ENGINE}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'jina'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.jinaApiBaseUrl.label')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
											type="text"
											placeholder={$i18n.t('Enter Jina API Base URL')}
											bind:value={webConfig.JINA_API_BASE_URL}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>

							<div class="mt-2">
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.jinaApiKey.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter Jina API Key')}
									bind:value={webConfig.JINA_API_KEY}
								/>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'bing'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.bingSearchV7Endpoint.label')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
											type="text"
											placeholder={$i18n.t('Enter Bing Search V7 Endpoint')}
											bind:value={webConfig.BING_SEARCH_V7_ENDPOINT}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>

							<div class="mt-2">
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.bingSearchV7SubscriptionKey.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter Bing Search V7 Subscription Key')}
									bind:value={webConfig.BING_SEARCH_V7_SUBSCRIPTION_KEY}
								/>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'exa'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.exaApiKey.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter Exa API Key')}
									bind:value={webConfig.EXA_API_KEY}
								/>
							</div>
							<AdminSettingField
								className="mt-1.5"
								label={$i18n.t('settings.admin.web.maxContentLength.label')}
								forId="exa-max-content-length"
								description={$i18n.t('settings.admin.web.maxContentLength.description')}
							>
								<input
									id="exa-max-content-length"
									class={inputClass}
									type="number"
									min="1"
									step="1"
									placeholder={$i18n.t('No limit')}
									bind:value={webConfig.EXA_MAX_CONTENT_LENGTH}
								/>
							</AdminSettingField>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'perplexity'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.perplexityApiKey.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter Perplexity API Key')}
									bind:value={webConfig.PERPLEXITY_API_KEY}
								/>
							</div>
						</div>

						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class="self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.perplexityModel.label')}
								</div>
								<input
									list="perplexity-model-list"
									class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
									bind:value={webConfig.PERPLEXITY_MODEL}
								/>

								<datalist id="perplexity-model-list">
									<option value="sonar">{$i18n.t('Sonar')}</option>
									<option value="sonar-pro">{$i18n.t('Sonar Pro')}</option>
									<option value="sonar-reasoning">{$i18n.t('Sonar Reasoning')}</option>
									<option value="sonar-reasoning-pro">{$i18n.t('Sonar Reasoning Pro')}</option>
									<option value="sonar-deep-research">{$i18n.t('Sonar Deep Research')}</option>
								</datalist>
							</div>
						</div>

						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.perplexitySearchContextUsage.label')}
								</div>
								<SettingsSelect
									bind:value={webConfig.PERPLEXITY_SEARCH_CONTEXT_USAGE}
									className="w-full"
								>
									<option value="low">{$i18n.t('Low')}</option>
									<option value="medium">{$i18n.t('Medium')}</option>
									<option value="high">{$i18n.t('High')}</option>
								</SettingsSelect>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'microsoft_web_iq'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.microsoftWebIqApiBaseUrl.label')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
											type="text"
											placeholder={$i18n.t('Enter Microsoft Web IQ API Base URL')}
											bind:value={webConfig.MICROSOFT_WEB_IQ_API_BASE_URL}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>

							<div class="mt-2">
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.microsoftWebIqApiKey.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter Microsoft Web IQ API Key')}
									bind:value={webConfig.MICROSOFT_WEB_IQ_API_KEY}
								/>
							</div>

							<div class="mt-2">
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.language.label')}
								</div>

								<input
									class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
									type="text"
									placeholder={$i18n.t('Enter language')}
									bind:value={webConfig.MICROSOFT_WEB_IQ_LANGUAGE}
									autocomplete="off"
								/>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'sougou'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.sougouSearchApiSid.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter Sougou Search API sID')}
									bind:value={webConfig.SOUGOU_API_SID}
								/>
							</div>
						</div>
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.sougouSearchApiSk.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter Sougou Search API SK')}
									bind:value={webConfig.SOUGOU_API_SK}
								/>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'firecrawl'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.firecrawlApiBaseUrl.label')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
											type="text"
											placeholder={$i18n.t('Enter Firecrawl API Base URL')}
											bind:value={webConfig.FIRECRAWL_API_BASE_URL}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>

							<div class="mt-2">
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.firecrawlApiKey.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter Firecrawl API Key')}
									bind:value={webConfig.FIRECRAWL_API_KEY}
								/>
							</div>

							<div class="mt-2">
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.firecrawlTimeoutS.label')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
											type="number"
											placeholder={$i18n.t('Enter Firecrawl Timeout')}
											bind:value={webConfig.FIRECRAWL_TIMEOUT}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'external'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.externalWebSearchUrl.label')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
											type="text"
											placeholder={$i18n.t('Enter External Web Search URL')}
											bind:value={webConfig.EXTERNAL_WEB_SEARCH_URL}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>

							<div class="mt-2">
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.externalWebSearchApiKey.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter External Web Search API Key')}
									bind:value={webConfig.EXTERNAL_WEB_SEARCH_API_KEY}
								/>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'yandex'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.yandexWebSearchUrl.label')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
											type="text"
											placeholder={$i18n.t('Enter Yandex Web Search URL')}
											bind:value={webConfig.YANDEX_WEB_SEARCH_URL}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>

							<div class="mt-2">
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.yandexWebSearchApiKey.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter Yandex Web Search API Key')}
									bind:value={webConfig.YANDEX_WEB_SEARCH_API_KEY}
								/>
							</div>

							<div class="mb-2.5">
								<div class=" mb-1 text-xs text-gray-600 dark:text-gray-400">
									{$i18n.t('settings.admin.web.yandexWebSearchConfig.label')}
								</div>

								<Tooltip
									content={$i18n.t(
										'Leave empty to use the default config, or enter a valid json (see https://yandex.cloud/en/docs/search-api/api-ref/WebSearch/search#yandex.cloud.searchapi.v2.WebSearchRequest)'
									)}
									placement="top-start"
								>
									<Textarea
										className={textareaClass}
										bind:value={webConfig.YANDEX_WEB_SEARCH_CONFIG}
										placeholder={$i18n.t(
											'Leave empty to use the default config, or enter a valid json (see https://yandex.cloud/en/docs/search-api/api-ref/WebSearch/search#yandex.cloud.searchapi.v2.WebSearchRequest)'
										)}
									/>
								</Tooltip>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'youcom'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.youComApiKey.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter You.com API Key')}
									bind:value={webConfig.YOUCOM_API_KEY}
								/>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'linkup'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.linkupApiKey.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter Linkup API Key')}
									bind:value={webConfig.LINKUP_API_KEY}
								/>
							</div>

							<div class="mt-2">
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.parameters.label')}
								</div>

								<Textarea
									className={textareaClass}
									bind:value={webConfig.LINKUP_SEARCH_PARAMS}
									placeholder={`{\n  "depth": "standard",\n  "outputType": "sourcedAnswer"\n}`}
								/>
							</div>
						</div>
					{:else if webConfig.WEB_SEARCH_ENGINE === 'openserp'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.openserpUrl.label')}
								</div>

								<div class="flex-1">
									<input
										class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
										type="text"
										placeholder={$i18n.t('Enter OpenSERP Base URL')}
										bind:value={webConfig.OPENSERP_BASE_URL}
										autocomplete="off"
										required
									/>
								</div>
							</div>
						</div>
					{/if}

					{#if webConfig.WEB_SEARCH_ENGINE === 'duckduckgo'}
						<div class="mb-2.5 flex w-full flex-col">
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.ddgsBackend.label')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<SettingsSelect bind:value={webConfig.DDGS_BACKEND} className="w-full">
											<option value="auto">{$i18n.t('Auto (Random)')}</option>
											<option value="bing">{$i18n.t('Bing')}</option>
											<option value="brave">{$i18n.t('Brave')}</option>
											<option value="duckduckgo">{$i18n.t('DuckDuckGo')}</option>
											<option value="google">{$i18n.t('Google')}</option>
											<option value="grokipedia">{$i18n.t('Grokipedia')}</option>
											<option value="mojeek">{$i18n.t('Mojeek')}</option>
											<option value="wikipedia">{$i18n.t('Wikipedia')}</option>
											<option value="yahoo">{$i18n.t('Yahoo')}</option>
											<option value="yandex">{$i18n.t('Yandex')}</option>
										</SettingsSelect>
									</div>
								</div>
							</div>
						</div>
					{/if}
				{/if}

				{#if webConfig.ENABLE_WEB_SEARCH}
					<AdminSettingField
						label={$i18n.t('settings.admin.web.searchLimits.label')}
						description={$i18n.t('settings.admin.web.searchLimits.description')}
					>
						<div class="flex gap-2">
							<div class="w-full">
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.searchResultCount.label')}
								</div>

								<input
									class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
									placeholder={$i18n.t('settings.admin.web.searchResultCount.label')}
									bind:value={webConfig.WEB_SEARCH_RESULT_COUNT}
									required
								/>
							</div>

							<div class="w-full">
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									<Tooltip
										content={$i18n.t('settings.admin.web.searchResultCount.description')}
										placement="top-start"
									>
										{$i18n.t('settings.admin.web.concurrentRequests.label')}
									</Tooltip>
								</div>

								<input
									class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
									placeholder={$i18n.t('settings.admin.web.concurrentRequests.label')}
									bind:value={webConfig.WEB_SEARCH_CONCURRENT_REQUESTS}
									type="number"
									min="0"
								/>
							</div>
						</div>
					</AdminSettingField>

					<AdminSettingField
						label={$i18n.t('settings.admin.web.fetchUrlContentLengthLimit.label')}
						description={$i18n.t('settings.admin.web.fetchUrlContentLengthLimit.description')}
					>
						<input
							class={inputClass}
							placeholder={$i18n.t('No limit')}
							bind:value={webConfig.WEB_FETCH_MAX_CONTENT_LENGTH}
							type="number"
							min="0"
						/>
					</AdminSettingField>

					<AdminSettingField
						label={$i18n.t('settings.admin.web.domainFilterList.label')}
						description={$i18n.t('settings.admin.web.domainFilterList.description')}
					>
						<input
							class={inputClass}
							placeholder={$i18n.t(
								'Enter domains separated by commas (e.g., example.com,site.org,!excludedsite.com)'
							)}
							bind:value={webConfig.WEB_SEARCH_DOMAIN_FILTER_LIST}
						/>
					</AdminSettingField>
				{/if}

				<AdminSettingRow
					label={$i18n.t('settings.admin.web.bypassEmbeddingAndRetrieval.label')}
					description={webConfig.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL
						? $i18n.t('settings.admin.web.bypassEmbeddingAndRetrieval.description')
						: $i18n.t('Use segmented retrieval for focused and relevant content extraction.')}
					let:labelId
				>
					<Switch
						bind:state={webConfig.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL}
						ariaLabelledbyId={labelId}
					/>
				</AdminSettingRow>

				<AdminSettingRow
					label={$i18n.t('settings.admin.web.bypassWebLoader.label')}
					description={$i18n.t('settings.admin.web.bypassWebLoader.description')}
					let:labelId
				>
					<Switch bind:state={webConfig.BYPASS_WEB_SEARCH_WEB_LOADER} ariaLabelledbyId={labelId} />
				</AdminSettingRow>

				<AdminSettingRow
					label={$i18n.t('settings.admin.web.trustProxyEnvironment.label')}
					description={webConfig.WEB_SEARCH_TRUST_ENV
						? $i18n.t('settings.admin.web.trustProxyEnvironment.description')
						: $i18n.t('Fetch page contents without proxy environment variables.')}
					let:labelId
				>
					<Switch bind:state={webConfig.WEB_SEARCH_TRUST_ENV} ariaLabelledbyId={labelId} />
				</AdminSettingRow>
			</AdminSettingSection>

			<AdminSettingSection title={$i18n.t('settings.admin.web.sections.loader.title')}>
				<AdminSettingRow
					label={$i18n.t('settings.admin.web.webLoaderEngine.label')}
					description={$i18n.t('settings.admin.web.webLoaderEngine.description')}
				>
					<SettingsSelect
						bind:value={webConfig.WEB_LOADER_ENGINE}
						placeholder={$i18n.t('Select a engine')}
					>
						<option value="">{$i18n.t('Default')}</option>
						{#each webLoaderEngines as engine}
							<option value={engine} disabled={$config?.features?.slim && engine === 'playwright'}
								>{engine}</option
							>
						{/each}
					</SettingsSelect>
				</AdminSettingRow>

				{#if webConfig.WEB_LOADER_ENGINE === '' || webConfig.WEB_LOADER_ENGINE === 'safe_web'}
					<AdminSettingField
						label={$i18n.t('settings.admin.web.timeout.label')}
						description={$i18n.t('settings.admin.web.timeout.description')}
					>
						<input
							class={inputClass}
							placeholder={$i18n.t('settings.admin.web.timeout.label')}
							bind:value={webConfig.WEB_LOADER_TIMEOUT}
						/>
					</AdminSettingField>

					<AdminSettingRow
						label={$i18n.t('settings.admin.web.verifySslCertificate.label')}
						description={$i18n.t('settings.admin.web.verifySslCertificate.description')}
						let:labelId
					>
						<Switch
							bind:state={webConfig.ENABLE_WEB_LOADER_SSL_VERIFICATION}
							ariaLabelledbyId={labelId}
						/>
					</AdminSettingRow>
				{:else if webConfig.WEB_LOADER_ENGINE === 'playwright'}
					<div class="mb-2.5 flex w-full flex-col">
						<div>
							<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
								{$i18n.t('settings.admin.web.playwrightWebsocketUrl.label')}
							</div>

							<div class="flex w-full">
								<div class="flex-1">
									<input
										class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
										type="text"
										placeholder={$i18n.t('Enter Playwright WebSocket URL')}
										bind:value={webConfig.PLAYWRIGHT_WS_URL}
										autocomplete="off"
									/>
								</div>
							</div>
						</div>

						<div class="mt-2">
							<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
								{$i18n.t('settings.admin.web.playwrightTimeoutMs.label')}
							</div>

							<div class="flex w-full">
								<div class="flex-1">
									<input
										class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
										placeholder={$i18n.t('Enter Playwright Timeout')}
										bind:value={webConfig.PLAYWRIGHT_TIMEOUT}
										autocomplete="off"
									/>
								</div>
							</div>
						</div>
					</div>
				{:else if webConfig.WEB_LOADER_ENGINE === 'firecrawl' && webConfig.WEB_SEARCH_ENGINE !== 'firecrawl'}
					<div class="mb-2.5 flex w-full flex-col">
						<div>
							<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
								{$i18n.t('settings.admin.web.firecrawlApiBaseUrl.label')}
							</div>

							<div class="flex w-full">
								<div class="flex-1">
									<input
										class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
										type="text"
										placeholder={$i18n.t('Enter Firecrawl API Base URL')}
										bind:value={webConfig.FIRECRAWL_API_BASE_URL}
										autocomplete="off"
									/>
								</div>
							</div>
						</div>

						<div class="mt-2">
							<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
								{$i18n.t('settings.admin.web.firecrawlApiKey.label')}
							</div>

							<SensitiveInput
								variant="settings"
								placeholder={$i18n.t('Enter Firecrawl API Key')}
								bind:value={webConfig.FIRECRAWL_API_KEY}
							/>
						</div>
					</div>
				{:else if webConfig.WEB_LOADER_ENGINE === 'tavily'}
					<div class="mb-2.5 flex w-full flex-col">
						<div>
							<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
								{$i18n.t('settings.admin.web.tavilyExtractDepth.label')}
							</div>

							<div class="flex w-full">
								<div class="flex-1">
									<input
										class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
										type="text"
										placeholder={$i18n.t('Enter Tavily Extract Depth')}
										bind:value={webConfig.TAVILY_EXTRACT_DEPTH}
										autocomplete="off"
									/>
								</div>
							</div>
						</div>

						{#if webConfig.WEB_SEARCH_ENGINE !== 'tavily'}
							<div class="mt-2">
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.tavilyApiKey.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter Tavily API Key')}
									bind:value={webConfig.TAVILY_API_KEY}
								/>
							</div>
						{/if}
					</div>
				{:else if webConfig.WEB_LOADER_ENGINE === 'microsoft_web_iq'}
					<div class="mb-2.5 flex w-full flex-col">
						{#if webConfig.WEB_SEARCH_ENGINE !== 'microsoft_web_iq'}
							<div>
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.microsoftWebIqApiBaseUrl.label')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
											type="text"
											placeholder={$i18n.t('Enter Microsoft Web IQ API Base URL')}
											bind:value={webConfig.MICROSOFT_WEB_IQ_API_BASE_URL}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>

							<div class="mt-2">
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.microsoftWebIqApiKey.label')}
								</div>

								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter Microsoft Web IQ API Key')}
									bind:value={webConfig.MICROSOFT_WEB_IQ_API_KEY}
								/>
							</div>

							<div class="mt-2">
								<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
									{$i18n.t('settings.admin.web.language.label')}
								</div>

								<input
									class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
									type="text"
									placeholder={$i18n.t('Enter language')}
									bind:value={webConfig.MICROSOFT_WEB_IQ_LANGUAGE}
									autocomplete="off"
								/>
							</div>
						{/if}
					</div>
				{:else if webConfig.WEB_LOADER_ENGINE === 'external'}
					<div class="mb-2.5 flex w-full flex-col">
						<div>
							<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
								{$i18n.t('settings.admin.web.externalWebLoaderUrl.label')}
							</div>

							<div class="flex w-full">
								<div class="flex-1">
									<input
										class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
										type="text"
										placeholder={$i18n.t('Enter External Web Loader URL')}
										bind:value={webConfig.EXTERNAL_WEB_LOADER_URL}
										autocomplete="off"
									/>
								</div>
							</div>
						</div>

						<div class="mt-2">
							<div class=" self-center text-xs text-gray-600 dark:text-gray-400 mb-1">
								{$i18n.t('settings.admin.web.externalWebLoaderApiKey.label')}
							</div>

							<SensitiveInput
								variant="settings"
								placeholder={$i18n.t('Enter External Web Loader API Key')}
								bind:value={webConfig.EXTERNAL_WEB_LOADER_API_KEY}
							/>
						</div>
					</div>
				{/if}

				<AdminSettingField
					label={$i18n.t('settings.admin.web.concurrentRequests.label')}
					description={$i18n.t('settings.admin.web.concurrentRequests.description')}
				>
					<input
						class={inputClass}
						placeholder={$i18n.t('settings.admin.web.concurrentRequests.label')}
						bind:value={webConfig.WEB_LOADER_CONCURRENT_REQUESTS}
						required
					/>
				</AdminSettingField>

				<AdminSettingField
					label={$i18n.t('settings.admin.web.youtubeLanguage.label')}
					description={$i18n.t('settings.admin.web.youtubeLanguage.description')}
				>
					<input
						class={inputClass}
						type="text"
						placeholder={$i18n.t('Enter language codes')}
						bind:value={webConfig.YOUTUBE_LOADER_LANGUAGE}
						autocomplete="off"
					/>
				</AdminSettingField>

				<AdminSettingField
					label={$i18n.t('settings.admin.web.youtubeProxyUrl.label')}
					description={$i18n.t('settings.admin.web.youtubeProxyUrl.description')}
				>
					<input
						class={inputClass}
						type="text"
						placeholder={$i18n.t('Enter proxy URL (e.g. https://user:password@host:port)')}
						bind:value={webConfig.YOUTUBE_LOADER_PROXY_URL}
						autocomplete="off"
					/>
				</AdminSettingField>
			</AdminSettingSection>
		{/if}
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
