<script lang="ts">
	import { getContext } from 'svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { marked } from 'marked';

	const i18n = getContext('i18n');

	const featureLabels = {
		web_search: {
			label: $i18n.t('Web Search'),
			description: $i18n.t('Model can search the web for information')
		},
		native_web_search: {
			label: $i18n.t('Native Web Search'),
			description: $i18n.t('Use model built-in web search capability')
		},
		image_generation: {
			label: $i18n.t('Image Generation'),
			description: $i18n.t('Model can generate images based on text prompts')
		},
		code_interpreter: {
			label: $i18n.t('Code Interpreter'),
			description: $i18n.t('Model can execute code and perform calculations')
		}
	};

	export let availableFeatures = ['web_search', 'native_web_search', 'image_generation', 'code_interpreter'];
	export let featureIds: string[] = [];

	// Mutual exclusion helper
	const getDisabledState = (feature: string, currentFeatureIds: string[]): boolean => {
		if (feature === 'web_search' && currentFeatureIds.includes('native_web_search')) {
			return true;
		}
		if (feature === 'native_web_search' && currentFeatureIds.includes('web_search')) {
			return true;
		}
		return false;
	};

	const getTooltipContent = (feature: string, currentFeatureIds: string[]): string => {
		if (feature === 'web_search' && currentFeatureIds.includes('native_web_search')) {
			return $i18n.t('Cannot enable Web Search when Native Web Search is enabled');
		}
		if (feature === 'native_web_search' && currentFeatureIds.includes('web_search')) {
			return $i18n.t('Cannot enable Native Web Search when Web Search is enabled');
		}
		return marked.parse(featureLabels[feature].description) as string;
	};

	const handleFeatureChange = (feature: string, checked: boolean) => {
		if (checked) {
			// Add the feature
			featureIds = [...featureIds, feature];

			// Mutual exclusion: remove the other search option if enabling one
			if (feature === 'web_search') {
				featureIds = featureIds.filter((id) => id !== 'native_web_search');
			} else if (feature === 'native_web_search') {
				featureIds = featureIds.filter((id) => id !== 'web_search');
			}
		} else {
			// Remove the feature
			featureIds = featureIds.filter((id) => id !== feature);
		}
	};
</script>

<div>
	<div class="flex w-full justify-between mb-1">
		<div class=" self-center text-xs font-medium text-gray-500">{$i18n.t('Default Features')}</div>
	</div>
	<div class="flex items-center mt-2 flex-wrap">
		{#each availableFeatures as feature (feature)}
			<div class=" flex items-center gap-2 mr-3 {getDisabledState(feature, featureIds) ? 'opacity-50' : ''}">
				<Checkbox
					state={featureIds.includes(feature) ? 'checked' : 'unchecked'}
					disabled={getDisabledState(feature, featureIds)}
					on:change={(e) => {
						handleFeatureChange(feature, e.detail === 'checked');
					}}
				/>

				<div class=" py-0.5 text-sm capitalize">
					<Tooltip content={getTooltipContent(feature, featureIds)}>
						{$i18n.t(featureLabels[feature].label)}
					</Tooltip>
				</div>
			</div>
		{/each}
	</div>
</div>
