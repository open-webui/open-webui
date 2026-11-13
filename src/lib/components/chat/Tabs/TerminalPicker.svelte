<script lang="ts" context="module">
	export type TerminalOption = { id: string; label: string; device: boolean };
</script>

<script lang="ts">
	import { getContext } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import KeyPill from '$lib/components/common/KeyPill.svelte';
	import Cloud from '$lib/components/icons/Cloud.svelte';
	import Server from '$lib/components/icons/Server.svelte';

	const i18n = getContext<any>('i18n');
	export let terminals: TerminalOption[];
	export let onclose: () => void;
	export let onselect: (id: string) => void;

	let query = '';
	let selectedIndex = 0;

	$: filteredTerminals = terminals.filter((terminal) =>
		terminal.label.toLowerCase().includes(query.trim().toLowerCase())
	);
	$: if (selectedIndex >= filteredTerminals.length)
		selectedIndex = Math.max(0, filteredTerminals.length - 1);

	const select = (terminal: TerminalOption) => {
		onselect(terminal.id);
		onclose();
	};

	const handleKeydown = (event: KeyboardEvent) => {
		if (event.isComposing) return;
		if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
			event.preventDefault();
			event.stopPropagation();
			selectedIndex = Math.max(
				0,
				Math.min(filteredTerminals.length - 1, selectedIndex + (event.key === 'ArrowDown' ? 1 : -1))
			);
			document
				.getElementById(`terminal-picker-option-${selectedIndex}`)
				?.scrollIntoView({ block: 'nearest' });
		} else if (event.key === 'Enter' && filteredTerminals[selectedIndex]) {
			event.preventDefault();
			event.stopPropagation();
			select(filteredTerminals[selectedIndex]);
		}
	};
</script>

<Modal
	size="sm"
	ariaLabel={$i18n.t('Select a terminal')}
	onRequestClose={onclose}
	className="bg-white dark:bg-gray-850 rounded-xl overflow-hidden !border-gray-100 dark:!border-gray-800 text-gray-700 dark:text-gray-100 font-normal"
>
	<div class="flex h-10 items-center gap-2 px-3">
		<input
			bind:value={query}
			role="combobox"
			aria-label={$i18n.t('Select a terminal')}
			aria-autocomplete="list"
			aria-expanded={filteredTerminals.length > 0}
			aria-controls="terminal-picker-options"
			aria-activedescendant={filteredTerminals.length
				? `terminal-picker-option-${selectedIndex}`
				: undefined}
			autocomplete="off"
			spellcheck="false"
			placeholder={$i18n.t('Select a terminal')}
			class="h-8 min-w-0 flex-1 bg-transparent text-[0.8125rem] font-normal outline-none placeholder:text-gray-400 dark:placeholder:text-gray-500"
			on:keydown={handleKeydown}
		/>
		<button type="button" aria-label={$i18n.t('Close')} on:click={onclose}>
			<KeyPill text="Esc" />
		</button>
	</div>
	<div
		id="terminal-picker-options"
		role="listbox"
		aria-label={$i18n.t('Terminals')}
		class="max-h-[min(20rem,60dvh)] overflow-y-auto px-1 pb-1"
	>
		{#each filteredTerminals as terminal, index (terminal.id)}
			<button
				type="button"
				role="option"
				tabindex="-1"
				id="terminal-picker-option-{index}"
				aria-selected={index === selectedIndex}
				class="flex h-[1.6875rem] w-full items-center gap-2 rounded-lg px-2 text-start text-[0.8125rem] font-normal transition-colors duration-75 {index ===
				selectedIndex
					? 'bg-gray-100/60 dark:bg-gray-800/60'
					: 'hover:bg-gray-50/40 dark:hover:bg-gray-800/40'}"
				on:mousemove={() => (selectedIndex = index)}
				on:click={() => select(terminal)}
			>
				<span class="shrink-0 text-gray-500 dark:text-gray-400">
					{#if terminal.device}
						<Server className="size-3.5" strokeWidth="2" />
					{:else}
						<Cloud className="size-3.5" strokeWidth="2" />
					{/if}
				</span>
				<span class="min-w-0 flex-1 truncate">{terminal.label}</span>
			</button>
		{/each}
	</div>
	{#if !filteredTerminals.length}
		<div role="status" class="px-3 pb-3 pt-1 text-[0.6875rem] text-gray-400 dark:text-gray-500">
			{$i18n.t('No terminals found')}
		</div>
	{/if}
</Modal>
