<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { config } from '$lib/stores';
	import ChartBar from '$lib/components/icons/ChartBar.svelte';

	const i18n = getContext('i18n');

	// List of 12 OpenRouter models as per the customizations
	const openRouterModels = [
		{ id: 'anthropic/claude-sonnet-4', name: 'Claude Sonnet 4', provider: 'Anthropic' },
		{ id: 'google/gemini-2.5-flash', name: 'Gemini 2.5 Flash', provider: 'Google' },
		{ id: 'google/gemini-2.5-pro', name: 'Gemini 2.5 Pro', provider: 'Google' },
		{ id: 'deepseek/deepseek-chat-v3-0324', name: 'DeepSeek Chat v3', provider: 'DeepSeek' },
		{ id: 'anthropic/claude-3.7-sonnet', name: 'Claude 3.7 Sonnet', provider: 'Anthropic' },
		{ id: 'google/gemini-2.5-flash-lite-preview-06-17', name: 'Gemini 2.5 Flash Lite Preview', provider: 'Google' },
		{ id: 'openai/gpt-4.1', name: 'GPT-4.1', provider: 'OpenAI' },
		{ id: 'x-ai/grok-4', name: 'Grok 4', provider: 'X AI' },
		{ id: 'openai/gpt-4o-mini', name: 'GPT-4o Mini', provider: 'OpenAI' },
		{ id: 'openai/o4-mini-high', name: 'O4 Mini High', provider: 'OpenAI' },
		{ id: 'openai/o3', name: 'O3', provider: 'OpenAI' },
		{ id: 'openai/chatgpt-4o-latest', name: 'ChatGPT 4o Latest', provider: 'OpenAI' }
	];

	let loading = true;

	onMount(() => {
		loading = false;
	});
</script>

<div class="flex flex-col h-full justify-between text-sm">
	<div class="overflow-y-scroll scrollbar-hidden h-full">
		<div class="mb-4">
			<div class="flex justify-between items-center text-xs">
				<div class="text-sm font-medium">{$i18n.t('Model Usage Overview')}</div>
			</div>
		</div>

		<div class="text-xs text-gray-600 dark:text-gray-400 mb-4">
			{$i18n.t('Available OpenRouter models for your organization')}
		</div>

		{#if loading}
			<div class="flex justify-center items-center h-64">
				<div class="text-gray-500">{$i18n.t('Loading...')}</div>
			</div>
		{:else}
			<div class="space-y-3">
				{#each openRouterModels as model}
					<div class="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
						<div class="flex-1">
							<div class="flex items-center gap-3">
								<div class="w-10 h-10 flex items-center justify-center rounded-lg bg-gray-200 dark:bg-gray-700">
									<ChartBar className="w-5 h-5 text-gray-600 dark:text-gray-400" />
								</div>
								<div>
									<div class="font-medium text-gray-900 dark:text-gray-100">
										{model.name}
									</div>
									<div class="text-xs text-gray-500 dark:text-gray-400">
										{model.provider} • <code class="text-xs bg-gray-200 dark:bg-gray-700 px-1 rounded">{model.id}</code>
									</div>
								</div>
							</div>
						</div>
						<div class="flex items-center gap-4">
							<div class="text-right">
								<div class="text-xs text-gray-500 dark:text-gray-400">
									{$i18n.t('Status')}
								</div>
								<div class="flex items-center gap-1 mt-1">
									<div class="w-2 h-2 rounded-full bg-green-500"></div>
									<span class="text-xs font-medium text-green-600 dark:text-green-400">
										{$i18n.t('Active')}
									</span>
								</div>
							</div>
						</div>
					</div>
				{/each}
			</div>

			<div class="mt-8 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
				<div class="flex items-start gap-3">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5">
						<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clip-rule="evenodd" />
					</svg>
					<div class="flex-1">
						<h4 class="text-sm font-medium text-blue-900 dark:text-blue-100 mb-1">
							{$i18n.t('Model Access Information')}
						</h4>
						<p class="text-xs text-blue-700 dark:text-blue-300">
							{$i18n.t('These models are configured for your organization through OpenRouter. Access is managed centrally and applies to all users within your organization.')}
						</p>
					</div>
				</div>
			</div>
		{/if}
	</div>
</div>