<script lang="ts">
	import { getContext } from 'svelte';

	import Modal from '$lib/components/common/Modal.svelte';
	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext<any>('i18n');

	export let show = false;
	export let machines: { id: string; name?: string }[] = [];
	/** Returns true once opened; otherwise the picker stays open. */
	export let onSelect: (machineId: string, directory: string) => Promise<boolean>;

	// Start on the machine new chats use.
	let machineId = (
		machines.find((machine) => machine.id === localStorage.selectedMachineId) ?? machines[0]
	).id;
	let opening = false;

	const selectDirectory = async (directory: string) => {
		if (opening) return;
		opening = true;
		if (await onSelect(machineId, directory)) show = false;
		opening = false;
	};
</script>

<Modal bind:show ariaLabel={$i18n.t('Open directory')} size="md">
	<div class="px-2 py-4">
		<div class="mb-3 flex items-center justify-between gap-2 px-2 text-sm">
			<span class="flex-1">{$i18n.t('Open directory')}</span>
			{#if machines.length > 1}
				<SettingsSelect
					bind:value={machineId}
					ariaLabel={$i18n.t('Machine')}
					className="min-w-0 max-w-[50%]"
					disabled={opening}
				>
					{#each machines as machine (machine.id)}
						<option value={machine.id}>{machine.name || $i18n.t('Machine')}</option>
					{/each}
				</SettingsSelect>
			{/if}
			<button
				type="button"
				aria-label={$i18n.t('Close')}
				class="text-base-500 hover:text-base-900 dark:hover:text-base-100"
				on:click={() => (show = false)}><XMark className="size-4" /></button
			>
		</div>
		<div class="h-[60dvh] min-h-0" aria-busy={opening}>
			{#await import('$lib/components/chat/FileNav.svelte') then { default: FileNav }}
				{#key machineId}
					<FileNav
						{machineId}
						manageFileRequests={false}
						showTerminalDock={false}
						onSelectDirectory={selectDirectory}
					/>
				{/key}
			{/await}
		</div>
	</div>
</Modal>
