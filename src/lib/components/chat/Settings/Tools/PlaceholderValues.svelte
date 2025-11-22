<script lang="ts">
	import { getContext } from 'svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let serverName: string = '';
	export let serverId: string = '';
	export let placeholders: string[] = [];
	export let values: { [key: string]: string } = {};
	export let onChange: (values: { [key: string]: string }) => void = () => {};

	// Initialize values if not set
	$: if (placeholders && !Object.keys(values).length) {
		values = placeholders.reduce((acc, placeholder) => {
			acc[placeholder] = '';
			return acc;
		}, {} as { [key: string]: string });
	}

	const handleValueChange = (placeholder: string, value: string) => {
		values[placeholder] = value;
		onChange(values);
	};
</script>

{#if placeholders && placeholders.length > 0}
	<div class="flex flex-col gap-2 p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
		<div class="flex items-center justify-between">
			<div class="font-medium text-sm">{serverName}</div>
			{#if serverId}
				<div class="text-xs text-gray-500">{serverId}</div>
			{/if}
		</div>

		<div class="flex flex-col gap-2">
			{#each placeholders as placeholder}
				<div class="flex flex-col gap-1">
					<label for={`${serverId}-${placeholder}`} class="text-xs text-gray-600 dark:text-gray-400">
						{placeholder}
					</label>
					<SensitiveInput
						id={`${serverId}-${placeholder}`}
						value={values[placeholder] || ''}
						on:input={(e) => handleValueChange(placeholder, e.target.value)}
						placeholder={$i18n.t(`Enter value for {{placeholder}}`, { placeholder })}
						required={false}
					/>
				</div>
			{/each}
		</div>

		<div class="text-xs text-gray-500 mt-1">
			<Tooltip
				content={$i18n.t(
					'These values will be used to replace placeholders in the server headers (e.g., {{{{PLACEHOLDER_NAME}}}})'
				)}
			>
				<span class="underline cursor-help">{$i18n.t('What are placeholders?')}</span>
			</Tooltip>
		</div>
	</div>
{/if}
