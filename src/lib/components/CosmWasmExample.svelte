<!-- CosmWasmExample.svelte -->
<script lang="ts">
	import { cosmWasm } from '$lib/stores/cosmwasm';
	import { onDestroy } from 'svelte';

	// Example of getting contract info
	let contractInfo = '';
	let loading = false;
	let error = '';

	// Example contract address - replace with your actual contract address
	const CONTRACT_ADDRESS = 'wasm1...';

	async function getContractInfo() {
		loading = true;
		error = '';
		try {
			const client = $cosmWasm.client;
			if (!client) {
				throw new Error('Client not initialized');
			}

			// Example query - replace with your actual contract query
			const result = await client.getContractInfo(CONTRACT_ADDRESS);
			contractInfo = JSON.stringify(result, null, 2);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to get contract info';
		} finally {
			loading = false;
		}
	}

	// Clean up on component destruction
	onDestroy(() => {
		cosmWasm.disconnect();
	});
</script>

<div class="p-4">
	<h2 class="text-xl mb-4">CosmWasm Client Status</h2>

	{#if $cosmWasm.isConnecting}
		<p>Connecting to CosmWasm node...</p>
	{:else if $cosmWasm.error}
		<p class="text-red-500">Error: {$cosmWasm.error.message}</p>
		<button
			class="mt-2 px-4 py-2 bg-blue-500 text-white rounded"
			on:click={() => cosmWasm.initialize()}
		>
			Retry Connection
		</button>
	{:else if $cosmWasm.client}
		<p class="text-green-500 mb-4">Connected to CosmWasm node</p>

		<button
			class="px-4 py-2 bg-blue-500 text-white rounded"
			on:click={getContractInfo}
			disabled={loading}
		>
			{loading ? 'Loading...' : 'Get Contract Info'}
		</button>

		{#if error}
			<p class="text-red-500 mt-2">{error}</p>
		{/if}

		{#if contractInfo}
			<pre class="mt-4 p-4 bg-gray-100 rounded overflow-auto">
                {contractInfo}
            </pre>
		{/if}
	{/if}
</div>
