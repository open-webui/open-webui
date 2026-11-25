<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import ModelSettingsLabel from './ModelSettingsLabel.svelte';
	import { getMachines, type MachineServer } from '$lib/apis/machines';

	const i18n = getContext<any>('i18n');

	export let machineId: string = '';
	export let label = '';
	export let description = '';
	export let onChange: () => void = () => {};

	let machineList: MachineServer[] = [];
	let show = false;
	let valueElement: HTMLElement | null = null;

	onMount(async () => {
		machineList = await getMachines(localStorage.token);
	});

	$: items = [
		{ value: '', label: $i18n.t('None') },
		...(machineId && !machineList.some((machine) => machine.id === machineId)
			? [{ value: machineId, label: $i18n.t('Unavailable') }]
			: []),
		...machineList.map((machine) => ({
			value: machine.id,
			label: machine.name || machine.id
		}))
	];
	$: selectedLabel = items.find((item) => item.value === machineId)?.label ?? $i18n.t('None');

	const select = (value: string) => {
		machineId = value;
		show = false;
		onChange();
	};
</script>

{#if machineList.length > 0 || machineId}
	<Dropdown anchorElement={valueElement} bind:show>
		<button
			type="button"
			aria-expanded={show}
			class="grid w-full grid-cols-[7rem_minmax(0,1fr)_auto] items-center gap-2 rounded-md px-1 py-1.5 text-left text-xs font-normal disabled:cursor-default sm:grid-cols-[8rem_minmax(0,1fr)_auto]"
		>
			<span class="text-base-600 dark:text-base-400"
				><ModelSettingsLabel
					label={label || $i18n.t('Default machine')}
					description={description ||
						$i18n.t('Choose the machine selected by default for chats with this model.')}
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
						aria-pressed={item.value === machineId}
						on:click={() => select(item.value)}
					>
						<span class="min-w-0 flex-1 truncate">{item.label}</span>
						{#if item.value === machineId}<Check
								className="size-3.5 shrink-0 text-base-500 dark:text-base-400"
							/>{/if}
					</button>
				{/each}
			</div>
		</div>
	</Dropdown>
{:else}
	<div
		class="grid grid-cols-[7rem_minmax(0,1fr)_auto] items-center gap-2 px-1 py-1.5 text-xs font-normal sm:grid-cols-[8rem_minmax(0,1fr)_auto]"
	>
		<span class="text-base-600 dark:text-base-400"
			><ModelSettingsLabel
				label={label || $i18n.t('Default machine')}
				description={description ||
					$i18n.t('Choose the machine selected by default for chats with this model.')}
			/></span
		>
		<span class="truncate text-base-500 dark:text-base-400">{$i18n.t('No machines available')}</span
		>
	</div>
{/if}
