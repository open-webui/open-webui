<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import Select from '$lib/components/common/Select.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import ModelSettingsLabel from './ModelSettingsLabel.svelte';
	import { getTerminalServers, type TerminalServer } from '$lib/apis/terminal';

	const i18n = getContext<any>('i18n');

	export let terminalId: string = '';
	export let label = '';
	export let description = '';
	export let onChange: () => void = () => {};

	let terminals: TerminalServer[] = [];

	onMount(async () => {
		terminals = await getTerminalServers(localStorage.token);
	});
</script>

{#if terminals.length > 0 || terminalId}
	<div
		class="grid min-h-7 grid-cols-[7rem_minmax(0,1fr)] items-center gap-2 px-1 text-xs font-normal text-gray-600 dark:text-gray-400 sm:grid-cols-[8rem_minmax(0,1fr)]"
	>
		<ModelSettingsLabel
			label={label || $i18n.t('Default terminal')}
			description={description ||
				$i18n.t('Choose the terminal server selected by default for chats with this model.')}
		/>
		<Select
			bind:value={terminalId}
			items={[
				{ value: '', label: $i18n.t('None') },
				...(terminalId && !terminals.some((terminal) => terminal.id === terminalId)
					? [{ value: terminalId, label: $i18n.t('Unavailable') }]
					: []),
				...terminals.map((terminal) => ({
					value: terminal.id,
					label: terminal.name || terminal.id
				}))
			]}
			triggerClass="flex w-fit max-w-full min-w-0 items-center gap-1 bg-transparent px-0.5 text-left text-xs font-normal text-gray-900 dark:text-gray-100"
			onChange={() => onChange()}
		>
			<svelte:fragment slot="trigger" let:selectedLabel>
				<span class="sr-only">{label || $i18n.t('Default terminal')}: </span>
				<span class="truncate">{selectedLabel}</span>
				<ChevronDown className="size-3 shrink-0" />
			</svelte:fragment>
			<svelte:fragment slot="item" let:item let:selected>
				<span class="min-w-0 flex-1 truncate text-left">{item.label}</span>
				{#if selected}<Check className="size-3 shrink-0" />{/if}
			</svelte:fragment>
		</Select>
	</div>
{:else}
	<p class="px-1 py-1 text-xs text-gray-500 dark:text-gray-400">
		{$i18n.t('No terminal servers available')}
	</p>
{/if}
