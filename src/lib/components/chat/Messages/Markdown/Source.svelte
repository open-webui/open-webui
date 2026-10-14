<script lang="ts">
	import { getContext } from 'svelte';
	import { decodeString } from '$lib/utils';
	import type { SourceInfo, SourceMetadata } from '$lib/utils/citations';
	import CitationSourceIcon from '../Citations/CitationSourceIcon.svelte';

	const i18n = getContext('i18n');

	export let id: string | number;

	export let title: string = 'N/A';
	export let href: string | null = null;
	export let source: SourceInfo | undefined = undefined;
	export let metadata: SourceMetadata | undefined = undefined;
	export let onClick: (id: string | number) => void = () => {};

	$: iconSource = source ?? { name: title };

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

	// Helper function to check if text is a URL and return the domain
	function formattedTitle(title: string): string {
		if (title.startsWith('http')) {
			return getDomain(title);
		}

		return title;
	}
</script>

{#if title !== 'N/A'}
	{@const label = formattedTitle(decodeString(title))}
	{@const chipClass =
		'text-[0.625rem] w-fit translate-y-[2px] px-2 py-0.5 dark:bg-white/5 dark:text-white/80 dark:hover:text-white bg-gray-50 text-black/80 hover:text-black transition rounded-xl inline-flex items-center gap-1 !no-underline hover:!no-underline visited:!no-underline focus-visible:!no-underline'}
	{#snippet content()}
		<CitationSourceIcon source={iconSource} {metadata} size={12} />
		<span class="line-clamp-1">
			{getDisplayTitle(label)}
		</span>
	{/snippet}
	{#if href}
		<a
			{href}
			target="_blank"
			rel="nofollow noopener noreferrer"
			referrerpolicy="no-referrer"
			aria-label={$i18n.t('Open source: {{title}}', { title: label })}
			class={chipClass}
		>
			{@render content()}
		</a>
	{:else}
		<button
			aria-label={$i18n.t('View source: {{title}}', { title: label })}
			class={chipClass}
			on:click={() => onClick(id)}
		>
			{@render content()}
		</button>
	{/if}
{/if}
