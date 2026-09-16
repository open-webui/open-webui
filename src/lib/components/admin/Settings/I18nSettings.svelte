<script lang="ts">
	import { getContext, tick } from 'svelte';
	import LanguageModeSelect from '$lib/components/common/LanguageModeSelect.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import type { I18nEntry } from '$lib/utils/translationDictionary';
	import languages from '$lib/i18n/locales/languages.json';

	const i18n = getContext<any>('i18n');
	export let entries: I18nEntry[] = [];
	let locale =
		languages.find((language) => language.code === $i18n.language)?.code ??
		languages.find((language) => language.code === $i18n.resolvedLanguage)?.code ??
		'en-US';
	let list: HTMLDivElement;
	const fieldClass =
		'block min-h-5 max-h-40 min-w-0 w-full resize-none bg-transparent text-[0.8125rem] leading-5 outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700 [field-sizing:content]';
	const add = async () => {
		if (!entries.length || entries.at(-1)?.content.trim()) {
			entries = [...entries, { content: '', i18n: {} }];
		}
		await tick();
		list.lastElementChild?.querySelector('textarea')?.focus();
	};
</script>

<div class="space-y-1.5">
	<div class="flex min-h-7 flex-wrap items-center justify-between gap-x-2 gap-y-1">
		<div class="text-xs text-gray-600 dark:text-gray-400">{$i18n.t('UI Translations')}</div>
		<div class="ms-auto flex shrink-0 items-center gap-1">
			{#if entries.length}<LanguageModeSelect
					bind:value={locale}
					includeDefault={false}
					className="w-fit"
				/>{/if}
			<Tooltip content={$i18n.t('Add translation')}>
				<button
					type="button"
					aria-label={$i18n.t('Add translation')}
					on:click={add}
					class="flex size-6 items-center justify-center text-gray-400 dark:text-gray-600"
				>
					<Plus className="size-3.5" />
				</button>
			</Tooltip>
		</div>
	</div>
	<div bind:this={list} class="flex flex-col gap-1.5">
		{#each entries as entry, index (entry)}
			<div
				class="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_1.5rem] items-center gap-2 rounded-lg border border-gray-100/40 px-2 py-1 transition focus-within:border-blue-400 dark:border-gray-850/50 dark:focus-within:border-blue-500"
			>
				<textarea
					rows="1"
					bind:value={entry.content}
					aria-label={$i18n.t('Key')}
					placeholder={$i18n.t('Key')}
					class="{fieldClass} text-gray-500 dark:text-gray-400"
				></textarea>
				<textarea
					rows="1"
					value={entry.i18n[locale]?.content ?? ''}
					aria-label={$i18n.t('Value')}
					placeholder={$i18n.t('Value')}
					class="{fieldClass} text-gray-700 dark:text-gray-200"
					on:input={(event) => {
						entry.i18n = { ...entry.i18n, [locale]: { content: event.currentTarget.value } };
					}}
				></textarea>
				<Tooltip content={$i18n.t('Delete')}>
					<button
						type="button"
						aria-label={$i18n.t('Delete')}
						on:click={() => (entries = entries.filter((_, i) => i !== index))}
						class="flex size-6 shrink-0 items-center justify-center text-gray-400 hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
					>
						<XMark className="size-3.5" />
					</button>
				</Tooltip>
			</div>
		{/each}
	</div>
</div>
