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

	function renderItem(item: Array<string> | string | object | null): string {
		try {
			if (typeof item === 'string') {
				return `<div>${item}</div>`;
			} else if (Array.isArray(item)) {
				return item.map(renderItem).join('');
			} else if (typeof item === 'object' && item !== null) {
				return Object.entries(item)
					.map(([key, value]): string => {
						if (typeof value === 'object') {
							return `<div>${key}:</div>${renderItem(value)}`;
						}
						return `<div>${key}: ${value}</div>`;
					})
					.join('');
			} else {
				return `<div>${String(item)}</div>`;
			}
		} catch (error) {
			console.error('Error rendering item:', error);
			return '<div>Error rendering content</div>';
		}
	}

	function handleReject() {
		console.log('--- handleReject!!!');

		dispatch('addMessage', {
			role: 'assistant',
			content: 'Transaction rejected',
			pending: false
		});
	}

	async function handleAccept() {
		console.log('--- handleAccept!!!');
		try {
			let parsedDoc;
			try {
				parsedDoc = citation.document[0] ? JSON.parse(citation.document[0]) : null;
			} catch (error) {
				throw new Error('Invalid transaction data');
			}

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
		}
	}

	// $: documentContent = (() => {
	// 	try {
	// 		if (!citation?.document?.[0]) return [];
	// 		const parsed = JSON.parse(citation.document[0]);
	// 		return Array.isArray(parsed) ? parsed : [parsed];
	// 	} catch (error) {
	// 		console.error('Error parsing document:', error);
	// 		return [];
	// 	}
	// })();
</script>

<div class="flex flex-col gap-2">
	<!-- <div class="flex-col text-xs font-medium flex-wrap">
		<div class="flex flex-col gap-1">RESPONSE:</div>
		{#if documentContent.length > 0}
			{@html documentContent.map(renderItem).join('')}
		{:else}
			<div>No content available</div>
		{/if}
	</div> -->
	<div class="flex gap-2">
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
	</div>
</div>
