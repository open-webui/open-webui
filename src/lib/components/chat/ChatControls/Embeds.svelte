<script lang="ts">
	import { embed, showControls, showEmbeds } from '$lib/stores';

	import FullHeightIframe from '$lib/components/common/FullHeightIframe.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let overlay = false;

	const getSrcUrl = (url: string, chatId?: string, messageId?: string) => {
		try {
			const parsed = new URL(url);

			if (chatId) {
				parsed.searchParams.set('chat_id', chatId);
			}

			if (messageId) {
				parsed.searchParams.set('message_id', messageId);
			}

			return parsed.toString();
		} catch {
			// Fallback for relative URLs or invalid input
			const hasQuery = url.includes('?');
			const parts = [];

			if (chatId) parts.push(`chat_id=${encodeURIComponent(chatId)}`);
			if (messageId) parts.push(`message_id=${encodeURIComponent(messageId)}`);

			if (parts.length === 0) return url;

			return url + (hasQuery ? '&' : '?') + parts.join('&');
		}
	};
</script>

{#if $embed}
	<div class="h-full w-full">
		<div
			class="pointer-events-auto z-20 flex justify-between items-center py-3 px-2 font-primar text-gray-900 dark:text-white"
		>
			<div class="flex-1 flex items-center justify-between pl-2">
				<a
					class="flex items-center space-x-2 hover:underline"
					href={$embed?.url}
					target="_blank"
					rel="noopener noreferrer"
				>
					{$embed?.title ?? 'Embedded Content'}
				</a>
			</div>

			<button
				class="self-center pointer-events-auto p-1 rounded-full bg-white dark:bg-gray-850"
				on:click={() => {
					showControls.set(false);
					showEmbeds.set(false);
					embed.set(null);
				}}
			>
				<XMark className="size-3.5 text-gray-900 dark:text-white" />
			</button>
		</div>

		<div class=" w-full h-full relative">
			{#if overlay}
				<div class=" absolute top-0 left-0 right-0 bottom-0 z-10"></div>
			{/if}

			<FullHeightIframe
				src={getSrcUrl($embed?.url ?? '', $embed?.chatId, $embed?.messageId)}
				payload={$embed?.source ?? null}
				iframeClassName="w-full h-full"
			/>
		</div>
	</div>
{/if}
