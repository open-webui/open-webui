<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { videoModels } from '$lib/stores';
	import { getVideoModels } from '$lib/apis/videos';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import ModelSettingsLabel from './ModelSettingsLabel.svelte';

	const i18n = getContext<any>('i18n');

	export let videoModelId: string = '';
	export let label = '';
	export let onChange: () => void = () => {};

	let show = false;
	let valueElement: HTMLElement | null = null;

	onMount(async () => {
		if ($videoModels === null) {
			videoModels.set(await getVideoModels(localStorage.token).catch(() => []));
		}
	});

	$: models = $videoModels ?? [];
	$: items = [
		{ value: '', label: $i18n.t('Default') },
		...(videoModelId && !models.some((model) => model.id === videoModelId)
			? [{ value: videoModelId, label: $i18n.t('Unavailable') }]
			: []),
		...models.map((model) => ({
			value: model.id,
			label:
				new Set(models.map((m) => m.connection_id)).size > 1
					? `${model.name} (${model.connection_name})`
					: model.name
		}))
	];
	$: selectedLabel = items.find((item) => item.value === videoModelId)?.label ?? $i18n.t('Default');

	const select = (value: string) => {
		videoModelId = value;
		show = false;
		onChange();
	};
</script>

{#if models.length > 1 || videoModelId}
	<Dropdown anchorElement={valueElement} bind:show>
		<button
			type="button"
			aria-expanded={show}
			class="grid w-full grid-cols-[7rem_minmax(0,1fr)_auto] items-center gap-2 rounded-md px-1 py-1.5 text-left text-xs font-normal disabled:cursor-default sm:grid-cols-[8rem_minmax(0,1fr)_auto]"
		>
			<span class="text-base-600 dark:text-base-400"
				><ModelSettingsLabel
					label={label || $i18n.t('Default video model')}
					description={$i18n.t(
						'Choose the video model used for chats with this model, unless the user picks another.'
					)}
				/></span
			>
			<span bind:this={valueElement} class="min-w-0 truncate text-base-900 dark:text-base-100"
				>{selectedLabel}</span
			>
			<ChevronRight className="size-3 text-base-400" />
		</button>

		<div slot="content">
			<div
				class="flex max-h-64 w-56 max-w-[calc(100vw-2rem)] flex-col gap-0.5 overflow-y-auto rounded-xl border border-base-200 bg-base-0 p-1 text-base-900 shadow-lg dark:border-base-800 dark:bg-base-850 dark:text-base-100"
			>
				{#each items as item (item.value)}
					<button
						type="button"
						class="flex min-h-7 w-full items-center justify-between gap-2 rounded-xl px-2 py-1 text-left text-xs hover:bg-base-50 dark:hover:bg-base-800"
						aria-pressed={item.value === videoModelId}
						on:click={() => select(item.value)}
					>
						<span class="min-w-0 flex-1 truncate">{item.label}</span>
						{#if item.value === videoModelId}<Check
								className="size-3.5 shrink-0 text-base-500 dark:text-base-400"
							/>{/if}
					</button>
				{/each}
			</div>
		</div>
	</Dropdown>
{/if}
