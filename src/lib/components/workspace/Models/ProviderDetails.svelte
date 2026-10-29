<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18n } from 'i18next';
	import ModelSettingsSection from './ModelSettingsSection.svelte';
	import ModelSettingsLabel from './ModelSettingsLabel.svelte';

	const i18n = getContext<Writable<I18n>>('i18n');
	export let model: unknown = null;

	const record = (value: unknown): Record<string, unknown> =>
		value && typeof value === 'object' && !Array.isArray(value)
			? (value as Record<string, unknown>)
			: {};

	const stringList = (value: unknown): string[] | null =>
		Array.isArray(value) && value.every((item) => typeof item === 'string' && item.trim())
			? [...new Set(value.map((item: string) => item.trim()))]
			: null;

	const tokenLimit = (value: unknown): number | null =>
		typeof value === 'number' && Number.isSafeInteger(value) && value > 0 ? value : null;

	const providerDetails = (model: unknown) => {
		const entry = record(model);
		const source = entry.openai ? record(entry.openai) : entry;
		const architecture = record(source.architecture);
		const provider = record(source.top_provider);

		return {
			inputs: stringList(architecture.input_modalities),
			outputs: stringList(architecture.output_modalities),
			context: tokenLimit(source.context_length),
			providerContext: tokenLimit(provider.context_length),
			maxOutput: tokenLimit(provider.max_completion_tokens),
			parameters: stringList(source.supported_parameters)
		};
	};

	$: details = providerDetails(model);
	$: available = Object.values(details).some((value) => value !== null);
	$: modalityLabels = {
		text: $i18n.t('Text'),
		image: $i18n.t('Image'),
		audio: $i18n.t('Audio'),
		video: $i18n.t('Video'),
		file: $i18n.t('File'),
		embeddings: $i18n.t('Embeddings')
	};
	const modalities = (values: string[] | null, labels: Record<string, string>) =>
		values === null
			? $i18n.t('Not provided')
			: values.map((value) => (Object.hasOwn(labels, value) ? labels[value] : value)).join(', ') ||
				$i18n.t('None reported');
	const tokens = (value: number | null, language: string) =>
		value === null
			? $i18n.t('Not provided')
			: $i18n.t('{{tokens}} tokens', { tokens: value.toLocaleString(language) });
	$: rows = [
		{ label: $i18n.t('Inputs'), value: modalities(details.inputs, modalityLabels) },
		{ label: $i18n.t('Outputs'), value: modalities(details.outputs, modalityLabels) },
		{ label: $i18n.t('Context window'), value: tokens(details.context, $i18n.language) },
		...(details.providerContext !== null && details.providerContext !== details.context
			? [
					{
						label: $i18n.t('Provider context'),
						value: tokens(details.providerContext, $i18n.language)
					}
				]
			: []),
		...(details.maxOutput !== null
			? [{ label: $i18n.t('Max output'), value: tokens(details.maxOutput, $i18n.language) }]
			: []),
		{
			label: $i18n.t('Supported parameters'),
			value:
				details.parameters === null
					? $i18n.t('Not provided')
					: details.parameters.join(', ') || $i18n.t('None reported')
		}
	];
</script>

{#if available}
	<ModelSettingsSection
		label={$i18n.t('Provider details')}
		description={$i18n.t('Reported by the provider.')}
		summary={details.context === null
			? $i18n.t('Available')
			: tokens(details.context, $i18n.language)}
	>
		<dl class="space-y-2 px-1 text-xs font-normal">
			{#each rows as row}
				<div
					class="grid grid-cols-[7rem_minmax(0,1fr)] items-start gap-2 sm:grid-cols-[8rem_minmax(0,1fr)]"
				>
					<dt class="text-gray-600 dark:text-gray-400">{row.label}</dt>
					<dd class="min-w-0 whitespace-normal break-words text-gray-900 dark:text-gray-100">
						{row.value}
					</dd>
				</div>
			{/each}
		</dl>
	</ModelSettingsSection>
{:else}
	<div
		class="grid grid-cols-[7rem_minmax(0,1fr)] items-center gap-2 px-1 py-1.5 text-xs font-normal sm:grid-cols-[8rem_minmax(0,1fr)]"
	>
		<span class="text-gray-600 dark:text-gray-400">
			<ModelSettingsLabel
				label={$i18n.t('Provider details')}
				description={$i18n.t('Reported by the provider.')}
			/>
		</span>
		<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Not provided')}</span>
	</div>
{/if}
