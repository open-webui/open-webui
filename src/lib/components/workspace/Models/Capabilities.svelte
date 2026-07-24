<script lang="ts">
	import { getContext } from 'svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { marked } from 'marked';

	const i18n = getContext('i18n');

	const capabilityLabels = {
		vision: {
			label: $i18n.t('Vision'),
			description: $i18n.t('Model accepts image inputs')
		},
		file_upload: {
			label: $i18n.t('File Upload'),
			description: $i18n.t('Model accepts file inputs')
		},
		file_context: {
			label: $i18n.t('File Context'),
			description: $i18n.t('Inject file content into conversation context')
		},
		web_search: {
			label: $i18n.t('Web Search'),
			description: $i18n.t('Model can search the web for information')
		},
		image_generation: {
			label: $i18n.t('Image Generation'),
			description: $i18n.t('Model can generate images based on text prompts')
		},
		code_interpreter: {
			label: $i18n.t('Code Interpreter'),
			description: $i18n.t('Model can execute code and perform calculations')
		},
		terminal: {
			label: $i18n.t('Terminal'),
			description: $i18n.t(
				'Model can access Open Terminal for command execution and file management'
			)
		},
		usage: {
			label: $i18n.t('Usage'),
			description: $i18n.t(
				'Sends `stream_options: { include_usage: true }` in the request.\nSupported providers will return token usage information in the response when set.'
			)
		},
		citations: {
			label: $i18n.t('Citations'),
			description: $i18n.t('Displays citations in the response')
		},
		status_updates: {
			label: $i18n.t('Status Updates'),
			description: $i18n.t('Displays status updates (e.g., web search progress) in the response')
		},
		builtin_tools: {
			label: $i18n.t('Builtin Tools'),
			description: $i18n.t(
				'Automatically inject system tools in native function calling mode (e.g., timestamps, memory, chat history, notes, etc.)'
			)
		},
		memory: {
			label: $i18n.t('Memory'),
			description: $i18n.t('Inject stored memories into the conversation context')
		}
	};

	export let capabilities: {
		file_context?: boolean;
		vision?: boolean;
		file_upload?: boolean;
		web_search?: boolean;
		image_generation?: boolean;
		code_interpreter?: boolean;
		terminal?: boolean;
		usage?: boolean;
		citations?: boolean;
		status_updates?: boolean;
		builtin_tools?: boolean;
		memory?: boolean;
	} = {};

	// Hide file_context when file_upload is disabled
	$: visibleCapabilities = Object.keys(capabilityLabels).filter((cap) => {
		if (cap === 'file_context' && !capabilities.file_upload) {
			return false;
		}
		return true;
	});
</script>

<div>
	<div class="mb-1.5 text-xs text-gray-400 dark:text-gray-600">{$i18n.t('Capabilities')}</div>
	<div class="grid grid-cols-1 gap-x-5 gap-y-1 sm:grid-cols-2 lg:grid-cols-3">
		{#each visibleCapabilities as capability}
			<div class="flex min-h-6 items-center justify-between gap-2.5">
				<div class="min-w-0 text-xs text-gray-600 dark:text-gray-400">
					<Tooltip content={marked.parse(capabilityLabels[capability].description)}>
						<span class="truncate">{$i18n.t(capabilityLabels[capability].label)}</span>
					</Tooltip>
				</div>
				<Checkbox
					state={capabilities[capability] ? 'checked' : 'unchecked'}
					on:change={(e) => {
						capabilities[capability] = e.detail === 'checked';
					}}
				/>
			</div>
		{/each}
	</div>
</div>
