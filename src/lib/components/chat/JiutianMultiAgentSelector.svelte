<script lang="ts">
	import { models, showSettings, settings, user, mobile, config } from '$lib/stores';
	import { onMount, tick, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getJiutianConfig, getJiutianModels } from '$lib/apis/jiutian';
	import Tooltip from '../common/Tooltip.svelte';
	import Switch from '../common/Switch.svelte';

	const i18n = getContext('i18n');

	export let selectedModels = [''];
	export let disabled = false;
	export let isMultiAgentMode = false;

	let jiutianConfig = null;
	let jiutianModels = [];
	let loading = false;

	// 加载九天平台配置和模型
	const loadJiutianData = async () => {
		if (!localStorage.token) return;
		
		loading = true;
		try {
			// 获取九天平台配置
			jiutianConfig = await getJiutianConfig(localStorage.token);
			
			// 获取九天平台模型列表
			const modelsResponse = await getJiutianModels(localStorage.token);
			jiutianModels = modelsResponse?.data || [];
		} catch (error) {
			console.error('Failed to load Jiutian data:', error);
			toast.error($i18n.t('Failed to load Jiutian platform data'));
		} finally {
			loading = false;
		}
	};

	// 切换多智能体模式
	const toggleMultiAgentMode = () => {
		isMultiAgentMode = !isMultiAgentMode;
		if (isMultiAgentMode) {
			// 切换到多智能体模式时，确保至少有两个模型
			if (selectedModels.length < 2) {
				selectedModels = [...selectedModels, ''];
			}
		} else {
			// 切换到单模型模式时，只保留第一个模型
			selectedModels = [selectedModels[0] || ''];
		}
	};

	// 添加模型
	const addModel = () => {
		selectedModels = [...selectedModels, ''];
	};

	// 移除模型
	const removeModel = (index: number) => {
		selectedModels.splice(index, 1);
		selectedModels = selectedModels;
		
		// 确保多智能体模式下至少有两个模型
		if (isMultiAgentMode && selectedModels.length < 2) {
			selectedModels = [...selectedModels, ''];
		}
	};

	onMount(() => {
		loadJiutianData();
	});

	// 监听多智能体模式变化
	$: if (isMultiAgentMode && selectedModels.length < 2) {
		selectedModels = [...selectedModels, ''];
	}
</script>

<div class="flex flex-col w-full items-start space-y-3">
	<!-- 多智能体模式开关 -->
	<div class="flex items-center justify-between w-full">
		<div class="flex items-center space-x-2">
			<span class="text-sm font-medium text-gray-700 dark:text-gray-300">
				{$i18n.t('Multi-Agent Mode')}
			</span>
			<Tooltip content={$i18n.t('Enable multiple AI agents to collaborate on responses')}>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1.5"
					stroke="currentColor"
					class="w-4 h-4 text-gray-400"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9 5.25h.008v.008H12v-.008z"
					/>
				</svg>
			</Tooltip>
		</div>
		<Switch bind:state={isMultiAgentMode} on:change={toggleMultiAgentMode} {disabled} />
	</div>

	<!-- 九天平台状态指示器 -->
	{#if loading}
		<div class="flex items-center space-x-2 text-sm text-gray-500">
			<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-900 dark:border-white"></div>
			<span>{$i18n.t('Loading Jiutian platform...')}</span>
		</div>
	{:else if jiutianConfig?.enabled}
		<div class="flex items-center space-x-2 text-sm text-green-600 dark:text-green-400">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				stroke-width="1.5"
				stroke="currentColor"
				class="w-4 h-4"
			>
				<path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
			</svg>
			<span>{$i18n.t('Jiutian Platform Connected')}</span>
		</div>
	{:else}
		<div class="flex items-center space-x-2 text-sm text-red-600 dark:text-red-400">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				stroke-width="1.5"
				stroke="currentColor"
				class="w-4 h-4"
			>
				<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
			</svg>
			<span>{$i18n.t('Jiutian Platform Not Available')}</span>
		</div>
	{/if}

	<!-- 模型选择器列表 -->
	<div class="w-full space-y-2">
		{#each selectedModels as selectedModel, selectedModelIdx}
			<div class="flex w-full items-center space-x-2">
				<!-- 模型选择下拉框 -->
				<div class="flex-1">
					<select
						bind:value={selectedModel}
						{disabled}
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
					>
						<option value="">{$i18n.t('Select a model')}</option>
						
						<!-- 九天平台模型 -->
						{#if isMultiAgentMode && jiutianModels.length > 0}
							<optgroup label="{$i18n.t('Jiutian Platform Models')}">
								{#each jiutianModels as model}
									<option value={model.id}>{model.name}</option>
								{/each}
							</optgroup>
						{/if}
						
						<!-- 常规模型 -->
						<optgroup label="{$i18n.t('Available Models')}">
							{#each $models as model}
								<option value={model.id}>{model.name}</option>
							{/each}
						</optgroup>
					</select>
				</div>

				<!-- 添加/删除按钮 -->
				{#if isMultiAgentMode}
					{#if selectedModelIdx === 0}
						<Tooltip content={$i18n.t('Add Model')}>
							<button
								class="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 disabled:opacity-50"
								{disabled}
								on:click={addModel}
								aria-label="Add Model"
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke-width="2"
									stroke="currentColor"
									class="w-5 h-5"
								>
									<path stroke-linecap="round" stroke-linejoin="round" d="M12 6v12m6-6H6" />
								</svg>
							</button>
						</Tooltip>
					{:else}
						<Tooltip content={$i18n.t('Remove Model')}>
							<button
								class="p-2 text-gray-500 hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400 disabled:opacity-50"
								{disabled}
								on:click={() => removeModel(selectedModelIdx)}
								aria-label="Remove Model"
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke-width="2"
									stroke="currentColor"
									class="w-5 h-5"
								>
									<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 12h-15" />
								</svg>
							</button>
						</Tooltip>
					{/if}
				{/if}
			</div>
		{/each}
	</div>

	<!-- 多智能体模式说明 -->
	{#if isMultiAgentMode}
		<div class="w-full p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
			<div class="flex items-start space-x-2">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1.5"
					stroke="currentColor"
					class="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z"
					/>
				</svg>
				<div class="text-sm text-blue-800 dark:text-blue-200">
					<p class="font-medium mb-1">{$i18n.t('Multi-Agent Collaboration')}</p>
					<p>{$i18n.t('Multiple AI models will work together to provide comprehensive responses. Each model will contribute its unique perspective and expertise.')}</p>
				</div>
			</div>
		</div>
	{/if}
</div>