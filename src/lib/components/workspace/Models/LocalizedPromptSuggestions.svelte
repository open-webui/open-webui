<script lang="ts">
	import { getContext } from 'svelte';
	import PromptSuggestions from './PromptSuggestions.svelte';

	const i18n = getContext<any>('i18n');

	export let promptSuggestions = [];
	export let localizedPromptSuggestions = {};
	export let locale = '';
	export let localeLabel = '';
	export let onChange = () => {};
	export let disabled = false;

	const clone = (value) => JSON.parse(JSON.stringify(value ?? []));

	$: hasCustomLocalePrompts =
		locale !== '' && Array.isArray(localizedPromptSuggestions?.[locale]?.suggestion_prompts);

	$: localePrompts = clone(
		hasCustomLocalePrompts
			? localizedPromptSuggestions[locale].suggestion_prompts
			: promptSuggestions
	);

	const updateLocalePrompts = (suggestions) => {
		localizedPromptSuggestions = {
			...(localizedPromptSuggestions ?? {}),
			[locale]: {
				...(localizedPromptSuggestions?.[locale] ?? {}),
				suggestion_prompts: suggestions
			}
		};
		onChange();
	};

	const useDefault = () => {
		const next = { ...(localizedPromptSuggestions ?? {}) };
		if (next[locale]) {
			next[locale] = { ...next[locale] };
			delete next[locale].suggestion_prompts;
			if (Object.keys(next[locale]).length === 0) {
				delete next[locale];
			}
		}
		localizedPromptSuggestions = next;
		onChange();
	};
</script>

{#if !locale}
	<PromptSuggestions bind:promptSuggestions {disabled} onChange={() => onChange()}>
		<span slot="label"><slot name="label" /></span>
		<svelte:fragment slot="actions"><slot name="language" /></svelte:fragment>
	</PromptSuggestions>
{:else}
	<PromptSuggestions
		{disabled}
		promptSuggestions={localePrompts}
		inherited={!hasCustomLocalePrompts}
		onChange={updateLocalePrompts}
	>
		<svelte:fragment slot="label">
			{#if hasCustomLocalePrompts}
				<button
					title={localeLabel}
					type="button"
					{disabled}
					class="hover:text-gray-900 disabled:opacity-40 dark:hover:text-gray-100"
					on:click={useDefault}
				>
					{$i18n.t('Use default')}
				</button>
			{/if}
		</svelte:fragment>
		<svelte:fragment slot="actions">
			<slot name="language" />
		</svelte:fragment>
	</PromptSuggestions>
{/if}
