<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { config, visibleControls } from '$lib/stores';
	import ModelSettingsSection from './ModelSettingsSection.svelte';
	import ModelSettingToggle from './ModelSettingToggle.svelte';
	import BuiltinTools from './BuiltinTools.svelte';

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
			description: $i18n.t('settings.admin.models.capabilities.webSearch.description'),
			enabled: $config?.features?.enable_web_search
		},
		image_generation: {
			label: $i18n.t('settings.admin.models.capabilities.imageGeneration.label'),
			description: $i18n.t('settings.admin.models.capabilities.imageGeneration.description'),
			enabled: $config?.features?.enable_image_generation
		},
		code_interpreter: {
			label: $i18n.t('settings.admin.models.capabilities.codeInterpreter.label'),
			description: $i18n.t('settings.admin.models.capabilities.codeInterpreter.description'),
			enabled: $config?.features?.enable_code_interpreter
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
			description: $i18n.t('settings.admin.models.capabilities.memory.description'),
			enabled: $config?.features?.enable_memories
		},
		builtin_tools: {
			label: $i18n.t('settings.admin.models.capabilities.builtinTools.label'),
			description: $i18n.t('settings.admin.models.capabilities.builtinTools.description')
		}
	};

	type Capability = keyof typeof capabilityLabels;

	export let capabilities: Partial<Record<Capability, boolean>> = {};

	export let defaultFeatureIds: string[] = [];
	export let builtinTools: Record<string, boolean> = {};
	export let disabled = false;
	const featureKeys = ['web_search', 'image_generation', 'code_interpreter'] as const;
	$: hasTerminal =
		$config?.features?.enable_terminal_servers || $config?.features?.enable_direct_integrations;
	$: availableCapabilities = (Object.keys(capabilityLabels) as Capability[]).filter(
		(key) =>
			(key !== 'file_context' || capabilities.file_upload) &&
			(key !== 'terminal' || hasTerminal) &&
			(capabilityLabels[key].enabled ?? true)
	);
	$: enabledCapabilityIds = availableCapabilities.filter((key) => capabilities[key]);
	$: availableFeatures = featureKeys.filter((key) => enabledCapabilityIds.includes(key));
	$: enabledDefaultIds = availableFeatures.filter((key) => defaultFeatureIds.includes(key));
	const setDefault = (key: string, enabled: boolean) => {
		defaultFeatureIds = enabled
			? [...new Set([...defaultFeatureIds, key])]
			: defaultFeatureIds.filter((id) => id !== key);
	};
</script>

<div class="space-y-0.5">
	<ModelSettingsSection
		label={$i18n.t('settings.admin.models.capabilities.title')}
		description={$i18n.t(
			'Choose which features are available for this model. The connected model and provider must support them.'
		)}
	>
		<span slot="summary" class="flex min-w-0 items-center gap-1 text-gray-900 dark:text-gray-100">
			<span class="min-w-0 truncate"
				>{enabledCapabilityIds
					.slice(0, 3)
					.map((key) => capabilityLabels[key].label)
					.join(', ') || $i18n.t('None')}</span
			>
			{#if enabledCapabilityIds.length > 3}<span class="shrink-0 text-gray-500"
					>+{enabledCapabilityIds.length - 3}</span
				>{/if}
		</span>
		<div class="grid grid-cols-1 gap-x-6 sm:grid-cols-2 lg:grid-cols-3">
			{#each availableCapabilities.filter((key) => $visibleControls[`model_editor.capabilities.${key}`]) as key}
				<ModelSettingToggle
					label={capabilityLabels[key].label}
					description={capabilityLabels[key].description}
					bind:checked={capabilities[key]}
					{disabled}
				/>
			{/each}
		</div>
	</ModelSettingsSection>

	<!-- Previous DefaultFeatures labels retained for i18n extraction:
	{$i18n.t('settings.admin.models.defaultFeatures.webSearch.label')}
	{$i18n.t('settings.admin.models.defaultFeatures.webSearch.description')}
	{$i18n.t('settings.admin.models.defaultFeatures.imageGeneration.label')}
	{$i18n.t('settings.admin.models.defaultFeatures.imageGeneration.description')}
	{$i18n.t('settings.admin.models.defaultFeatures.codeInterpreter.label')}
	{$i18n.t('settings.admin.models.defaultFeatures.codeInterpreter.description')}
	-->
	{#if availableFeatures.some((key) => $visibleControls[`model_editor.defaults.${key}`])}
		<ModelSettingsSection
			label={$i18n.t('settings.admin.models.defaultFeatures.title')}
			description={$i18n.t('Choose which available features start enabled in new chats.')}
		>
			<span slot="summary" class="flex min-w-0 items-center gap-1 text-gray-900 dark:text-gray-100">
				<span class="min-w-0 truncate"
					>{enabledDefaultIds
						.slice(0, 3)
						.map((key) => capabilityLabels[key].label)
						.join(', ') || $i18n.t('None')}</span
				>
				{#if enabledDefaultIds.length > 3}<span class="shrink-0 text-gray-500"
						>+{enabledDefaultIds.length - 3}</span
					>{/if}
			</span>
			<p class="mb-1 px-1 text-xs text-gray-500 dark:text-gray-400">
				{$i18n.t('Start enabled in new chats')}
			</p>
			<div class="grid grid-cols-1 gap-x-6 sm:grid-cols-2 lg:grid-cols-3">
				{#each availableFeatures.filter((key) => $visibleControls[`model_editor.defaults.${key}`]) as key}
					<ModelSettingToggle
						label={capabilityLabels[key].label}
						checked={defaultFeatureIds.includes(key)}
						{disabled}
						on:change={(e) => setDefault(key, e.detail)}
					/>
				{/each}
			</div>
		</ModelSettingsSection>
	{/if}

	{#if capabilities.builtin_tools}
		<BuiltinTools bind:builtinTools {capabilities} {disabled} />
	{/if}
</div>
