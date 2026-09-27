<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { marked } from 'marked';

	const i18n: Writable<i18nType> = getContext('i18n');

	let capabilityLabels;
	$: capabilityLabels = {
		vision: {
			label: $i18n.t('settings.admin.models.capabilities.vision.label'),
			description: $i18n.t('settings.admin.models.capabilities.vision.description')
		},
		file_upload: {
			label: $i18n.t('settings.admin.models.capabilities.fileUpload.label'),
			description: $i18n.t('settings.admin.models.capabilities.fileUpload.description')
		},
		file_context: {
			label: $i18n.t('settings.admin.models.capabilities.fileContext.label'),
			description: $i18n.t('settings.admin.models.capabilities.fileContext.description')
		},
		web_search: {
			label: $i18n.t('settings.admin.models.capabilities.webSearch.label'),
			description: $i18n.t('settings.admin.models.capabilities.webSearch.description')
		},
		image_generation: {
			label: $i18n.t('settings.admin.models.capabilities.imageGeneration.label'),
			description: $i18n.t('settings.admin.models.capabilities.imageGeneration.description')
		},
		code_interpreter: {
			label: $i18n.t('settings.admin.models.capabilities.codeInterpreter.label'),
			description: $i18n.t('settings.admin.models.capabilities.codeInterpreter.description')
		},
		terminal: {
			label: $i18n.t('settings.admin.models.capabilities.terminal.label'),
			description: $i18n.t('settings.admin.models.capabilities.terminal.description')
		},
		usage: {
			label: $i18n.t('settings.admin.models.capabilities.usage.label'),
			description: $i18n.t('settings.admin.models.capabilities.usage.description')
		},
		citations: {
			label: $i18n.t('settings.admin.models.capabilities.citations.label'),
			description: $i18n.t('settings.admin.models.capabilities.citations.description')
		},
		status_updates: {
			label: $i18n.t('settings.admin.models.capabilities.statusUpdates.label'),
			description: $i18n.t('settings.admin.models.capabilities.statusUpdates.description')
		},
		memory: {
			label: $i18n.t('settings.admin.models.capabilities.memory.label'),
			description: $i18n.t('settings.admin.models.capabilities.memory.description')
		},
		builtin_tools: {
			label: $i18n.t('settings.admin.models.capabilities.builtinTools.label'),
			description: $i18n.t('settings.admin.models.capabilities.builtinTools.description')
		}
	};

	type Capability = keyof typeof capabilityLabels;

	export let capabilities: Partial<Record<Capability, boolean>> = {};

	const setCapability = (capability: Capability, checked: boolean) => {
		capabilities[capability] = checked;
		capabilities = capabilities;
	};

	// Hide file_context when file_upload is disabled
	$: visibleCapabilities = (Object.keys(capabilityLabels) as Capability[]).filter((cap) => {
		if (cap === 'file_context' && !capabilities.file_upload) {
			return false;
		}
		return true;
	});
</script>

<div>
	<div class="mb-1.5 text-xs text-gray-400 dark:text-gray-600">
		{$i18n.t('settings.admin.models.capabilities.title')}
	</div>
	<div class="grid grid-cols-1 gap-x-5 gap-y-1 sm:grid-cols-2 lg:grid-cols-3">
		{#each visibleCapabilities as capability}
			<div class="flex min-h-6 items-center gap-2.5">
				<Checkbox
					ariaLabel={$i18n.t(capabilityLabels[capability].label)}
					state={capabilities[capability] ? 'checked' : 'unchecked'}
					on:change={(e) => {
						setCapability(capability, e.detail === 'checked');
					}}
				/>
				<button
					type="button"
					class="min-w-0 cursor-pointer text-left text-xs text-gray-600 dark:text-gray-400"
					on:click={() => setCapability(capability, !capabilities[capability])}
				>
					<Tooltip
						as="span"
						className="block min-w-0"
						content={marked.parse(capabilityLabels[capability].description)}
					>
						<span class="block truncate">{$i18n.t(capabilityLabels[capability].label)}</span>
					</Tooltip>
				</button>
			</div>
		{/each}
	</div>
</div>
