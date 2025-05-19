<script lang="ts">
	import { getContext } from 'svelte';
	const i18n: any = getContext('i18n');

	import Plus from '$lib/components/icons/Plus.svelte';
	import Minus from '$lib/components/icons/Minus.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { KeySelectionStrategy } from '$lib/utils/apiKeySelection';

	// Props
	export let apiKeys: string[] = [''];
	export let keyWeights: Record<string, number> = {};
	export let selectionStrategy: string = KeySelectionStrategy.RANDOM;
	export let placeholder: string = 'API Key';

	// Local state
	let newKey = '';

	// Add a new API key
	function addApiKey() {
		if (newKey.trim()) {
			apiKeys = [...apiKeys, newKey.trim()];
			newKey = '';
		}
	}

	// Remove an API key
	function removeApiKey(index: number) {
		apiKeys = apiKeys.filter((_, i) => i !== index);

		// If we removed all keys, add an empty one
		if (apiKeys.length === 0) {
			apiKeys = [''];
		}
	}

	// Update a key weight
	function updateKeyWeight(key: string, weight: number) {
		keyWeights = {
			...keyWeights,
			[key]: weight
		};
	}

	// Get the display name for a strategy
	function getStrategyDisplayName(strategy: string): string {
		switch (strategy) {
			case KeySelectionStrategy.RANDOM:
				return i18n.t('Random');
			case KeySelectionStrategy.ROUND_ROBIN:
				return i18n.t('Round Robin');
			case KeySelectionStrategy.LEAST_RECENTLY_USED:
				return i18n.t('Least Recently Used');
			case KeySelectionStrategy.WEIGHTED:
				return i18n.t('Weighted');
			default:
				return strategy;
		}
	}
</script>

<div class="flex flex-col w-full">
	<div class="mb-1 flex justify-between">
		<div class="text-xs text-gray-500">{i18n.t('API Keys')}</div>
		<div class="text-xs text-gray-500">
			<span class="mr-2">{i18n.t('Selection Strategy')}:</span>
			<select
				class="bg-transparent outline-hidden text-xs"
				bind:value={selectionStrategy}
			>
				<option value={KeySelectionStrategy.RANDOM}>{getStrategyDisplayName(KeySelectionStrategy.RANDOM)}</option>
				<option value={KeySelectionStrategy.ROUND_ROBIN}>{getStrategyDisplayName(KeySelectionStrategy.ROUND_ROBIN)}</option>
				<option value={KeySelectionStrategy.LEAST_RECENTLY_USED}>{getStrategyDisplayName(KeySelectionStrategy.LEAST_RECENTLY_USED)}</option>
				<option value={KeySelectionStrategy.WEIGHTED}>{getStrategyDisplayName(KeySelectionStrategy.WEIGHTED)}</option>
			</select>
		</div>
	</div>

	{#if apiKeys.length > 0}
		<div class="flex flex-col gap-2">
			{#each apiKeys as apiKey, index}
				<div class="flex gap-2 items-center">
					<div class="flex-1">
						<SensitiveInput
							inputClassName="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
							bind:value={apiKeys[index]}
							placeholder={placeholder}
						/>
					</div>

					{#if selectionStrategy === KeySelectionStrategy.WEIGHTED}
						<div class="w-16">
							<Tooltip content={i18n.t('Weight')}>
								<input
									type="number"
									min="1"
									class="w-full text-sm bg-transparent outline-hidden text-center"
									value={keyWeights[apiKey] || 1}
									on:input={(e) => {
										// Handle the input event safely
										if (e.target && 'value' in e.target) {
											const value = String(e.target.value);
											updateKeyWeight(apiKey, parseInt(value) || 1);
										}
									}}
								/>
							</Tooltip>
						</div>
					{/if}

					<button
						type="button"
						class="shrink-0"
						on:click={() => removeApiKey(index)}
						disabled={apiKeys.length === 1 && !apiKeys[0]}
					>
						<Minus strokeWidth="2" className="size-3.5" />
					</button>
				</div>
			{/each}
		</div>
	{/if}

	<div class="flex items-center mt-2">
		<input
			class="w-full py-1 text-sm rounded-lg bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
			bind:value={newKey}
			placeholder={i18n.t('Add a new API key')}
		/>

		<div>
			<button
				type="button"
				on:click={addApiKey}
			>
				<Plus className="size-3.5" strokeWidth="2" />
			</button>
		</div>
	</div>

	<div class="text-xs text-gray-500 mt-2">
		{#if selectionStrategy === KeySelectionStrategy.RANDOM}
			{i18n.t('Random: Selects a random API key for each request')}
		{:else if selectionStrategy === KeySelectionStrategy.ROUND_ROBIN}
			{i18n.t('Round Robin: Cycles through API keys in sequence')}
		{:else if selectionStrategy === KeySelectionStrategy.LEAST_RECENTLY_USED}
			{i18n.t('Least Recently Used: Selects the key that was used least recently')}
		{:else if selectionStrategy === KeySelectionStrategy.WEIGHTED}
			{i18n.t('Weighted: Selects keys based on their assigned weights')}
		{/if}
	</div>
</div>
