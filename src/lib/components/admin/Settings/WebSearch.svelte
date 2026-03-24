<script lang="ts">
	import { getRAGConfig, updateRAGConfig } from '$lib/apis/retrieval';
	import Switch from '$lib/components/common/Switch.svelte';

	import { models } from '$lib/stores';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import SelectDropdown from '$lib/components/common/SelectDropdown.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let webSearchEngines = [
		'searxng',
		'google_pse',
		'brave',
		'kagi',
		'mojeek',
		'bocha',
		'serpstack',
		'serper',
		'serply',
		'searchapi',
		'serpapi',
		'duckduckgo',
		'tavily',
		'jina',
		'bing',
		'exa',
		'perplexity',
		'sougou'
	];
	let webLoaderEngines = ['playwright', 'firecrawl', 'tavily'];

	$: webSearchEngineOptions = [
		{ value: '', label: 'Select a engine' },
		...webSearchEngines.map((engine) => ({ value: engine, label: engine }))
	];

	$: webLoaderEngineOptions = [
		{ value: '', label: 'Default' },
		...webLoaderEngines.map((engine) => ({ value: engine, label: engine }))
	];

	let webConfig = null;

	const submitHandler = async () => {
		// Convert domain filter string to array before sending
		if (webConfig.WEB_SEARCH_DOMAIN_FILTER_LIST) {
			webConfig.WEB_SEARCH_DOMAIN_FILTER_LIST = webConfig.WEB_SEARCH_DOMAIN_FILTER_LIST.split(',')
				.map((domain) => domain.trim())
				.filter((domain) => domain.length > 0);
		} else {
			webConfig.WEB_SEARCH_DOMAIN_FILTER_LIST = [];
		}

		// Convert Youtube loader language string to array before sending
		if (webConfig.YOUTUBE_LOADER_LANGUAGE) {
			webConfig.YOUTUBE_LOADER_LANGUAGE = webConfig.YOUTUBE_LOADER_LANGUAGE.split(',')
				.map((lang) => lang.trim())
				.filter((lang) => lang.length > 0);
		} else {
			webConfig.YOUTUBE_LOADER_LANGUAGE = [];
		}

		const res = await updateRAGConfig(localStorage.token, {
			web: webConfig
		});

		webConfig.WEB_SEARCH_DOMAIN_FILTER_LIST = webConfig.WEB_SEARCH_DOMAIN_FILTER_LIST.join(',');
		webConfig.YOUTUBE_LOADER_LANGUAGE = webConfig.YOUTUBE_LOADER_LANGUAGE.join(',');
	};

	onMount(async () => {
		const res = await getRAGConfig(localStorage.token);

		if (res) {
			webConfig = res.web;

			// Convert array back to comma-separated string for display
			if (webConfig?.WEB_SEARCH_DOMAIN_FILTER_LIST) {
				webConfig.WEB_SEARCH_DOMAIN_FILTER_LIST = webConfig.WEB_SEARCH_DOMAIN_FILTER_LIST.join(',');
			}

			webConfig.YOUTUBE_LOADER_LANGUAGE = webConfig.YOUTUBE_LOADER_LANGUAGE.join(',');
		}
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		await submitHandler();
		saveHandler();
	}}
