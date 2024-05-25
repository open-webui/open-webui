<script lang="ts">
	import { Collapsible } from 'bits-ui';

	import { setDefaultModels } from '$lib/apis/configs';
	import {
		models,
		showSettings,
		settings,
		user,
		mobile,
		chatType,
		promptOptions,
		selectedChatEmbeddingIndex
	} from '$lib/stores';
	import { onMount, tick, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Selector from './ModelSelector/Selector.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import {getEmbeddingIndex} from "$lib/apis/embedding";

	const i18n = getContext('i18n');

	export let selectedModels = [''];
	export let disabled = false;

	export let showSetDefault = true;

	const saveDefaultModel = async () => {
		const hasEmptyModel = selectedModels.filter((it) => it === '');
		if (hasEmptyModel.length) {
			toast.error($i18n.t('Choose a model before saving...'));
			return;
		}
		settings.set({ ...$settings, models: selectedModels });
		localStorage.setItem('settings', JSON.stringify($settings));

		if ($user.role === 'admin') {
			console.log('setting default models globally');
			await setDefaultModels(localStorage.token, selectedModels.join(','));
		}
		toast.success($i18n.t('Default model updated'));
	};

	const getDesLanguageOption = (type: string) => {
		if (type === 'translate' || type === 'translate_coding') {
			return [
				{value: 'English', label: 'English'},
				{value: 'Chinese', label: 'Chinese'},
				{value: 'Việt', label: 'Tiếng Việt'},
				{value: 'Russian', label: 'Russian'},
				{value: 'Japan', label: 'Japan'},
				{value: 'German', label: 'German'}
			]
		} else if (type === 'translate_ancient') {
			return [
				{value: 'Việt', label: 'Tiếng Việt'},
				{value: 'Hán Việt', label: 'Hán Việt'},
				{value: 'Trung Hoa cổ', label: 'Trung Hoa cổ'},
				{value: 'Hoa', label: 'Hoa'}
			]
		}
		return []
	};

	const loadEmbeddingIndex = async (type: string) => {
		if (type !== 'chat_embedding') {
			return []
		}
		const results = await getEmbeddingIndex()
		selectedChatEmbeddingIndex.set($selectedChatEmbeddingIndex || results?.[0]?.id || 0)
		return results
	}

	let embeddingIndexs = [];

	$: if (selectedModels.length > 0 && $models.length > 0) {
		selectedModels = selectedModels.map((model) =>
			$models.map((m) => m.id).includes(model) ? model : ''
		);
	}

	$: supportedTranslateLangs = getDesLanguageOption($chatType)
	$: (async () => embeddingIndexs = await loadEmbeddingIndex($chatType))()
</script>

<div class="flex flex-col w-full items-center md:items-start">
	{#each selectedModels as selectedModel, selectedModelIdx}
		<div class="flex w-full max-w-fit">
			<div class="overflow-hidden w-full">
				<div class="mr-1 max-w-full">
					<Selector
						placeholder={$i18n.t('Select a model')}
						items={$models
							.filter((model) => model.name !== 'hr')
							.map((model) => ({
								value: model.id,
								label: model.name,
								info: model
							}))}
						bind:value={selectedModel}
					/>
				</div>
			</div>

			{#if selectedModelIdx === 0}
				<div class="  self-center mr-2 disabled:text-gray-600 disabled:hover:text-gray-600">
					<Tooltip content={$i18n.t('Add Model')}>
						<button
							class=" "
							{disabled}
							on:click={() => {
								selectedModels = [...selectedModels, ''];
							}}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="2"
								stroke="currentColor"
								class="size-3.5"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M12 6v12m6-6H6" />
							</svg>
						</button>
					</Tooltip>
				</div>
			{:else}
				<div class="  self-center disabled:text-gray-600 disabled:hover:text-gray-600 mr-2">
					<Tooltip content={$i18n.t('Remove Model')}>
						<button
							{disabled}
							on:click={() => {
								selectedModels.splice(selectedModelIdx, 1);
								selectedModels = selectedModels;
							}}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="2"
								stroke="currentColor"
								class="size-3.5"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 12h-15" />
							</svg>
						</button>
					</Tooltip>
				</div>
			{/if}
		</div>
	{/each}
</div>

<div class="text-left mt-0.5 ml-1 text-[0.7rem] text-gray-500">
	<span> {$i18n.t($chatType)}</span>
	{#if supportedTranslateLangs.length > 0}
		<span class="mx-2">-></span>
		<select class="capitalize rounded-lg py-2 pl-4 pr-10 text-sm dark:text-gray-300 dark:bg-gray-850 disabled:text-gray-500 dark:disabled:text-gray-500 outline-none"
				on:change={(e) => promptOptions.set({...$promptOptions, translate_lang: e.target.value})}
		>
			{#each supportedTranslateLangs as info}
				<option value="{info.value}">{info.label}</option>
			{/each}
		</select>
	{/if}
	{#if embeddingIndexs.length > 0}
		<select class="ml-2 capitalize rounded-lg py-2 pl-4 pr-10 text-sm dark:text-gray-300 dark:bg-gray-850 disabled:text-gray-500 dark:disabled:text-gray-500 outline-none"
				bind:value={$selectedChatEmbeddingIndex}
		>
			{#each embeddingIndexs as info}
				<option value="{info.id}">{info.name}</option>
			{/each}
		</select>
	{/if}
</div>

<!--{#if showSetDefault && !$mobile}-->
<!--	<div class="text-left mt-0.5 ml-1 text-[0.7rem] text-gray-500">-->
<!--&lt;!&ndash;		<button on:click={saveDefaultModel}> {$i18n.t('Set as default')}</button>&ndash;&gt;-->
<!--		<button> {$i18n.t($chatType)}</button>-->
<!--	</div>-->
<!--{/if}-->
