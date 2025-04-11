<script lang="ts">
	import { getRAGConfig, updateRAGConfig } from '$lib/apis/retrieval';
	import Switch from '$lib/components/common/Switch.svelte';

	import { models } from '$lib/stores';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let webConfig = null;
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

	let youtubeLanguage = 'en';
	let youtubeTranslation = null;
	let youtubeProxyUrl = '';

	const submitHandler = async () => {
		// Convert domain filter string to array before sending
		if (webConfig.search.domain_filter_list) {
			webConfig.search.domain_filter_list = webConfig.search.domain_filter_list
				.split(',')
				.map((domain) => domain.trim())
				.filter((domain) => domain.length > 0);
		} else {
			webConfig.search.domain_filter_list = [];
		}

		const res = await updateRAGConfig(localStorage.token, {
			web: webConfig,
			youtube: {
				language: youtubeLanguage.split(',').map((lang) => lang.trim()),
				translation: youtubeTranslation,
				proxy_url: youtubeProxyUrl
			}
		});

		webConfig.search.domain_filter_list = webConfig.search.domain_filter_list.join(', ');
	};

	onMount(async () => {
		const res = await getRAGConfig(localStorage.token);

		if (res) {
			webConfig = res.web;
			// Convert array back to comma-separated string for display
			if (webConfig?.search?.domain_filter_list) {
				webConfig.search.domain_filter_list = webConfig.search.domain_filter_list.join(', ');
			}

			youtubeLanguage = res.youtube.language.join(',');
			youtubeTranslation = res.youtube.translation;
			youtubeProxyUrl = res.youtube.proxy_url;
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
	<div class=" space-y-3 overflow-y-scroll scrollbar-hidden h-full">
		{#if webConfig}
			<div class="">
				<div class="mb-3">
					<div class=" mb-2.5 text-base font-medium">{$i18n.t('General')}</div>

					<hr class=" border-gray-100 dark:border-gray-850 my-2" />

					<div class="  mb-2.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Web Search')}
						</div>
						<div class="flex items-center relative">
							<Switch bind:state={webConfig.search.enabled} />
						</div>
					</div>

					<div class="  mb-2.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Web Search Engine')}
						</div>
						<div class="flex items-center relative">
							<select
								class="dark:bg-gray-900 w-fit pr-8 rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-right"
								bind:value={webConfig.search.engine}
								placeholder={$i18n.t('Select a engine')}
								required
							>
								<option disabled selected value="">{$i18n.t('Select a engine')}</option>
								{#each webSearchEngines as engine}
									<option value={engine}>{engine}</option>
								{/each}
							</select>
						</div>
					</div>

					{#if webConfig.search.engine !== ''}
						{#if webConfig.search.engine === 'searxng'}
							<div class="mb-2.5 flex w-full flex-col">
								<div>
									<div class=" self-center text-xs font-medium mb-1">
										{$i18n.t('Searxng Query URL')}
									</div>

									<div class="flex w-full">
										<div class="flex-1">
											<input
												class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
												type="text"
												placeholder={$i18n.t('Enter Searxng Query URL')}
												bind:value={webConfig.search.searxng_query_url}
												autocomplete="off"
											/>
										</div>
									</div>
								</div>
							</div>
						{:else if webConfig.search.engine === 'google_pse'}
							<div class="mb-2.5 flex w-full flex-col">
								<div>
									<div class=" self-center text-xs font-medium mb-1">
										{$i18n.t('Google PSE API Key')}
									</div>

									<SensitiveInput
										placeholder={$i18n.t('Enter Google PSE API Key')}
										bind:value={webConfig.search.google_pse_api_key}
									/>
								</div>
								<div class="mt-1.5">
									<div class=" self-center text-xs font-medium mb-1">
										{$i18n.t('Google PSE Engine Id')}
									</div>

									<div class="flex w-full">
										<div class="flex-1">
											<input
												class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
												type="text"
												placeholder={$i18n.t('Enter Google PSE Engine Id')}
												bind:value={webConfig.search.google_pse_engine_id}
												autocomplete="off"
											/>
										</div>
									</div>
								</div>
							</div>
						{:else if webConfig.search.engine === 'brave'}
							<div class="mb-2.5 flex w-full flex-col">
								<div>
									<div class=" self-center text-xs font-medium mb-1">
										{$i18n.t('Brave Search API Key')}
									</div>

									<SensitiveInput
										placeholder={$i18n.t('Enter Brave Search API Key')}
										bind:value={webConfig.search.brave_search_api_key}
									/>
								</div>
							</div>
						{:else if webConfig.search.engine === 'kagi'}
							<div class="mb-2.5 flex w-full flex-col">
								<div>
									<div class=" self-center text-xs font-medium mb-1">
										{$i18n.t('Kagi Search API Key')}
									</div>

									<SensitiveInput
										placeholder={$i18n.t('Enter Kagi Search API Key')}
										bind:value={webConfig.search.kagi_search_api_key}
									/>
								</div>
								.
							</div>
						{:else if webConfig.search.engine === 'mojeek'}
							<div class="mb-2.5 flex w-full flex-col">
								<div>
									<div class=" self-center text-xs font-medium mb-1">
										{$i18n.t('Mojeek Search API Key')}
									</div>

									<SensitiveInput
										placeholder={$i18n.t('Enter Mojeek Search API Key')}
										bind:value={webConfig.search.mojeek_search_api_key}
									/>
								</div>
							</div>
						{:else if webConfig.search.engine === 'bocha'}
							<div class="mb-2.5 flex w-full flex-col">
								<div>
									<div class=" self-center text-xs font-medium mb-1">
										{$i18n.t('Bocha Search API Key')}
									</div>

									<SensitiveInput
										placeholder={$i18n.t('Enter Bocha Search API Key')}
										bind:value={webConfig.search.bocha_search_api_key}
									/>
								</div>
							</div>
						{:else if webConfig.search.engine === 'serpstack'}
							<div class="mb-2.5 flex w-full flex-col">
								<div>
									<div class=" self-center text-xs font-medium mb-1">
										{$i18n.t('Serpstack API Key')}
									</div>

									<SensitiveInput
										placeholder={$i18n.t('Enter Serpstack API Key')}
										bind:value={webConfig.search.serpstack_api_key}
									/>
								</div>
							</div>
						{:else if webConfig.search.engine === 'serper'}
							<div class="mb-2.5 flex w-full flex-col">
								<div>
									<div class=" self-center text-xs font-medium mb-1">
										{$i18n.t('Serper API Key')}
									</div>

									<SensitiveInput
										placeholder={$i18n.t('Enter Serper API Key')}
										bind:value={webConfig.search.serper_api_key}
									/>
								</div>
							</div>
						{:else if webConfig.search.engine === 'serply'}
							<div class="mb-2.5 flex w-full flex-col">
								<div>
									<div class=" self-center text-xs font-medium mb-1">
										{$i18n.t('Serply API Key')}
									</div>

									<SensitiveInput
										placeholder={$i18n.t('Enter Serply API Key')}
										bind:value={webConfig.search.serply_api_key}
									/>
								</div>
							</div>
						{:else if webConfig.search.engine === 'searchapi'}
							<div class="mb-2.5 flex w-full flex-col">
								<div>
									<div class=" self-center text-xs font-medium mb-1">
										{$i18n.t('SearchApi API Key')}
									</div>

									<SensitiveInput
										placeholder={$i18n.t('Enter SearchApi API Key')}
										bind:value={webConfig.search.searchapi_api_key}
									/>
								</div>
								<div class="mt-1.5">
									<div class=" self-center text-xs font-medium mb-1">
										{$i18n.t('SearchApi Engine')}
									</div>

									<div class="flex w-full">
										<div class="flex-1">
											<input
												class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
												type="text"
												placeholder={$i18n.t('Enter SearchApi Engine')}
												bind:value={webConfig.search.searchapi_engine}
												autocomplete="off"
											/>
										</div>
									</div>
								</div>
							</div>
						{:else if webConfig.search.engine === 'serpapi'}
							<div class="mb-2.5 flex w-full flex-col">
								<div>
									<div class=" self-center text-xs font-medium mb-1">
										{$i18n.t('SerpApi API Key')}
									</div>

									<SensitiveInput
										placeholder={$i18n.t('Enter SerpApi API Key')}
										bind:value={webConfig.search.serpapi_api_key}
									/>
								</div>
								<div class="mt-1.5">
									<div class=" self-center text-xs font-medium mb-1">
										{$i18n.t('SerpApi Engine')}
									</div>

									<div class="flex w-full">
										<div class="flex-1">
											<input
												class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
												type="text"
												placeholder={$i18n.t('Enter SerpApi Engine')}
												bind:value={webConfig.search.serpapi_engine}
												autocomplete="off"
											/>
										</div>
									</div>
								</div>
							</div>
						{:else if webConfig.search.engine === 'tavily'}
							<div class="mb-2.5 flex w-full flex-col">
								<div>
									<div class=" self-center text-xs font-medium mb-1">
										{$i18n.t('Tavily API Key')}
									</div>

									<SensitiveInput
										placeholder={$i18n.t('Enter Tavily API Key')}
										bind:value={webConfig.search.tavily_api_key}
									/>
								</div>
							</div>
						{:else if webConfig.search.engine === 'jina'}
							<div class="mb-2.5 flex w-full flex-col">
								<div>
									<div class=" self-center text-xs font-medium mb-1">
										{$i18n.t('Jina API Key')}
									</div>

									<SensitiveInput
										placeholder={$i18n.t('Enter Jina API Key')}
										bind:value={webConfig.search.jina_api_key}
									/>
								</div>
							</div>
						{:else if webConfig.search.engine === 'exa'}
							<div class="mb-2.5 flex w-full flex-col">
								<div>
									<div class=" self-center text-xs font-medium mb-1">
										{$i18n.t('Exa API Key')}
									</div>

									<SensitiveInput
										placeholder={$i18n.t('Enter Exa API Key')}
										bind:value={webConfig.search.exa_api_key}
									/>
								</div>
							</div>
						{:else if webConfig.search.engine === 'perplexity'}
							<div>
								<div class=" self-center text-xs font-medium mb-1">
									{$i18n.t('Perplexity API Key')}
								</div>

								<SensitiveInput
									placeholder={$i18n.t('Enter Perplexity API Key')}
									bind:value={webConfig.search.perplexity_api_key}
								/>
							</div>
						{:else if webConfig.search.engine === 'bing'}
							<div class="mb-2.5 flex w-full flex-col">
								<div>
									<div class=" self-center text-xs font-medium mb-1">
										{$i18n.t('Bing Search V7 Endpoint')}
									</div>

									<div class="flex w-full">
										<div class="flex-1">
											<input
												class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
												type="text"
												placeholder={$i18n.t('Enter Bing Search V7 Endpoint')}
												bind:value={webConfig.search.bing_search_v7_endpoint}
												autocomplete="off"
											/>
										</div>
									</div>
								</div>

								<div class="mt-2">
									<div class=" self-center text-xs font-medium mb-1">
										{$i18n.t('Bing Search V7 Subscription Key')}
									</div>

									<SensitiveInput
										placeholder={$i18n.t('Enter Bing Search V7 Subscription Key')}
										bind:value={webConfig.search.bing_search_v7_subscription_key}
									/>
								</div>
							</div>
							{:else if webConfig.search.engine === 'sougou'}
								<div class="mb-2.5 flex w-full flex-col">
									<div>
										<div class=" self-center text-xs font-medium mb-1">
											{$i18n.t('Sougou Search API sID')}
										</div>
	
										<SensitiveInput
											placeholder={$i18n.t('Enter Sougou Search API sID')}
											bind:value={webConfig.search.sougou_api_sid}
										/>
									</div>
								</div>
								<div class="mb-2.5 flex w-full flex-col">
									<div>
										<div class=" self-center text-xs font-medium mb-1">
											{$i18n.t('Sougou Search API SK')}
										</div>
	
										<SensitiveInput
											placeholder={$i18n.t('Enter Sougou Search API SK')}
											bind:value={webConfig.search.sougou_api_sk}
										/>
									</div>
								</div>
						{/if}
					{/if}

					{#if webConfig.search.enabled}
						<div class="mb-2.5 flex w-full flex-col">
							<div class="flex gap-2">
								<div class="w-full">
									<div class=" self-center text-xs font-medium mb-1">
										{$i18n.t('Search Result Count')}
									</div>

									<input
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
										placeholder={$i18n.t('Search Result Count')}
										bind:value={webConfig.search.result_count}
										required
									/>
								</div>

								<div class="w-full">
									<div class=" self-center text-xs font-medium mb-1">
										{$i18n.t('Concurrent Requests')}
									</div>

									<input
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
										placeholder={$i18n.t('Concurrent Requests')}
										bind:value={webConfig.search.concurrent_requests}
										required
									/>
								</div>
							</div>
						</div>

						<div class="mb-2.5 flex w-full flex-col">
							<div class="  text-xs font-medium mb-1">
								{$i18n.t('Domain Filter List')}
							</div>

							<input
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
								placeholder={$i18n.t(
									'Enter domains separated by commas (e.g., example.com,site.org)'
								)}
								bind:value={webConfig.search.domain_filter_list}
							/>
						</div>
					{/if}

					<div class="  mb-2.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
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

					<div class="  mb-2.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Trust Proxy Environment')}
						</div>
						<div class="flex items-center relative">
							<Tooltip
								content={webConfig.search.trust_env
									? $i18n.t(
											'Use proxy designated by http_proxy and https_proxy environment variables to fetch page contents.'
										)
									: $i18n.t(
											'Use no proxy to fetch page contents.'
										)}
							>
								<Switch bind:state={webConfig.search.trust_env} />
							</Tooltip>
						</div>
					</div>
				</div>

				<div class="mb-3">
					<div class=" mb-2.5 text-base font-medium">{$i18n.t('Loader')}</div>

					<hr class=" border-gray-100 dark:border-gray-850 my-2" />

					<div class="  mb-2.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Bypass SSL verification for Websites')}
						</div>
						<div class="flex items-center relative">
							<Switch bind:state={webConfig.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION} />
						</div>
					</div>

					<div class="  mb-2.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Youtube Language')}
						</div>
						<div class="flex items-center relative">
							<input
								class="flex-1 w-full rounded-lg text-sm bg-transparent outline-hidden"
								type="text"
								placeholder={$i18n.t('Enter language codes')}
								bind:value={youtubeLanguage}
								autocomplete="off"
							/>
						</div>
					</div>

					<div class="  mb-2.5 flex flex-col w-full justify-between">
						<div class=" mb-1 text-xs font-medium">
							{$i18n.t('Youtube Proxy URL')}
						</div>
						<div class="flex items-center relative">
							<input
								class="flex-1 w-full rounded-lg text-sm bg-transparent outline-hidden"
								type="text"
								placeholder={$i18n.t('Enter proxy URL (e.g. https://user:password@host:port)')}
								bind:value={youtubeProxyUrl}
								autocomplete="off"
							/>
						</div>
					</div>
				</div>
			</div>
		{/if}
	</div>
	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