>
	<div class="space-y-3 overflow-y-auto scrollbar-hidden h-full" style="padding-right: 4px;">
		{#if webConfig}
			<div class="">
				<!-- General Section -->
				<div class="mb-3" style="background: linear-gradient(to bottom, rgba(0,0,0,0.02), transparent); border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid rgba(0,0,0,0.05);">
					<div class="mb-4 flex items-center gap-2">
					<div class="w-1 h-6 bg-orange-500 rounded-sm"></div>
					<div class="text-base font-medium text-gray-800 dark:text-gray-200 tracking-tight">
						{$i18n.t('General')}
					</div>
				</div>

					<div class="space-y-3" style="background: white; border-radius: 10px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid rgba(0,0,0,0.06);">
						<!-- Web Search Toggle -->
						<div class="flex w-full justify-between items-center" style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
							<div class="self-center text-xs font-medium" style="color: #374151; font-size: 13px;">
								{$i18n.t('Web Search')}
							</div>
							<div class="flex items-center relative">
								<Switch bind:state={webConfig.ENABLE_WEB_SEARCH} />
							</div>
						</div>

						<!-- Web Search Engine -->
						<div class="flex w-full flex-col gap-2 sm:flex-row sm:justify-between sm:items-center" style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
							<div class="self-center text-xs font-medium" style="color: #374151; font-size: 13px;">
								{$i18n.t('Web Search Engine')}
							</div>
							<div class="w-full sm:w-auto">
								<SelectDropdown
									value={webConfig.WEB_SEARCH_ENGINE}
									options={webSearchEngineOptions}
									on:change={(e) => (webConfig.WEB_SEARCH_ENGINE = e.detail.value)}
								/>
							</div>
						</div>

						<!-- Engine-specific Configuration -->
						{#if webConfig.WEB_SEARCH_ENGINE !== ''}
							<div style="padding: 12px; background: #f9fafb; border-radius: 8px; border: 1px solid rgba(0,0,0,0.06);">
								{#if webConfig.WEB_SEARCH_ENGINE === 'searxng'}
									<div class="flex w-full flex-col">
										<div>
											<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
												{$i18n.t('Searxng Query URL')}
											</div>

											<div class="flex w-full">
												<div class="flex-1">
													<input
														class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
														type="text"
														placeholder={$i18n.t('Enter Searxng Query URL')}
														bind:value={webConfig.SEARXNG_QUERY_URL}
														autocomplete="off"
														style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
													/>
												</div>
											</div>
										</div>
									</div>
								{:else if webConfig.WEB_SEARCH_ENGINE === 'google_pse'}
									<div class="flex w-full flex-col" style="gap: 12px;">
										<div>
											<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
												{$i18n.t('Google PSE API Key')}
											</div>

											<SensitiveInput
												placeholder={$i18n.t('Enter Google PSE API Key')}
												bind:value={webConfig.GOOGLE_PSE_API_KEY}
											/>
										</div>
										<div class="mt-1.5">
											<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
												{$i18n.t('Google PSE Engine Id')}
											</div>

											<div class="flex w-full">
												<div class="flex-1">
													<input
														class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
														type="text"
														placeholder={$i18n.t('Enter Google PSE Engine Id')}
														bind:value={webConfig.GOOGLE_PSE_ENGINE_ID}
														autocomplete="off"
														style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
													/>
												</div>
											</div>
										</div>
									</div>
								{:else if webConfig.WEB_SEARCH_ENGINE === 'brave'}
									<div class="flex w-full flex-col">
										<div>
											<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
												{$i18n.t('Brave Search API Key')}
											</div>

											<SensitiveInput
												placeholder={$i18n.t('Enter Brave Search API Key')}
												bind:value={webConfig.BRAVE_SEARCH_API_KEY}
											/>
										</div>
									</div>
								{:else if webConfig.WEB_SEARCH_ENGINE === 'kagi'}
									<div class="flex w-full flex-col">
										<div>
											<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
												{$i18n.t('Kagi Search API Key')}
											</div>

											<SensitiveInput
												placeholder={$i18n.t('Enter Kagi Search API Key')}
												bind:value={webConfig.KAGI_SEARCH_API_KEY}
											/>
										</div>
									</div>
								{:else if webConfig.WEB_SEARCH_ENGINE === 'mojeek'}
									<div class="flex w-full flex-col">
										<div>
											<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
												{$i18n.t('Mojeek Search API Key')}
											</div>

											<SensitiveInput
												placeholder={$i18n.t('Enter Mojeek Search API Key')}
												bind:value={webConfig.MOJEEK_SEARCH_API_KEY}
											/>
										</div>
									</div>
								{:else if webConfig.WEB_SEARCH_ENGINE === 'bocha'}
									<div class="flex w-full flex-col">
										<div>
											<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
												{$i18n.t('Bocha Search API Key')}
											</div>

											<SensitiveInput
												placeholder={$i18n.t('Enter Bocha Search API Key')}
												bind:value={webConfig.BOCHA_SEARCH_API_KEY}
											/>
										</div>
									</div>
								{:else if webConfig.WEB_SEARCH_ENGINE === 'serpstack'}
									<div class="flex w-full flex-col">
										<div>
											<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
												{$i18n.t('Serpstack API Key')}
											</div>

											<SensitiveInput
												placeholder={$i18n.t('Enter Serpstack API Key')}
												bind:value={webConfig.SERPSTACK_API_KEY}
											/>
										</div>
									</div>
								{:else if webConfig.WEB_SEARCH_ENGINE === 'serper'}
									<div class="flex w-full flex-col">
										<div>
											<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
												{$i18n.t('Serper API Key')}
											</div>

											<SensitiveInput
												placeholder={$i18n.t('Enter Serper API Key')}
												bind:value={webConfig.SERPER_API_KEY}
											/>
										</div>
									</div>
								{:else if webConfig.WEB_SEARCH_ENGINE === 'serply'}
									<div class="flex w-full flex-col">
										<div>
											<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
												{$i18n.t('Serply API Key')}
											</div>

											<SensitiveInput
												placeholder={$i18n.t('Enter Serply API Key')}
												bind:value={webConfig.SERPLY_API_KEY}
											/>
										</div>
									</div>
								{:else if webConfig.WEB_SEARCH_ENGINE === 'tavily'}
									<div class="flex w-full flex-col">
										<div>
											<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
												{$i18n.t('Tavily API Key')}
											</div>

											<SensitiveInput
												placeholder={$i18n.t('Enter Tavily API Key')}
												bind:value={webConfig.TAVILY_API_KEY}
											/>
										</div>
									</div>
								{:else if webConfig.WEB_SEARCH_ENGINE === 'searchapi'}
									<div class="flex w-full flex-col" style="gap: 12px;">
										<div>
											<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
												{$i18n.t('SearchApi API Key')}
											</div>

											<SensitiveInput
												placeholder={$i18n.t('Enter SearchApi API Key')}
												bind:value={webConfig.SEARCHAPI_API_KEY}
											/>
										</div>
										<div class="mt-1.5">
											<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
												{$i18n.t('SearchApi Engine')}
											</div>

											<div class="flex w-full">
												<div class="flex-1">
													<input
														class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
														type="text"
														placeholder={$i18n.t('Enter SearchApi Engine')}
														bind:value={webConfig.SEARCHAPI_ENGINE}
														autocomplete="off"
														style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
													/>
												</div>
											</div>
										</div>
									</div>
								{:else if webConfig.WEB_SEARCH_ENGINE === 'serpapi'}
									<div class="flex w-full flex-col" style="gap: 12px;">
										<div>
											<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
												{$i18n.t('SerpApi API Key')}
											</div>

											<SensitiveInput
												placeholder={$i18n.t('Enter SerpApi API Key')}
												bind:value={webConfig.SERPAPI_API_KEY}
											/>
										</div>
										<div class="mt-1.5">
											<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
												{$i18n.t('SerpApi Engine')}
											</div>

											<div class="flex w-full">
												<div class="flex-1">
													<input
														class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
														type="text"
														placeholder={$i18n.t('Enter SerpApi Engine')}
														bind:value={webConfig.SERPAPI_ENGINE}
														autocomplete="off"
														style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
													/>
												</div>
											</div>
										</div>
									</div>
								{:else if webConfig.WEB_SEARCH_ENGINE === 'jina'}
									<div class="flex w-full flex-col">
										<div>
											<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
												{$i18n.t('Jina API Key')}
											</div>

											<SensitiveInput
												placeholder={$i18n.t('Enter Jina API Key')}
												bind:value={webConfig.JINA_API_KEY}
											/>
										</div>
									</div>
								{:else if webConfig.WEB_SEARCH_ENGINE === 'bing'}
									<div class="flex w-full flex-col" style="gap: 12px;">
										<div>
											<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
												{$i18n.t('Bing Search V7 Endpoint')}
											</div>

											<div class="flex w-full">
												<div class="flex-1">
													<input
														class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
														type="text"
														placeholder={$i18n.t('Enter Bing Search V7 Endpoint')}
														bind:value={webConfig.BING_SEARCH_V7_ENDPOINT}
														autocomplete="off"
														style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
													/>
												</div>
											</div>
										</div>

										<div class="mt-2">
											<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
												{$i18n.t('Bing Search V7 Subscription Key')}
											</div>

											<SensitiveInput
												placeholder={$i18n.t('Enter Bing Search V7 Subscription Key')}
												bind:value={webConfig.BING_SEARCH_V7_SUBSCRIPTION_KEY}
											/>
										</div>
									</div>
								{:else if webConfig.WEB_SEARCH_ENGINE === 'exa'}
									<div class="flex w-full flex-col">
										<div>
											<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
												{$i18n.t('Exa API Key')}
											</div>

											<SensitiveInput
												placeholder={$i18n.t('Enter Exa API Key')}
												bind:value={webConfig.EXA_API_KEY}
											/>
										</div>
									</div>
								{:else if webConfig.WEB_SEARCH_ENGINE === 'perplexity'}
									<div>
										<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
											{$i18n.t('Perplexity API Key')}
										</div>

										<SensitiveInput
											placeholder={$i18n.t('Enter Perplexity API Key')}
											bind:value={webConfig.PERPLEXITY_API_KEY}
										/>
									</div>
								{:else if webConfig.WEB_SEARCH_ENGINE === 'sougou'}
									<div class="flex w-full flex-col" style="gap: 12px;">
										<div>
											<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
												{$i18n.t('Sougou Search API sID')}
											</div>

											<SensitiveInput
												placeholder={$i18n.t('Enter Sougou Search API sID')}
												bind:value={webConfig.SOUGOU_API_SID}
											/>
										</div>
										<div>
											<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
												{$i18n.t('Sougou Search API SK')}
											</div>

											<SensitiveInput
												placeholder={$i18n.t('Enter Sougou Search API SK')}
												bind:value={webConfig.SOUGOU_API_SK}
											/>
										</div>
									</div>
								{/if}
							</div>
						{/if}

						{#if webConfig.ENABLE_WEB_SEARCH}
							<!-- Search Configuration -->
							<div style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
								<div class="flex w-full flex-col">
									<div class="flex gap-2" style="gap: 12px;">
										<div class="w-full">
											<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
												{$i18n.t('Search Result Count')}
											</div>

											<input
												class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
												placeholder={$i18n.t('Search Result Count')}
												bind:value={webConfig.WEB_SEARCH_RESULT_COUNT}
												required
												style="background: #f9fafb; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s; text-align: center;"
											/>
										</div>

										<div class="w-full">
											<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
												{$i18n.t('Concurrent Requests')}
											</div>

											<input
												class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
												placeholder={$i18n.t('Concurrent Requests')}
												bind:value={webConfig.WEB_SEARCH_CONCURRENT_REQUESTS}
												required
												style="background: #f9fafb; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s; text-align: center;"
											/>
										</div>
									</div>
								</div>
							</div>

							<!-- Domain Filter -->
							<div style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
								<div class="flex w-full flex-col">
									<div class="text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
										{$i18n.t('Domain Filter List')}
									</div>

									<input
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
										placeholder={$i18n.t(
											'Enter domains separated by commas (e.g., example.com,site.org)'
										)}
										bind:value={webConfig.WEB_SEARCH_DOMAIN_FILTER_LIST}
										style="background: #f9fafb; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
									/>
								</div>
							</div>
						{/if}

						<!-- Bypass Embedding -->
						<div class="flex w-full justify-between items-center" style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
							<div class="self-center text-xs font-medium" style="color: #374151; font-size: 13px;">
								<Tooltip content={$i18n.t('Full Context Mode')} placement="top-start">
									{$i18n.t('Bypass Embedding and Retrieval')}
								</Tooltip>
							</div>
							<div class="flex items-center relative">
								<Tooltip
									content={webConfig.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL
										? $i18n.t(
												'Inject the entire content as context for comprehensive processing, this is recommended for complex queries.'
											)
										: $i18n.t(
												'Default to segmented retrieval for focused and relevant content extraction, this is recommended for most cases.'
											)}
								>
									<Switch bind:state={webConfig.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL} />
								</Tooltip>
							</div>
						</div>

						<!-- Trust Proxy -->
						<div class="flex w-full justify-between items-center" style="padding: 8px 0;">
							<div class="self-center text-xs font-medium" style="color: #374151; font-size: 13px;">
								{$i18n.t('Trust Proxy Environment')}
							</div>
							<div class="flex items-center relative">
								<Tooltip
									content={webConfig.WEB_SEARCH_TRUST_ENV
										? $i18n.t(
												'Use proxy designated by http_proxy and https_proxy environment variables to fetch page contents.'
											)
										: $i18n.t('Use no proxy to fetch page contents.')}
								>
									<Switch bind:state={webConfig.WEB_SEARCH_TRUST_ENV} />
								</Tooltip>
							</div>
						</div>
					</div>
				</div>

				<!-- Loader Section -->
				<div class="mb-3" style="background: linear-gradient(to bottom, rgba(0,0,0,0.02), transparent); border-radius: 12px; padding: 20px; border: 1px solid rgba(0,0,0,0.05);">
					<div class="mb-4 flex items-center gap-2">
					<div class="w-1 h-6 bg-orange-500 rounded-sm"></div>
					<div class="text-base font-medium text-gray-800 dark:text-gray-200 tracking-tight">
						{$i18n.t('Loader')}
					</div>
				</div>

					<div class="space-y-3" style="background: white; border-radius: 10px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid rgba(0,0,0,0.06);">
						<!-- Web Loader Engine -->
						<div class="flex w-full flex-col gap-2 sm:flex-row sm:justify-between sm:items-center" style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
							<div class="self-center text-xs font-medium" style="color: #374151; font-size: 13px;">
								{$i18n.t('Web Loader Engine')}
							</div>
							<div class="w-full sm:w-auto">
								<SelectDropdown
									value={webConfig.WEB_LOADER_ENGINE}
									options={webLoaderEngineOptions}
									on:change={(e) => (webConfig.WEB_LOADER_ENGINE = e.detail.value)}
								/>
							</div>
						</div>

						<!-- Loader Engine-specific Configuration -->
						{#if webConfig.WEB_LOADER_ENGINE === '' || webConfig.WEB_LOADER_ENGINE === 'safe_web'}
							<div class="flex w-full justify-between items-center" style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
								<div class="self-center text-xs font-medium" style="color: #374151; font-size: 13px;">
									{$i18n.t('Verify SSL Certificate')}
								</div>
								<div class="flex items-center relative">
									<Switch bind:state={webConfig.ENABLE_WEB_LOADER_SSL_VERIFICATION} />
								</div>
							</div>
						{:else if webConfig.WEB_LOADER_ENGINE === 'playwright'}
							<div style="padding: 12px; background: #f9fafb; border-radius: 8px; border: 1px solid rgba(0,0,0,0.06);">
								<div class="flex w-full flex-col" style="gap: 12px;">
									<div>
										<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
											{$i18n.t('Playwright WebSocket URL')}
										</div>

										<div class="flex w-full">
											<div class="flex-1">
												<input
													class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
													type="text"
													placeholder={$i18n.t('Enter Playwright WebSocket URL')}
													bind:value={webConfig.PLAYWRIGHT_WS_URL}
													autocomplete="off"
													style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
												/>
											</div>
										</div>
									</div>

									<div class="mt-2">
										<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
											{$i18n.t('Playwright Timeout (ms)')}
										</div>

										<div class="flex w-full">
											<div class="flex-1">
												<input
													class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
													placeholder={$i18n.t('Enter Playwright Timeout')}
													bind:value={webConfig.PLAYWRIGHT_TIMEOUT}
													autocomplete="off"
													style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
												/>
											</div>
										</div>
									</div>
								</div>
							</div>
						{:else if webConfig.WEB_LOADER_ENGINE === 'firecrawl'}
							<div style="padding: 12px; background: #f9fafb; border-radius: 8px; border: 1px solid rgba(0,0,0,0.06);">
								<div class="flex w-full flex-col" style="gap: 12px;">
									<div>
										<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
											{$i18n.t('Firecrawl API Base URL')}
										</div>

										<div class="flex w-full">
											<div class="flex-1">
												<input
													class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
													type="text"
													placeholder={$i18n.t('Enter Firecrawl API Base URL')}
													bind:value={webConfig.FIRECRAWL_API_BASE_URL}
													autocomplete="off"
													style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
												/>
											</div>
										</div>
									</div>

									<div class="mt-2">
										<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
											{$i18n.t('Firecrawl API Key')}
										</div>

										<SensitiveInput
											placeholder={$i18n.t('Enter Firecrawl API Key')}
											bind:value={webConfig.FIRECRAWL_API_KEY}
										/>
									</div>
								</div>
							</div>
						{:else if webConfig.WEB_LOADER_ENGINE === 'tavily'}
							<div style="padding: 12px; background: #f9fafb; border-radius: 8px; border: 1px solid rgba(0,0,0,0.06);">
								<div class="flex w-full flex-col" style="gap: 12px;">
									<div>
										<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
											{$i18n.t('Tavily Extract Depth')}
										</div>

										<div class="flex w-full">
											<div class="flex-1">
												<input
													class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
													type="text"
													placeholder={$i18n.t('Enter Tavily Extract Depth')}
													bind:value={webConfig.TAVILY_EXTRACT_DEPTH}
													autocomplete="off"
													style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
												/>
											</div>
										</div>
									</div>

									{#if webConfig.WEB_SEARCH_ENGINE !== 'tavily'}
										<div class="mt-2">
											<div class="self-center text-xs font-medium mb-1" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
												{$i18n.t('Tavily API Key')}
											</div>

											<SensitiveInput
												placeholder={$i18n.t('Enter Tavily API Key')}
												bind:value={webConfig.TAVILY_API_KEY}
											/>
										</div>
									{/if}
								</div>
							</div>
						{/if}

						<!-- Youtube Language -->
						<div class="flex w-full justify-between items-center" style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
							<div class="self-center text-xs font-medium" style="color: #374151; font-size: 13px;">
								{$i18n.t('Youtube Language')}
							</div>
							<div class="flex items-center relative" style="flex: 1; max-width: 250px;">
								<input
									class="flex-1 w-full rounded-lg text-sm bg-transparent outline-hidden"
									type="text"
									placeholder={$i18n.t('Enter language codes')}
									bind:value={webConfig.YOUTUBE_LOADER_LANGUAGE}
									autocomplete="off"
									style="background: #f9fafb; border: 1px solid rgba(0,0,0,0.1); border-radius: 6px; padding: 6px 12px; transition: all 0.2s;"
								/>
							</div>
						</div>

						<!-- Youtube Proxy URL -->
						<div class="flex flex-col w-full justify-between" style="padding: 8px 0;">
							<div class="mb-1 text-xs font-medium" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
								{$i18n.t('Youtube Proxy URL')}
							</div>
							<div class="flex items-center relative">
								<input
									class="flex-1 w-full rounded-lg text-sm bg-transparent outline-hidden"
									type="text"
									placeholder={$i18n.t('Enter proxy URL (e.g. https://user:password@host:port)')}
									bind:value={webConfig.YOUTUBE_LOADER_PROXY_URL}
									autocomplete="off"
									style="background: #f9fafb; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
								/>
							</div>
						</div>
					</div>
				</div>
			</div>
		{/if}
	</div>
	<div class="flex justify-end pt-3 text-sm font-medium" style="border-top: 1px solid rgba(0,0,0,0.08); padding-top: 16px;">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-orange-600 hover:bg-orange-700 text-white transition rounded-lg"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>