<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { models, config } from '$lib/stores';

	import { toast } from 'svelte-sonner';
	import { deleteSharedChatById, getChatById, shareChatById } from '$lib/apis/chats';
	import { copyToClipboard } from '$lib/utils';

	import Modal from '../common/Modal.svelte';
	import Link from '../icons/Link.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	export let chatId;

	let chat = null;
	let shareUrl = null;
	const i18n = getContext('i18n');

	export let show = false;

	const isDifferentChat = (_chat) => {
		if (!chat) {
			return true;
		}
		if (!_chat) {
			return false;
		}
		return chat.id !== _chat.id || chat.share_id !== _chat.share_id;
	};

	$: if (show) {
		(async () => {
			if (chatId) {
				const _chat = await getChatById(localStorage.token, chatId);
				if (isDifferentChat(_chat)) {
					chat = _chat;
				}
				console.log(chat);
			} else {
				chat = null;
				console.log(chat);
			}
		})();
	}
	let usages = [];
	let allUnique = [];

	function extractUsages(obj) {
		const results = [];
		function recurse(item) {
			if (Array.isArray(item)) {
				item.forEach(recurse);  // 🟢 Recurse into array elements
			} else if (typeof item === 'object' && item !== null) {
				for (const key in item) {
					if (key === 'usage') {
						results.push(item[key]);  // 🎯 Found a usage!
					} else {
						recurse(item[key]);      // 🔄 Recurse into nested objects
					}
				}
			}
		}
		recurse(obj);
		return results;
	}

	function handleParse(chatInput) {
		try {
			const parsed = typeof chatInput === 'string' ? JSON.parse(chatInput) : chatInput;
			usages = extractUsages(parsed);
			console.log(usages);
		} catch (error) {
			alert('Invalid JSON input');
			usages = [];
		}
		const seen = new Set();
		allUnique = usages.filter(obj => {
			const serialized = JSON.stringify(obj);
			if (seen.has(serialized)) {
				return false; // Duplicate
			}
			seen.add(serialized);
			return true; // Unique
		});
	}
	$: if (show) {
		handleParse(chat); // ✅ only call when chat is freshly fetched
	}
</script>

<Modal bind:show size="lg">
	<div>
		<div class=" flex justify-between w-full dark:text-gray-300 px-5 pt-4 pb-0.5">
			<div class=" text-lg font-medium self-center">{$i18n.t('Chat Profile Data')}</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		{#if chat}
			<div class="px-5 pt-4 pb-5 w-full flex flex-col text-left justify-center">
				<div class="w-full flex flex-col space-y-4 text-left">
					{#if usages.length > 0}
						{#each allUnique as usage, i}
							<pre class="text-left"><strong  class="block mb-2">Message #{i + 1}:</strong></pre>
							<div class="grid grid-cols-2 gap-x-6 gap-y-2 border rounded p-4 bg-gray-50">
								{#each Object.entries(usage) as [key, value]}
									<div class="font-medium text-left text-gray-700">{key}</div>
									<pre class="w-full max-w-[1200px] overflow-auto whitespace-pre-wrap font-mono text-sm bg-gray-100 border rounded p-4">{String(value)}</pre>
								{/each}
							</div>
						{/each}
					{:else}
						<p>No usage blocks found yet.</p>
					{/if}
				</div>
			</div>
		{/if}
	</div>
</Modal>
