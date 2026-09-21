<script lang="ts">
	import { getContext } from 'svelte';
	import PromptSuggestions from './PromptSuggestions.svelte';

	const i18n = getContext<any>('i18n');

	export let promptSuggestions = [];
	export let localizedPromptSuggestions = {};
	export let locale = '';
	export let localeLabel = '';
	export let onChange = () => {};

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
	<PromptSuggestions bind:promptSuggestions onChange={() => onChange()}>
		<span slot="label"></span>
		<svelte:fragment slot="actions"><slot name="language" /></svelte:fragment>
	</PromptSuggestions>
{:else}
	<PromptSuggestions
		promptSuggestions={localePrompts}
		inherited={!hasCustomLocalePrompts}
		onChange={updateLocalePrompts}
	>
		<span
			slot="label"
			title={localeLabel}
			class="flex flex-wrap items-center gap-x-3 gap-y-1 text-[0.6875rem] text-gray-400 dark:text-gray-600"
		>
			{#if hasCustomLocalePrompts}
				<button
					type="button"
					class="text-gray-500 transition hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
					aria-label={$i18n.t('Use default')}
					on:click={useDefault}
				>
					{$i18n.t('Use default')}
				</button>
			{/if}
		</span>
		<svelte:fragment slot="actions">
			<slot name="language" />
		</svelte:fragment>
	</PromptSuggestions>
{/if}
