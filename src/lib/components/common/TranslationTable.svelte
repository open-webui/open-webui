<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { validateDictionary } from '$lib/utils/translationDictionary';
	import Tooltip from './Tooltip.svelte';
	import ArrowUturnLeft from '$lib/components/icons/ArrowUturnLeft.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	const i18n = getContext<any>('i18n');
	export let value: Record<string, string> = {};
	export let source: Record<string, string> = {};
	export let filename = 'translations.json';
	export let onChange = (_value: Record<string, string>) => {};
	export let allowNewKeys = false;
	let adding = false;
	let newKey = '';
	const addKey = () => {
		if (newKey.trim()) {
			update(newKey.trim(), value?.[newKey.trim()] ?? '');
			query = newKey.trim();
			modified = false;
			adding = false;
			newKey = '';
		}
	};
	let query = '';
	let modified = false;
	let page = 0;
	let fileInput: HTMLInputElement;
	const exportFile = () => {
		const data = Object.fromEntries(Object.entries(value ?? {}).filter(([, text]) => text.trim()));
		const url = URL.createObjectURL(
			new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
		);
		const link = document.createElement('a');
		link.href = url;
		link.download = filename;
		link.click();
		setTimeout(() => URL.revokeObjectURL(url), 1000);
	};
	$: keys = [...new Set([...Object.keys(source), ...Object.keys(value ?? {})])]
		.filter(
			(key) =>
				(!modified || value?.[key]?.trim()) &&
				`${key} ${source[key] ?? ''} ${value?.[key] ?? ''}`
					.toLocaleLowerCase()
					.includes(query.toLocaleLowerCase())
		)
		.sort();
	$: (query, modified, (page = 0));
	$: pages = Math.max(1, Math.ceil(keys.length / 50));
	$: if (page >= pages) page = pages - 1;
	const update = (key: string, text: string) => {
		value = { ...value, [key]: text };
		onChange(value);
	};
	const reset = (key: string) => {
		const next = { ...value };
		delete next[key];
		value = next;
		onChange(value);
	};
	const importFile = async (event: Event) => {
		const input = event.currentTarget as HTMLInputElement;
		try {
			if (input.files?.[0]) {
				value = {
					...value,
					...validateDictionary(JSON.parse(await input.files[0].text()), source)
				};
				onChange(value);
			}
		} catch (error) {
			toast.error(String(error));
		}
		input.value = '';
	};
</script>

<div class="flex min-h-0 flex-1 flex-col gap-2">
	<div class="flex flex-wrap items-center gap-3 text-xs">
		<slot name="language" />
		<input
			bind:this={fileInput}
			type="file"
			accept="application/json,.json"
			hidden
			on:change={importFile}
		/>
		<button type="button" on:click={() => fileInput.click()}>{$i18n.t('Import')}</button>
		<button type="button" on:click={exportFile}>{$i18n.t('Export')}</button>
		{#if allowNewKeys}<Tooltip content={$i18n.t('Add translation')}
				><button
					class="flex size-6 items-center justify-center"
					type="button"
					aria-label={$i18n.t('Add translation')}
					on:click={() => (adding = !adding)}><Plus className="size-3.5" /></button
				></Tooltip
			>{/if}
	</div>
	{#if adding}<div class="flex items-center gap-2 text-xs">
			<input
				class="min-w-0 flex-1 rounded-lg border border-gray-200 bg-transparent px-2 py-1.5 dark:border-gray-800"
				aria-label={$i18n.t('Translation key')}
				placeholder={$i18n.t('Translation key')}
				bind:value={newKey}
				on:keydown={(event) => {
					if (event.key === 'Enter') {
						event.preventDefault();
						addKey();
					}
				}}
			/><button
				type="button"
				class="flex size-7 items-center justify-center"
				aria-label={$i18n.t('Add')}
				on:click={addKey}><Plus className="size-4" /></button
			>
		</div>{/if}
	<div class="flex items-center gap-3 text-xs">
		<input
			class="min-w-0 flex-1 rounded-lg border border-gray-200 bg-transparent px-2 py-1.5 outline-hidden dark:border-gray-800"
			bind:value={query}
			placeholder={$i18n.t('Search')}
			aria-label={$i18n.t('Search translations')}
		/>
		<label class="flex shrink-0 items-center gap-1.5"
			><input type="checkbox" bind:checked={modified} />{$i18n.t('Modified')}</label
		>
	</div>
	<div class="min-h-0 flex-1 overflow-y-auto">
		<div
			class="sticky top-0 z-10 hidden grid-cols-[minmax(0,1fr)_minmax(0,1fr)_1.5rem] gap-3 border-b border-gray-100 bg-white py-2 text-xs text-gray-500 dark:border-gray-800 dark:bg-gray-900 sm:grid"
		>
			<span>{$i18n.t('Original')}</span><span>{$i18n.t('Translation')}</span>
		</div>
		{#each keys.slice(page * 50, (page + 1) * 50) as key (key)}
			<div
				class="grid grid-cols-[minmax(0,1fr)_1.5rem] items-start gap-2 border-b border-gray-100 py-2 dark:border-gray-800 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_1.5rem] sm:gap-3"
			>
				<div class="col-span-2 min-w-0 text-xs sm:col-span-1">
					<div class="break-words">{key}</div>
					{#if source[key] && source[key] !== key}<div class="mt-1 break-words text-gray-500">
							{source[key]}
						</div>{/if}
				</div>
				<textarea
					rows="2"
					class="w-full min-w-0 resize-y rounded-md border border-gray-100 bg-transparent px-2 py-1 text-xs outline-hidden focus:border-gray-400 dark:border-gray-800"
					aria-label={key}
					placeholder={source[key] || key}
					value={value?.[key] ?? ''}
					on:input={(event) => update(key, event.currentTarget.value)}
				></textarea>
				<Tooltip content={$i18n.t('Use default')}
					><button
						type="button"
						class="flex size-6 items-center justify-center disabled:opacity-30"
						aria-label={`${$i18n.t('Use default')}: ${key}`}
						disabled={!Object.hasOwn(value ?? {}, key)}
						on:click={() => reset(key)}><ArrowUturnLeft className="size-3.5" /></button
					></Tooltip
				>
			</div>
		{/each}
		{#if !keys.length}<div class="py-6 text-center text-xs text-gray-500">
				{$i18n.t('No results found')}
			</div>{/if}
	</div>
	<div class="flex items-center justify-end gap-3 text-xs text-gray-500">
		<span>{page + 1} / {pages}</span>
		<button
			type="button"
			class="flex size-7 items-center justify-center disabled:opacity-30"
			aria-label={$i18n.t('Previous')}
			disabled={page === 0}
			on:click={() => page--}><ChevronLeft className="size-4" /></button
		>
		<button
			type="button"
			class="flex size-7 items-center justify-center disabled:opacity-30"
			aria-label={$i18n.t('Next')}
			disabled={page + 1 >= pages}
			on:click={() => page++}><ChevronRight className="size-4" /></button
		>
	</div>
</div>
