<script lang="ts">
	import { getContext } from 'svelte';
	import { v4 as uuidv4 } from 'uuid';
	import { createEventDispatcher } from 'svelte';
	// import { updateChatById, getChatList } from '$lib/apis/chats';
	import { addReaction, deleteMessage, removeReaction, updateMessage } from '$lib/apis/channels';
	import { keplerWallet } from '$lib/contexts/KeplerWalletContext';

	import { chats, currentChatPage } from '$lib/stores';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');
	export let citation: { document: string[] };
	let isExecuting = false;
	let parsedDoc: any = null;
	let isValidJson = false;

	// Try to parse the document on component initialization
	$: {
		try {
			parsedDoc = citation.document[0] ? JSON.parse(citation.document[0]) : null;
			isValidJson = true;
		} catch (error) {
			parsedDoc = citation.document[0] || null;
			isValidJson = false;
		}
	}

	function formatValue(value: any): string {
		if (typeof value === 'object' && value !== null) {
			return JSON.stringify(value, null, 2);
		}
		return String(value);
	}

	function handleReject() {
		dispatch('addMessage', {
			role: 'assistant',
			content: 'Transaction rejected',
			pending: false
		});
	}

	async function handleAccept() {
		try {
			isExecuting = true;
			if (!parsedDoc) {
				throw new Error('No transaction data available');
			}

			const result = await keplerWallet.executeContract(parsedDoc);
			const txHash = result.transactionHash;
			console.log('Transaction:', result);

			dispatch('addMessage', {
				role: 'assistant',
				content: `Transaction successful!\r\nTx hash: ${txHash}`,
				pending: false
			});
		} catch (error: any) {
			console.error('Transaction signing failed:', error);
			dispatch('addMessage', {
				role: 'assistant',
				content: `Transaction failed: ${error.message}`,
				pending: false
			});
		} finally {
			isExecuting = false;
		}
	}
</script>

<div class="flex flex-col gap-4">
	{#if parsedDoc}
		<div class="bg-gray-50 rounded-lg p-4 font-mono text-sm overflow-x-auto">
			{#if isValidJson}
				<div class="space-y-2">
					{#each Object.entries(parsedDoc) as [key, value]}
						<div>
							<span class="text-purple-600">{key}:</span>
							<span class="text-gray-800 whitespace-pre-wrap">{formatValue(value)}</span>
						</div>
					{/each}
				</div>
			{:else}
				<div class="text-red-600">
					Invalid JSON format. Preview of raw content:
					<div class="mt-2 text-gray-800 whitespace-pre-wrap">{parsedDoc}</div>
				</div>
			{/if}
		</div>
	{/if}

	<div class="flex gap-2">
		{#if isExecuting}
			<div class="flex items-center justify-center">
				<div class="animate-spin rounded-full h-6 w-6 border-b-2 border-green-500"></div>
				<span class="ml-2 text-sm text-gray-600">Executing transaction...</span>
			</div>
		{:else if isValidJson && parsedDoc}
			<button
				class="px-3 py-1 bg-green-500 hover:bg-green-600 text-white rounded-md text-sm"
				on:click={handleAccept}
			>
				Accept
			</button>
			<button
				class="px-3 py-1 bg-red-500 hover:bg-red-600 text-white rounded-md text-sm"
				on:click={handleReject}
			>
				Reject
			</button>
		{/if}
	</div>
</div>
