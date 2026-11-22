<script lang="ts" context="module">
	export type MachineOption = { id: string; label: string; device: boolean };
</script>

<script lang="ts">
	import { getContext } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import KeyPill from '$lib/components/common/KeyPill.svelte';
	import Cloud from '$lib/components/icons/Cloud.svelte';
	import Server from '$lib/components/icons/Server.svelte';

	const i18n = getContext<any>('i18n');
	export let options: MachineOption[];
	export let onclose: () => void;
	export let onselect: (id: string) => void;

	let query = '';
	let selectedIndex = 0;

	$: filteredMachines = options.filter((machine) =>
		machine.label.toLowerCase().includes(query.trim().toLowerCase())
	);
	$: if (selectedIndex >= filteredMachines.length)
		selectedIndex = Math.max(0, filteredMachines.length - 1);

	const select = (machine: MachineOption) => {
		onselect(machine.id);
		onclose();
	};

	const handleKeydown = (event: KeyboardEvent) => {
		if (event.isComposing) return;
		if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
			event.preventDefault();
			event.stopPropagation();
			selectedIndex = Math.max(
				0,
				Math.min(filteredMachines.length - 1, selectedIndex + (event.key === 'ArrowDown' ? 1 : -1))
			);
			document
				.getElementById(`terminal-picker-option-${selectedIndex}`)
				?.scrollIntoView({ block: 'nearest' });
		} else if (event.key === 'Enter' && filteredMachines[selectedIndex]) {
			event.preventDefault();
			event.stopPropagation();
			select(filteredMachines[selectedIndex]);
		}
	};
</script>

<Modal
	size="sm"
	ariaLabel={$i18n.t('Select a machine')}
	onRequestClose={onclose}
	className="bg-base-0 dark:bg-base-850 rounded-xl overflow-hidden !border-base-100 dark:!border-base-800 text-base-700 dark:text-base-100 font-normal"
>
	<div class="flex h-10 items-center gap-2 px-3">
		<input
			bind:value={query}
			role="combobox"
			aria-label={$i18n.t('Select a machine')}
			aria-autocomplete="list"
			aria-expanded={filteredMachines.length > 0}
			aria-controls="terminal-picker-options"
			aria-activedescendant={filteredMachines.length
				? `terminal-picker-option-${selectedIndex}`
				: undefined}
			autocomplete="off"
			spellcheck="false"
			placeholder={$i18n.t('Select a machine')}
			class="h-8 min-w-0 flex-1 bg-transparent text-[0.8125rem] font-normal outline-none placeholder:text-base-400 dark:placeholder:text-base-500"
			on:keydown={handleKeydown}
		/>
		<button type="button" aria-label={$i18n.t('Close')} on:click={onclose}>
			<KeyPill text="Esc" />
		</button>
	</div>
	<!-- Earlier wording, kept so i18n:parse does not drop its translations: $i18n.t('Terminals') -->
	<div
		id="terminal-picker-options"
		role="listbox"
		aria-label={$i18n.t('Machines')}
		class="max-h-[min(20rem,60dvh)] overflow-y-auto px-1 pb-1"
	>
		{#each filteredMachines as machine, index (machine.id)}
			<button
				type="button"
				role="option"
				tabindex="-1"
				id="terminal-picker-option-{index}"
				aria-selected={index === selectedIndex}
				class="flex h-[1.6875rem] w-full items-center gap-2 rounded-lg px-2 text-start text-[0.8125rem] font-normal transition-colors duration-75 {index ===
				selectedIndex
					? 'bg-base-100/60 dark:bg-base-800/60'
					: 'hover:bg-base-50/40 dark:hover:bg-base-800/40'}"
				on:mousemove={() => (selectedIndex = index)}
				on:click={() => select(machine)}
			>
				<span class="shrink-0 text-base-500 dark:text-base-400">
					{#if machine.device}
						<Server className="size-3.5" strokeWidth="2" />
					{:else}
						<Cloud className="size-3.5" strokeWidth="2" />
					{/if}
				</span>
				<span class="min-w-0 flex-1 truncate">{machine.label}</span>
			</button>
		{/each}
	</div>
	{#if !filteredMachines.length}
		<div role="status" class="px-3 pb-3 pt-1 text-[0.6875rem] text-base-400 dark:text-base-500">
			{$i18n.t('No machines found')}
		</div>
	{/if}
</Modal>
