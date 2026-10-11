<script lang="ts">
	// Keep keys in nested template expressions visible to i18next-parser.
	// $i18n.t("Translation");

	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { validateDictionary } from '$lib/utils/translationDictionary';
	import Tooltip from './Tooltip.svelte';
	import ArrowUturnLeft from '$lib/components/icons/ArrowUturnLeft.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	const i18n = getContext<any>('i18n');
	export let value: Record<string, string> = {};
	export let source: Record<string, string> = {};
	export let filename = 'translations.json';
	export let onChange = (_value: Record<string, string>) => {};
	export let allowNewKeys = false;
	export let readOnly = false;
	let adding = false;
	let newKey = '';
	const addKey = () => {
		if (readOnly) return;
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
		if (readOnly) return;
		value = { ...value, [key]: text };
		onChange(value);
	};
	const reset = (key: string) => {
		if (readOnly) return;
		const next = { ...value };
		delete next[key];
		value = next;
		onChange(value);
	};
	const importFile = async (event: Event) => {
		if (readOnly) return;
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

<div class="flex min-h-0 flex-1 flex-col gap-1.5">
	<div class="flex min-h-7 flex-wrap items-center justify-between gap-x-2 gap-y-1">
		<div class="text-xs text-gray-600 dark:text-gray-400">{$i18n.t('Translations')}</div>
		<div class="ms-auto flex shrink-0 items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
			<slot name="language" />
			<input
				bind:this={fileInput}
				type="file"
				accept="application/json,.json"
				hidden
				on:change={importFile}
			/>
			<button
				type="button"
				class="hover:text-gray-900 disabled:opacity-40 dark:hover:text-gray-100"
				disabled={readOnly}
				on:click={() => fileInput.click()}>{$i18n.t('Import')}</button
			>
			<button
				type="button"
				class="hover:text-gray-900 disabled:opacity-40 dark:hover:text-gray-100"
				on:click={exportFile}>{$i18n.t('Export')}</button
			>
			{#if allowNewKeys && !readOnly}
				<Tooltip content={$i18n.t('Add translation')}>
					<button
						class="flex size-6 items-center justify-center text-gray-400 dark:text-gray-600"
						type="button"
						aria-label={$i18n.t('Add translation')}
						on:click={() => (adding = !adding)}><Plus className="size-3.5" /></button
					>
				</Tooltip>
			{/if}
		</div>
	</div>
	{#if adding && !readOnly}<div class="flex items-center gap-2 text-xs">
			<input
				class="min-w-0 flex-1 bg-transparent px-2 py-1 text-[0.8125rem] outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700"
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
	<div class="flex items-center gap-2 px-2 py-1 text-xs text-gray-500 dark:text-gray-400">
		<Search className="size-3.5 shrink-0 text-gray-500" />
		<input
			class="min-w-0 w-full bg-transparent py-0.5 text-xs placeholder:text-gray-500 dark:placeholder:text-gray-400 outline-hidden"
			bind:value={query}
			placeholder={$i18n.t('Search')}
			aria-label={$i18n.t('Search translations')}
		/>
		<label class="flex shrink-0 items-center gap-1.5"
			><input type="checkbox" bind:checked={modified} />{$i18n.t('Modified')}</label
		>
	</div>
	<div class="min-h-0 flex-1 overflow-y-auto">
		<div class="flex flex-col gap-1.5">
			{#each keys.slice(page * 50, (page + 1) * 50) as key (key)}
				<div class="flex items-end gap-2 px-2">
					<label class="min-w-0 flex-1 space-y-1">
						<Tooltip
							as="span"
							className="block min-w-0"
							content={key}
							allowHTML={false}
							placement="top-start"
						>
							<span
								class="block whitespace-pre-wrap break-words text-xs text-gray-600 dark:text-gray-400"
								>{source[key] || key}</span
							>
						</Tooltip>
						<textarea
							rows="1"
							readonly={readOnly}
							class="block min-h-7 max-h-40 min-w-0 w-full resize-none rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-500 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-400 dark:focus:border-blue-500 [field-sizing:content]"
							aria-label={key}
							placeholder={$i18n.t('Translation')}
							value={value?.[key] ?? ''}
							on:input={(event) => update(key, event.currentTarget.value)}
						></textarea>
					</label>
					<div class="mb-0.5 w-6 shrink-0">
						{#if !readOnly && Object.hasOwn(value ?? {}, key)}
							<Tooltip content={$i18n.t('Use default')}>
								<button
									type="button"
									class="flex size-6 items-center justify-center text-gray-400 hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300"
									aria-label={`${$i18n.t('Use default')}: ${key}`}
									on:click={() => reset(key)}><ArrowUturnLeft className="size-3.5" /></button
								>
							</Tooltip>
						{/if}
					</div>
				</div>
			{:else}
				<div class="px-2 py-1 text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t('No results found')}
				</div>
			{/each}
		</div>
	</div>
	{#if pages > 1}
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
	{/if}
</div>
