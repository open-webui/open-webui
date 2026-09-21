<script lang="ts">
	import { getContext } from 'svelte';
	import { resolveLocalizedString } from '$lib/utils/localizedContent';
	const i18n = getContext<any>('i18n');
	export let value = '';
	export let translations: Record<string, Record<string, string>> = {};
	export let locale = '';
	export let field = 'name';
	export let placeholder = '';
	export let className = 'w-full bg-transparent text-sm outline-hidden';
	export let multiline = false;
	export let rows = 3;
	export let required = false;
	export let disabled = false;
	export let showControls = true;
	$: translated = translations?.[locale]?.[field] ?? '';
	$: fallback = resolveLocalizedString(value, translations, locale, field);
	const update = (next: string) => {
		if (!locale) {
			value = next;
			return;
		}
		const entry = { ...translations?.[locale] };
		if (next.trim()) entry[field] = next;
		else delete entry[field];
		const nextTranslations = { ...translations };
		if (Object.keys(entry).length) nextTranslations[locale] = entry;
		else delete nextTranslations[locale];
		translations = nextTranslations;
	};
</script>

<div class="min-w-0 flex-1">
	{#if multiline}
		<textarea
			class={className}
			{rows}
			value={locale ? translated : value}
			placeholder={locale ? fallback || placeholder : placeholder}
			aria-label={placeholder || field}
			required={required && !locale}
			{disabled}
			on:input={(e) => update(e.currentTarget.value)}
		></textarea>
	{:else}
		<input
			class={className}
			value={locale ? translated : value}
			placeholder={locale ? fallback || placeholder : placeholder}
			aria-label={placeholder || field}
			required={required && !locale}
			{disabled}
			on:input={(e) => update(e.currentTarget.value)}
		/>
	{/if}
	{#if locale && showControls && (translated || fallback)}
		<div
			class="mt-1 flex flex-wrap items-center gap-3 text-[0.6875rem] text-gray-400 dark:text-gray-600"
		>
			{#if translated}<button
					type="button"
					class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
					{disabled}
					on:click={() => update('')}>{$i18n.t('Use default')}</button
				>
			{:else if fallback}<button
					type="button"
					class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
					{disabled}
					on:click={() => update(fallback)}>{$i18n.t('Copy default')}</button
				>{/if}
		</div>
	{/if}
</div>
