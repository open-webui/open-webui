<script lang="ts">
	import { embed } from '$lib/stores';

	import FullHeightIframe from '$lib/components/common/FullHeightIframe.svelte';

	export let overlay = false;
	// Preserve the former embed close label for i18n extraction.
	// t('Close embed')

	const getSrcUrl = (url: string, chatId?: string, messageId?: string, sourceId: string) => {
		try {
			const parsed = new URL(url);

			if (chatId) {
				parsed.searchParams.set('chat_id', chatId);
			}

			if (messageId) {
				parsed.searchParams.set('message_id', messageId);
			}

			if (sourceId) {
				parsed.searchParams.set('source_id', sourceId);
			}

			return parsed.toString();
		} catch {
			// Fallback for relative URLs or invalid input
			const hasQuery = url.includes('?');
			const parts = [];

			if (chatId) parts.push(`chat_id=${encodeURIComponent(chatId)}`);
			if (messageId) parts.push(`message_id=${encodeURIComponent(messageId)}`);
			if (sourceId) parts.push(`source_id=${encodeURIComponent(sourceId)}`);

			if (parts.length === 0) return url;

			return url + (hasQuery ? '&' : '?') + parts.join('&');
		}
	};
</script>

{#if $embed}
	<div class="h-full w-full flex flex-col">
		<div
			class="pointer-events-auto z-20 flex justify-between items-center pb-3 px-2 font-primar text-gray-900 dark:text-white flex-shrink-0"
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
		</div>

		<div class="w-full flex-1 min-h-0 relative">
			{#if overlay}
				<div class=" absolute top-0 left-0 right-0 bottom-0 z-10"></div>
			{/if}

			<FullHeightIframe
				src={getSrcUrl($embed?.url ?? '', $embed?.chatId, $embed?.messageId, $embed?.sourceId)}
				payload={$embed?.source ?? null}
				iframeClassName="w-full h-full"
			/>
		</div>
	</div>
{/if}
