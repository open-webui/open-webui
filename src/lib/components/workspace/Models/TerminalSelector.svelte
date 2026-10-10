<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { getTerminalServers, type TerminalServer } from '$lib/apis/terminal';

	const i18n = getContext('i18n');

	export let terminalId: string = '';

	let terminals: TerminalServer[] = [];

	onMount(async () => {
		terminals = await getTerminalServers(localStorage.token);
	});
</script>

{#if terminals.length > 0}
	<div class="flex w-full justify-between mb-1">
		<div class="self-center text-xs font-normal text-gray-600 dark:text-gray-400">
			{$i18n.t('Terminal')}
		</div>
	</div>

	<select
		class="block h-5 w-full py-0 text-xs leading-5 bg-transparent outline-hidden cursor-pointer font-normal text-gray-900 dark:text-gray-100"
		bind:value={terminalId}
	>
		<option value="">{$i18n.t('None')}</option>
		{#each terminals as terminal (terminal.id)}
			<option value={terminal.id}>{terminal.name || terminal.id}</option>
		{/each}
	</select>
{/if}
