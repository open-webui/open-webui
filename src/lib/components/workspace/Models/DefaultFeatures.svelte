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
	<div class="flex w-full justify-between mb-1">
		<div class=" self-center text-xs font-medium text-gray-500">{$i18n.t('Default Features')}</div>
	</div>
	<div class="flex items-center mt-2 flex-wrap">
		{#each availableFeatures as feature}
			<div class=" flex items-center gap-2 mr-3">
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

				<div class=" py-0.5 text-sm capitalize">
					<Tooltip content={marked.parse(featureLabels[feature].description)}>
						{$i18n.t(featureLabels[feature].label)}
					</Tooltip>
				</div>
			</div>
		{/each}
	</div>
</div>
