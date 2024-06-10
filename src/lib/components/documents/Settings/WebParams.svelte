<script lang="ts">
	import { getRAGConfig, updateRAGConfig } from '$lib/apis/rag';
	import Switch from '$lib/components/common/Switch.svelte';

	import { documents, models } from '$lib/stores';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let webConfig = null;
	let webSearchEngines = ['searxng', 'google_pse', 'brave', 'serpstack', 'serper', 'serply'];

	let youtubeLanguage = 'en';
	let youtubeTranslation = null;

	const submitHandler = async () => {
		const res = await updateRAGConfig(localStorage.token, {
			web: webConfig,
			youtube: {
				language: youtubeLanguage.split(',').map((lang) => lang.trim()),
				translation: youtubeTranslation
			}
		});
	};

	onMount(async () => {
		const res = await getRAGConfig(localStorage.token);

		if (res) {
			webConfig = res.web;

			youtubeLanguage = res.youtube.language.join(',');
			youtubeTranslation = res.youtube.translation;
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
	<div class=" space-y-3 pr-1.5 overflow-y-scroll h-full max-h-[22rem]">
		{#if webConfig}
			<div>
				<div class=" mb-1 text-sm font-medium">
					{$i18n.t('Web Search')}
				</div>

				<div>
					<div class=" py-0.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Enable Web Search')}
						</div>

						<Switch bind:state={webConfig.search.enabled} />
					</div>
				</div>

				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">{$i18n.t('Web Search Engine')}</div>
					<div class="flex items-center relative">
						<select
							class="dark:bg-gray-900 w-fit pr-8 rounded px-2 p-1 text-xs bg-transparent outline-none text-right"
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
					<div class="mt-1.5">
						{#if webConfig.search.engine === 'searxng'}
							<div>
								<div class=" self-center text-xs font-medium mb-1">
									{$i18n.t('Searxng Query URL')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
											type="text"
											placeholder={$i18n.t('Enter Searxng Query URL')}
											bind:value={webConfig.search.searxng_query_url}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>
						{:else if webConfig.search.engine === 'google_pse'}
							<div>
								<div class=" self-center text-xs font-medium mb-1">
									{$i18n.t('Google PSE API Key')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
											type="text"
											placeholder={$i18n.t('Enter Google PSE API Key')}
											bind:value={webConfig.search.google_pse_api_key}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>
							<div class="mt-1.5">
								<div class=" self-center text-xs font-medium mb-1">
									{$i18n.t('Google PSE Engine Id')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
											type="text"
											placeholder={$i18n.t('Enter Google PSE Engine Id')}
											bind:value={webConfig.search.google_pse_engine_id}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>
						{:else if webConfig.search.engine === 'brave'}
							<div>
								<div class=" self-center text-xs font-medium mb-1">
									{$i18n.t('Brave Search API Key')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
											type="text"
											placeholder={$i18n.t('Enter Brave Search API Key')}
											bind:value={webConfig.search.brave_search_api_key}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>
						{:else if webConfig.search.engine === 'serpstack'}
							<div>
								<div class=" self-center text-xs font-medium mb-1">
									{$i18n.t('Serpstack API Key')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
											type="text"
											placeholder={$i18n.t('Enter Serpstack API Key')}
											bind:value={webConfig.search.serpstack_api_key}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>
						{:else if webConfig.search.engine === 'serper'}
							<div>
								<div class=" self-center text-xs font-medium mb-1">
									{$i18n.t('Serper API Key')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
											type="text"
											placeholder={$i18n.t('Enter Serper API Key')}
											bind:value={webConfig.search.serper_api_key}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>
						{/if}
					</div>
				{/if}

				{#if webConfig.search.enabled}
					<div class="mt-2 flex gap-2 mb-1">
						<div class="w-full">
							<div class=" self-center text-xs font-medium mb-1">
								{$i18n.t('Search Result Count')}
							</div>

							<input
								class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
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
								class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
								placeholder={$i18n.t('Concurrent Requests')}
								bind:value={webConfig.search.concurrent_requests}
								required
							/>
						</div>
					</div>
				{/if}
			</div>

			<hr class=" dark:border-gray-850 my-2" />

			<div>
				<div class=" mb-1 text-sm font-medium">
					{$i18n.t('Web Loader Settings')}
				</div>

				<div>
					<div class=" py-0.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Bypass SSL verification for Websites')}
						</div>

						<button
							class="p-1 px-3 text-xs flex rounded transition"
							on:click={() => {
								webConfig.ssl_verification = !webConfig.ssl_verification;
								submitHandler();
							}}
							type="button"
						>
							{#if webConfig.ssl_verification === true}
								<span class="ml-2 self-center">{$i18n.t('On')}</span>
							{:else}
								<span class="ml-2 self-center">{$i18n.t('Off')}</span>
							{/if}
						</button>
					</div>
				</div>

				<div class=" mt-2 mb-1 text-sm font-medium">
					{$i18n.t('Youtube Loader Settings')}
				</div>

				<div>
					<div class=" py-0.5 flex w-full justify-between">
						<div class=" w-20 text-xs font-medium self-center">{$i18n.t('Language')}</div>
						<div class=" flex-1 self-center">
							<input
								class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
								type="text"
								placeholder={$i18n.t('Enter language codes')}
								bind:value={youtubeLanguage}
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
			class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
