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
		image_generation: {
			label: $i18n.t('Image Generation'),
			description: $i18n.t('Model can generate images based on text prompts')
		},
		code_interpreter: {
			label: $i18n.t('Code Interpreter'),
			description: $i18n.t('Model can execute code and perform calculations')
		}
	};

	export let availableFeatures = ['web_search', 'image_generation', 'code_interpreter'];
	export let featureIds = [];
</script>

<div>
	<div class="mb-1.5 text-xs text-gray-400 dark:text-gray-600">{$i18n.t('Default Features')}</div>
	<div class="grid grid-cols-1 gap-x-5 gap-y-1 sm:grid-cols-3">
		{#each availableFeatures as feature}
			<div class="flex min-h-6 items-center justify-between gap-2.5">
				<div class="min-w-0 text-xs text-gray-600 dark:text-gray-400">
					<Tooltip content={marked.parse(featureLabels[feature].description)}>
						<span class="truncate">{$i18n.t(featureLabels[feature].label)}</span>
					</Tooltip>
				</div>
				<Checkbox
					state={featureIds.includes(feature) ? 'checked' : 'unchecked'}
					on:change={(e) => {
						if (e.detail === 'checked') {
							featureIds = [...featureIds, feature];
						} else {
							featureIds = featureIds.filter((id) => id !== feature);
						}
					}}
				/>
			</div>
		{/each}
	</div>
</div>
