<script lang="ts">
	import { getContext, onMount } from 'svelte';
	const i18n: any = getContext('i18n');

	import { user } from '$lib/stores';

	import XMark from '$lib/components/icons/XMark.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import { getOllamaConfig } from '$lib/apis/ollama';
	import { getOpenAIConfig } from '$lib/apis/openai';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';
	import ManageMultipleOllama from './Manage/ManageMultipleOllama.svelte';
	import ManageMultipleProviderModels from './Manage/ManageMultipleProviderModels.svelte';

	export let show = false;

	type ProviderConnection = {
		idx: number;
		url: string;
		provider: string;
		config: Record<string, any>;
	};
	const MANAGEMENT_PROVIDERS = new Set(['llama.cpp', 'lmstudio']);

	let selected: '' | 'ollama' | 'provider' | null = null;
	let ollamaConfig: any = null;
	let providerConnections: ProviderConnection[] = [];

	$: hasOllamaManagement =
		ollamaConfig?.ENABLE_OLLAMA_API && (ollamaConfig?.OLLAMA_BASE_URLS ?? []).length > 0;
	$: hasProviderManagement = providerConnections.length > 0;

	onMount(async () => {
		if ($user?.role === 'admin') {
			let openaiConfig: any = null;
			await Promise.all([
				(async () => {
					ollamaConfig = await getOllamaConfig(localStorage.token);
				})(),
				(async () => {
					openaiConfig = await getOpenAIConfig(localStorage.token);
				})()
			]);

			providerConnections = openaiConfig?.ENABLE_OPENAI_API
				? (openaiConfig.OPENAI_API_BASE_URLS ?? [])
						.map((url: string, idx: number) => ({
							idx,
							url,
							provider:
								(
									openaiConfig.OPENAI_API_CONFIGS?.[idx] ??
									openaiConfig.OPENAI_API_CONFIGS?.[String(idx)] ??
									openaiConfig.OPENAI_API_CONFIGS?.[url] ??
									{}
								)?.provider ?? '',
							config:
								openaiConfig.OPENAI_API_CONFIGS?.[idx] ??
								openaiConfig.OPENAI_API_CONFIGS?.[String(idx)] ??
								openaiConfig.OPENAI_API_CONFIGS?.[url] ??
								{}
						}))
						.filter((connection: ProviderConnection) =>
							MANAGEMENT_PROVIDERS.has(connection.provider)
						)
				: [];

			const hasOllama =
				ollamaConfig?.ENABLE_OLLAMA_API && (ollamaConfig?.OLLAMA_BASE_URLS ?? []).length > 0;
			const hasProvider = providerConnections.length > 0;

			if (hasOllama) {
				selected = 'ollama';
				return;
			}

			selected = hasProvider ? 'provider' : '';
		}
	});
</script>

<Modal size="sm" bind:show className="bg-white dark:bg-gray-900 rounded-4xl">
	<div>
		<div class=" flex justify-between dark:text-gray-100 px-4 pt-3 pb-1">
			<div class=" text-sm font-medium self-center">
				{$i18n.t('Manage Models')}
			</div>
			<button
				class="self-center rounded-lg p-1 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-4'} />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-3 pb-4 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				{#if selected === ''}
					<div class=" py-5 text-gray-400 text-xs">
						<div>
							{$i18n.t('No inference engine with management support found')}
						</div>
					</div>
				{:else if selected !== null}
					<div class=" flex w-full flex-col">
						<div class=" px-1.5 py-1">
							{#if hasOllamaManagement && hasProviderManagement}
								<div class="mb-2">
									<SettingsSelect
										bind:value={selected}
										className="w-full"
										placeholder={$i18n.t('Select an engine')}
									>
										<option value="ollama">{$i18n.t('Ollama')}</option>
										<option value="provider">{$i18n.t('Model providers')}</option>
									</SettingsSelect>
								</div>
							{/if}
							{#if selected === 'ollama'}
								<ManageMultipleOllama {ollamaConfig} />
							{:else if selected === 'provider'}
								<ManageMultipleProviderModels connections={providerConnections} />
							{/if}
						</div>
					</div>
				{:else}
					<div class=" py-5">
						<Spinner />
					</div>
				{/if}
			</div>
		</div>
	</div>
</Modal>
