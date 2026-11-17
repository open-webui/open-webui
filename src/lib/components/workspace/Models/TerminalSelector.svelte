<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import ModelSettingsLabel from './ModelSettingsLabel.svelte';
	import { getTerminalServers, type TerminalServer } from '$lib/apis/terminal';

	const i18n = getContext<any>('i18n');

	export let terminalId: string = '';
	export let label = '';
	export let description = '';
	export let onChange: () => void = () => {};

	let terminals: TerminalServer[] = [];
	let show = false;
	let valueElement: HTMLElement | null = null;

	onMount(async () => {
		terminals = await getTerminalServers(localStorage.token);
	});

	$: items = [
		{ value: '', label: $i18n.t('None') },
		...(terminalId && !terminals.some((terminal) => terminal.id === terminalId)
			? [{ value: terminalId, label: $i18n.t('Unavailable') }]
			: []),
		...terminals.map((terminal) => ({
			value: terminal.id,
			label: terminal.name || terminal.id
		}))
	];
	$: selectedLabel = items.find((item) => item.value === terminalId)?.label ?? $i18n.t('None');

	const select = (value: string) => {
		terminalId = value;
		show = false;
		onChange();
	};
</script>

{#if terminals.length > 0 || terminalId}
	<Dropdown anchorElement={valueElement} bind:show>
		<button
			type="button"
			aria-expanded={show}
			class="grid w-full grid-cols-[7rem_minmax(0,1fr)_auto] items-center gap-2 rounded-md px-1 py-1.5 text-left text-xs font-normal disabled:cursor-default sm:grid-cols-[8rem_minmax(0,1fr)_auto]"
		>
			<span class="text-gray-600 dark:text-gray-400"
				><ModelSettingsLabel
					label={label || $i18n.t('Default terminal')}
					description={description ||
						$i18n.t('Choose the terminal server selected by default for chats with this model.')}
				/></span
			>
			<span bind:this={valueElement} class="min-w-0 truncate text-gray-900 dark:text-gray-100"
				>{selectedLabel}</span
			>
			<ChevronRight className="size-3 text-gray-400" />
		</button>

		<div slot="content">
			<div
				class="flex max-h-64 w-56 max-w-[calc(100vw-2rem)] flex-col gap-0.5 overflow-y-auto rounded-xl border border-gray-200 bg-white p-1 text-gray-900 shadow-lg dark:border-gray-800 dark:bg-gray-850 dark:text-gray-100"
			>
				{#each items as item (item.value)}
					<button
						type="button"
						class="flex min-h-7 w-full items-center justify-between gap-2 rounded-xl px-2 py-1 text-left text-xs hover:bg-gray-50 dark:hover:bg-gray-800"
						aria-pressed={item.value === terminalId}
						on:click={() => select(item.value)}
					>
						<span class="min-w-0 flex-1 truncate">{item.label}</span>
						{#if item.value === terminalId}<Check
								className="size-3.5 shrink-0 text-gray-500 dark:text-gray-400"
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
		<span class="text-gray-600 dark:text-gray-400"
			><ModelSettingsLabel
				label={label || $i18n.t('Default terminal')}
				description={description ||
					$i18n.t('Choose the terminal server selected by default for chats with this model.')}
			/></span
		>
		<span class="truncate text-gray-500 dark:text-gray-400"
			>{$i18n.t('No terminal servers available')}</span
		>
	</div>
{/if}
