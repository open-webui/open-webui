<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import {
		getToolValvesSpecById,
		getUserValvesSpecById as getToolUserValvesSpec
	} from '$lib/apis/tools';
	import {
		getFunctionValvesSpecById,
		getUserValvesSpecById as getFunctionUserValvesSpec
	} from '$lib/apis/functions';
	import { valveTranslationSource } from '$lib/utils/localizedContent';
	import TranslationTable from '$lib/components/common/TranslationTable.svelte';
	const i18n = getContext<any>('i18n');
	export let id = '';
	export let kind: 'tool' | 'function';
	export let locale: string;
	export let translations: Record<string, Record<string, string>> = {};
	let fields: Record<string, string> = {};
	let loadError = false;
	const headerFields = ['name', 'description'];
	$: source = fields;
	$: values = Object.fromEntries(
		Object.entries(translations?.[locale] ?? {}).filter(([key]) => !headerFields.includes(key))
	);
	const load = async () => {
		if (!id) return;
		loadError = false;
		const loaders =
			kind === 'tool'
				? [getToolValvesSpecById, getToolUserValvesSpec]
				: [getFunctionValvesSpecById, getFunctionUserValvesSpec];
		const results = await Promise.allSettled(
			loaders.map((loader) => loader(localStorage.token, id))
		);
		fields = Object.assign(
			{},
			...results.map((result, index) => {
				if (result.status === 'rejected') {
					loadError = true;
					return {};
				}
				return valveTranslationSource(result.value, index ? 'user_valves' : 'valves');
			})
		);
	};
	const changed = (next: Record<string, string>) => {
		translations = {
			...translations,
			[locale]: {
				...Object.fromEntries(
					Object.entries(translations?.[locale] ?? {}).filter(([key]) => headerFields.includes(key))
				),
				...next
			}
		};
	};
	onMount(load);
</script>

{#if loadError}<div class="mb-2 text-xs text-red-500" role="alert">
		{$i18n.t('Failed to load valves')}<button type="button" class="ms-2 underline" on:click={load}
			>{$i18n.t('Retry')}</button
		>
	</div>{/if}
<TranslationTable
	value={values}
	{source}
	filename={`${kind}-${id}-${locale}.json`}
	onChange={changed}
	allowNewKeys
/>
