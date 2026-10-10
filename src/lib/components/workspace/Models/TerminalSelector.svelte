<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import ModelSettingsLabel from './ModelSettingsLabel.svelte';
	import { getTerminalServers, type TerminalServer } from '$lib/apis/terminal';

	const i18n = getContext<any>('i18n');

	export let terminalId: string = '';

	let terminals: TerminalServer[] = [];

	onMount(async () => {
		terminals = await getTerminalServers(localStorage.token);
	});
</script>

{#if terminals.length > 0}
	<label
		class="flex min-h-8 items-center justify-between gap-3 px-1 text-xs font-normal text-gray-600 dark:text-gray-400"
	>
		<ModelSettingsLabel
			label={$i18n.t('Default terminal')}
			description={$i18n.t('Choose the terminal server selected by default for chats with this model.')}
		/>
		<select
			class="min-w-0 max-w-[60%] cursor-pointer bg-transparent py-0 text-xs font-normal text-gray-900 outline-hidden dark:text-gray-100"
			bind:value={terminalId}
		>
			<option value="">{$i18n.t('None')}</option>
			{#each terminals as terminal (terminal.id)}
				<option value={terminal.id}>{terminal.name || terminal.id}</option>
			{/each}
		</select>
	</label>
{:else}
	<p class="px-1 py-1 text-xs text-gray-500 dark:text-gray-400">
		{$i18n.t('No terminal servers available')}
	</p>
{/if}
