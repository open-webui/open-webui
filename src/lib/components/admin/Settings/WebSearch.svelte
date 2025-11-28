<script lang="ts">
	import { getRAGConfig, updateRAGConfig } from '$lib/apis/retrieval';
	import Switch from '$lib/components/common/Switch.svelte';

	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	// Exa-only configuration
	let enableWebSearch = false;
	let exaApiKey = '';
	let exaNumResults = 10;
	let exaSearchType = 'auto';
	let exaIncludeDomains = '';
	let exaExcludeDomains = '';
	let exaMaxCharacters = 10000;
	let exaLivecrawl = 'fallback';
	let webSearchSystemPrompt = '';

	// YouTube loader settings (kept for compatibility)
	let youtubeLoaderLanguage = '';
	let youtubeLoaderProxyUrl = '';

	const submitHandler = async () => {
		// Convert domain strings to arrays
		const includeDomains = exaIncludeDomains
			.split(',')
			.map((d) => d.trim())
			.filter((d) => d.length > 0);
		const excludeDomains = exaExcludeDomains
			.split(',')
			.map((d) => d.trim())
			.filter((d) => d.length > 0);
		const youtubeLanguages = youtubeLoaderLanguage
			.split(',')
			.map((l) => l.trim())
			.filter((l) => l.length > 0);

		const res = await updateRAGConfig(localStorage.token, {
			web: {
				ENABLE_WEB_SEARCH: enableWebSearch,
				EXA_API_KEY: exaApiKey,
				EXA_SEARCH_NUM_RESULTS: exaNumResults,
				EXA_SEARCH_TYPE: exaSearchType,
				EXA_INCLUDE_DOMAINS: includeDomains,
				EXA_EXCLUDE_DOMAINS: excludeDomains,
				EXA_CONTENTS_MAX_CHARACTERS: exaMaxCharacters,
				EXA_CONTENTS_LIVECRAWL: exaLivecrawl,
				WEB_SEARCH_SYSTEM_PROMPT: webSearchSystemPrompt,
				YOUTUBE_LOADER_LANGUAGE: youtubeLanguages,
				YOUTUBE_LOADER_PROXY_URL: youtubeLoaderProxyUrl
			}
		});

		if (res) {
			toast.success($i18n.t('Settings saved successfully'));
		}
	};

	onMount(async () => {
		const res = await getRAGConfig(localStorage.token);

		if (res && res.web) {
			enableWebSearch = res.web.ENABLE_WEB_SEARCH ?? false;
			exaApiKey = res.web.EXA_API_KEY ?? '';
			exaNumResults = res.web.EXA_SEARCH_NUM_RESULTS ?? 10;
			exaSearchType = res.web.EXA_SEARCH_TYPE ?? 'auto';
			exaIncludeDomains = (res.web.EXA_INCLUDE_DOMAINS ?? []).join(', ');
			exaExcludeDomains = (res.web.EXA_EXCLUDE_DOMAINS ?? []).join(', ');
			exaMaxCharacters = res.web.EXA_CONTENTS_MAX_CHARACTERS ?? 10000;
			exaLivecrawl = res.web.EXA_CONTENTS_LIVECRAWL ?? 'fallback';
			webSearchSystemPrompt = res.web.WEB_SEARCH_SYSTEM_PROMPT ?? '';
			youtubeLoaderLanguage = (res.web.YOUTUBE_LOADER_LANGUAGE ?? []).join(', ');
			youtubeLoaderProxyUrl = res.web.YOUTUBE_LOADER_PROXY_URL ?? '';
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
		<div class="">
			<div class="mb-3">
				<div class=" mb-2.5 text-base font-medium">{$i18n.t('Web Search')}</div>

				<hr class=" border-gray-100 dark:border-gray-850 my-2" />

				<div class="  mb-2.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Enable Web Search')}
					</div>
					<div class="flex items-center relative">
						<Switch bind:state={enableWebSearch} />
					</div>
				</div>

				{#if enableWebSearch}
					<div class="mb-2.5 flex w-full flex-col">
						<div>
							<div class=" self-center text-xs font-medium mb-1">
								{$i18n.t('Exa API Key')}
							</div>

							<SensitiveInput
								placeholder={$i18n.t('Enter Exa API Key')}
								bind:value={exaApiKey}
								required
							/>
						</div>
					</div>

					<div class="mb-2.5 flex w-full flex-col">
						<div class="flex gap-2">
							<div class="w-full">
								<div class=" self-center text-xs font-medium mb-1">
									{$i18n.t('Search Results Count')}
								</div>

								<input
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									type="number"
									placeholder={$i18n.t('Number of results')}
									bind:value={exaNumResults}
									min="1"
									max="50"
								/>
							</div>

							<div class="w-full">
								<div class=" self-center text-xs font-medium mb-1">
									{$i18n.t('Search Type')}
								</div>

								<select
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									bind:value={exaSearchType}
								>
									<option value="auto">{$i18n.t('Auto')}</option>
									<option value="neural">{$i18n.t('Neural')}</option>
									<option value="keyword">{$i18n.t('Keyword')}</option>
								</select>
							</div>
						</div>
					</div>

					<div class="mb-2.5 flex w-full flex-col">
						<div>
							<div class=" self-center text-xs font-medium mb-1">
								<Tooltip
									content={$i18n.t('Only search results from these domains will be included')}
								>
									{$i18n.t('Include Domains')}
								</Tooltip>
							</div>

							<input
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
								type="text"
								placeholder={$i18n.t(
									'Enter domains separated by commas (e.g., example.com, site.org)'
								)}
								bind:value={exaIncludeDomains}
							/>
						</div>
					</div>

					<div class="mb-2.5 flex w-full flex-col">
						<div>
							<div class=" self-center text-xs font-medium mb-1">
								<Tooltip content={$i18n.t('Search results from these domains will be excluded')}>
									{$i18n.t('Exclude Domains')}
								</Tooltip>
							</div>

							<input
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
								type="text"
								placeholder={$i18n.t('Enter domains separated by commas')}
								bind:value={exaExcludeDomains}
							/>
						</div>
					</div>

					<div class="mb-2.5 flex w-full flex-col">
						<div class="flex gap-2">
							<div class="w-full">
								<div class=" self-center text-xs font-medium mb-1">
									<Tooltip content={$i18n.t('Maximum characters to fetch from each page')}>
										{$i18n.t('Max Characters per Page')}
									</Tooltip>
								</div>

								<input
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									type="number"
									placeholder="10000"
									bind:value={exaMaxCharacters}
									min="1000"
									max="50000"
								/>
							</div>

							<div class="w-full">
								<div class=" self-center text-xs font-medium mb-1">
									<Tooltip content={$i18n.t('How to handle fetching fresh content from URLs')}>
										{$i18n.t('Live Crawl Mode')}
									</Tooltip>
								</div>

								<select
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									bind:value={exaLivecrawl}
								>
									<option value="never">{$i18n.t('Never (cached only)')}</option>
									<option value="fallback">{$i18n.t('Fallback (try cache first)')}</option>
									<option value="always">{$i18n.t('Always (live crawl)')}</option>
								</select>
							</div>
						</div>
					</div>

					<div class="mb-2.5 flex w-full flex-col">
						<div>
							<div class=" self-center text-xs font-medium mb-1">
								<Tooltip
									content={$i18n.t(
										'System prompt added to guide the model on when and how to use web search tools'
									)}
								>
									{$i18n.t('Web Search System Prompt')}
								</Tooltip>
							</div>

							<textarea
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden resize-y"
								rows="6"
								placeholder={$i18n.t('Enter system prompt for web search...')}
								bind:value={webSearchSystemPrompt}
							></textarea>
						</div>
					</div>
				{/if}
			</div>

			<div class="mb-3">
				<div class=" mb-2.5 text-base font-medium">{$i18n.t('YouTube Loader')}</div>

				<hr class=" border-gray-100 dark:border-gray-850 my-2" />

				<div class="  mb-2.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Youtube Language')}
					</div>
					<div class="flex items-center relative">
						<input
							class="flex-1 w-full rounded-lg text-sm bg-transparent outline-hidden"
							type="text"
							placeholder={$i18n.t('Enter language codes (e.g., en, es, fr)')}
							bind:value={youtubeLoaderLanguage}
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
							bind:value={youtubeLoaderProxyUrl}
							autocomplete="off"
						/>
					</div>
				</div>
			</div>
		</div>
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
