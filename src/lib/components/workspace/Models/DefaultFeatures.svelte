<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { marked } from 'marked';

	const i18n: Writable<i18nType> = getContext('i18n');

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

	type Feature = keyof typeof featureLabels;

	export let availableFeatures: string[] = ['web_search', 'image_generation', 'code_interpreter'];
	export let featureIds: string[] = [];

	const getFeatureLabel = (feature: string) => featureLabels[feature as Feature];

	const setFeature = (feature: string, checked: boolean) => {
		if (checked) {
			if (!featureIds.includes(feature)) {
				featureIds = [...featureIds, feature];
			}
		} else {
			featureIds = featureIds.filter((id) => id !== feature);
		}
	};
</script>

<div>
	<div class="mb-1.5 text-xs text-gray-400 dark:text-gray-600">{$i18n.t('Default Features')}</div>
	<div class="grid grid-cols-1 gap-x-5 gap-y-1 sm:grid-cols-2 lg:grid-cols-3">
		{#each availableFeatures as feature}
			<div class="flex min-h-6 items-center gap-2.5">
				<Checkbox
					ariaLabel={$i18n.t(getFeatureLabel(feature).label)}
					state={featureIds.includes(feature) ? 'checked' : 'unchecked'}
					on:change={(e) => {
						setFeature(feature, e.detail === 'checked');
					}}
				/>
				<button
					type="button"
					class="min-w-0 cursor-pointer text-left text-xs text-gray-600 dark:text-gray-400"
					on:click={() => setFeature(feature, !featureIds.includes(feature))}
				>
					<Tooltip
						as="span"
						className="block min-w-0"
						content={marked.parse(getFeatureLabel(feature).description)}
					>
						<span class="block truncate">{$i18n.t(getFeatureLabel(feature).label)}</span>
					</Tooltip>
				</button>
			</div>
		{/each}
	</div>
</div>
