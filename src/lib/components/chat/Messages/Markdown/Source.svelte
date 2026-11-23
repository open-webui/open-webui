<script lang="ts">
	import { getContext } from 'svelte';
	import type { Readable } from 'svelte/store';
	import { decodeString } from '$lib/utils';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');
	const citations = getContext<Readable<{ number: number; document: string[] }[]>>('citations');

	export let id;

	export let title: string = 'N/A';

	export let onClick: Function = () => {};

	// Helper function to return only the domain from a URL
	function getDomain(url: string): string {
		const domain = url.replace('http://', '').replace('https://', '').split(/[/?#]/)[0];

		if (domain.startsWith('www.')) {
			return domain.slice(4);
		}
		return domain;
	}

	const getDisplayTitle = (title: string) => {
		if (!title) return 'N/A';
		if (title.length > 30) {
			return title.slice(0, 15) + '...' + title.slice(-10);
		}
		return title;
	};

	const getDisplayPassage = (passage: string) => {
		if (passage.length > 300) {
			return passage.slice(0, 300) + '...';
		}
		return passage;
	};

	// Helper function to check if text is a URL and return the domain
	function formattedTitle(title: string): string {
		if (title.startsWith('http')) {
			return getDomain(title);
		}

		return title;
	}
</script>

{#if title !== 'N/A'}
	{@const number = typeof id === 'string' ? parseInt(id.split('#')[0]) : id}
	{@const citation = $citations.find((entry) => entry.number === number)}
	<Tooltip
		as="span"
		className=""
		content={`${decodeString(title)}: ${getDisplayPassage(citation.document[0])}`}
	>
		<button
			aria-label={$i18n.t('View source: {{title}}', { title: formattedTitle(decodeString(title)) })}
			class="text-[0.625rem] w-fit translate-y-[2px] px-2 py-0.5 dark:bg-base-0/5 dark:text-base-0/80 dark:hover:text-base-0 bg-base-50 text-base-1000/80 hover:text-base-1000 transition rounded-xl"
			on:click={() => {
				onClick(id);
			}}
		>
			<span class="line-clamp-1">
				{getDisplayTitle(formattedTitle(decodeString(title)))}
			</span>
		</button>
	</Tooltip>
{/if}
