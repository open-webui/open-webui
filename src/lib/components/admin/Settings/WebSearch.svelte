<script lang="ts">
	import { getRAGConfig, updateRAGConfig } from '$lib/apis/retrieval';
	import Switch from '$lib/components/common/Switch.svelte';

	import { onMount, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let saveHandler: Function;

	let enableWebSearch = false;

	// Exa powers search result discovery.
	let exaApiKey = '';
	let exaNumResults = 10;
	let exaSearchType = 'auto';
	let exaIncludeDomains = '';
	let exaExcludeDomains = '';

	// Jina Reader powers full-content fetches from URLs.
	let jinaApiKey = '';
	let jinaReaderTokenUsage = 0;
	let jinaReaderViewportWidth = 1280;
	let jinaReaderViewportHeight = 12000;
	let jinaReaderTimeout = 30;
	let loadedJinaApiKey = '';
	let loadedJinaReaderTokenUsage = 0;
	let lastObservedJinaApiKey = '';
	let jinaConfigLoaded = false;

	let webSearchSystemPrompt = '';

	// YouTube loader settings (kept for compatibility)
	let youtubeLoaderLanguage = '';
	let youtubeLoaderProxyUrl = '';

	$: if (jinaConfigLoaded && jinaApiKey !== lastObservedJinaApiKey) {
		// Default to a fresh meter for a new key. Admins can still type an existing
		// usage value after changing the key if they are migrating an already-used key.
		jinaReaderTokenUsage = jinaApiKey === loadedJinaApiKey ? loadedJinaReaderTokenUsage : 0;
		lastObservedJinaApiKey = jinaApiKey;
	}

	const toNumber = (value: unknown, fallback: number) => {
		const parsed = Number(value);
		return Number.isFinite(parsed) ? parsed : fallback;
	};

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
				EXA_SEARCH_NUM_RESULTS: toNumber(exaNumResults, 10),
				EXA_SEARCH_TYPE: exaSearchType,
				EXA_INCLUDE_DOMAINS: includeDomains,
				EXA_EXCLUDE_DOMAINS: excludeDomains,
				JINA_API_KEY: jinaApiKey,
				JINA_READER_TOKEN_USAGE: Math.max(0, Math.floor(toNumber(jinaReaderTokenUsage, 0))),
				JINA_READER_VIEWPORT_WIDTH: Math.max(
					320,
					Math.floor(toNumber(jinaReaderViewportWidth, 1280))
				),
				JINA_READER_VIEWPORT_HEIGHT: Math.max(
					1000,
					Math.floor(toNumber(jinaReaderViewportHeight, 12000))
				),
				JINA_READER_TIMEOUT: Math.max(1, Math.floor(toNumber(jinaReaderTimeout, 30))),
				WEB_SEARCH_SYSTEM_PROMPT: webSearchSystemPrompt,
				YOUTUBE_LOADER_LANGUAGE: youtubeLanguages,
				YOUTUBE_LOADER_PROXY_URL: youtubeLoaderProxyUrl
			}
		});

		if (res) {
			loadedJinaApiKey = jinaApiKey;
			loadedJinaReaderTokenUsage = Math.max(0, Math.floor(toNumber(jinaReaderTokenUsage, 0)));
			lastObservedJinaApiKey = jinaApiKey;
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
			jinaApiKey = res.web.JINA_API_KEY ?? '';
			jinaReaderTokenUsage = res.web.JINA_READER_TOKEN_USAGE ?? 0;
			jinaReaderViewportWidth = res.web.JINA_READER_VIEWPORT_WIDTH ?? 1280;
			jinaReaderViewportHeight = res.web.JINA_READER_VIEWPORT_HEIGHT ?? 12000;
			jinaReaderTimeout = res.web.JINA_READER_TIMEOUT ?? 30;
			loadedJinaApiKey = jinaApiKey;
			loadedJinaReaderTokenUsage = jinaReaderTokenUsage;
			lastObservedJinaApiKey = jinaApiKey;
			jinaConfigLoaded = true;
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
					<div class="rounded-xl border border-gray-100 dark:border-gray-850 p-3 mb-3">
						<div class="mb-2 text-sm font-medium">{$i18n.t('Search Provider: Exa')}</div>
						<div class="mb-2.5 flex w-full flex-col">
							<div class=" self-center text-xs font-medium mb-1">
								<Tooltip content={$i18n.t('Used by web_search to discover pages and snippets')}>
									{$i18n.t('Exa API Key')}
								</Tooltip>
							</div>

							<SensitiveInput
								placeholder={$i18n.t('Enter Exa API Key')}
								bind:value={exaApiKey}
								required
							/>
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

						<div class="flex w-full flex-col">
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
					</div>

					<div class="rounded-xl border border-gray-100 dark:border-gray-850 p-3 mb-3">
						<div class="mb-1 text-sm font-medium">
							{$i18n.t('Content Fetch Provider: Jina Reader')}
						</div>
						<div class="mb-3 text-xs text-gray-500 dark:text-gray-400">
							{$i18n.t(
								'Used by web_fetch to read full page content. Requests use Jina Reader browser mode with retained links, images, media links, ATX headings, and a final 1280×12000 viewport by default.'
							)}
						</div>

						<div class="mb-2.5 flex w-full flex-col">
							<div class=" self-center text-xs font-medium mb-1">
								<Tooltip
									content={$i18n.t('Sent as Authorization: Bearer <key> to https://r.jina.ai/')}
								>
									{$i18n.t('Jina API Key')}
								</Tooltip>
							</div>

							<SensitiveInput
								placeholder={$i18n.t('Enter Jina API Key')}
								bind:value={jinaApiKey}
								required
							/>
						</div>

						<div class="mb-2.5 flex w-full flex-col">
							<div class=" self-center text-xs font-medium mb-1">
								<Tooltip
									content={$i18n.t(
										'Automatically increments from Jina Reader response usage.tokens. Changing the API key resets this value to 0 unless you set it manually before saving.'
									)}
								>
									{$i18n.t('Jina Token Usage')}
								</Tooltip>
							</div>

							<input
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
								type="number"
								placeholder="0"
								bind:value={jinaReaderTokenUsage}
								min="0"
							/>
						</div>

						<div class="mb-2.5 grid grid-cols-1 gap-2 md:grid-cols-3">
							<div>
								<div class=" self-center text-xs font-medium mb-1">
									{$i18n.t('Viewport Width')}
								</div>
								<input
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									type="number"
									bind:value={jinaReaderViewportWidth}
									min="320"
								/>
							</div>
							<div>
								<div class=" self-center text-xs font-medium mb-1">
									{$i18n.t('Viewport Height')}
								</div>
								<input
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									type="number"
									bind:value={jinaReaderViewportHeight}
									min="1000"
								/>
							</div>
							<div>
								<div class=" self-center text-xs font-medium mb-1">
									<Tooltip content={$i18n.t('Sent as X-Timeout in seconds')}>
										{$i18n.t('Timeout')}
									</Tooltip>
								</div>
								<input
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									type="number"
									bind:value={jinaReaderTimeout}
									min="1"
								/>
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
			class="px-3.5 py-1.5 text-sm font-medium bg-book-cloth hover:bg-kraft text-white dark:bg-book-cloth dark:text-white dark:hover:bg-kraft transition-colors duration-200 ease-paper rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
