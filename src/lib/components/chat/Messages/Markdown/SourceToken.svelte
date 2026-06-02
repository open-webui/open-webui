<script lang="ts">
	import { LinkPreview } from 'bits-ui';
	import { decodeString } from '$lib/utils';
	import Source from './Source.svelte';

	export let id;
	export let token;
	export let sourceIds: (string | { name: string; url?: string | null })[] = [];
	export let onClick: Function = () => {};

	let containerElement;
	let openPreview = false;

	// Helper to get source info from sourceIds array (handles both string and object formats)
	function getSourceInfo(index: number): { name: string; url: string | null } {
		const source = sourceIds[index];
		if (!source) return { name: 'N/A', url: null };
		if (typeof source === 'string') {
			return { name: source, url: null };
		}
		return { name: source.name ?? 'N/A', url: source.url ?? null };
	}

	// Helper function to return only the domain from a URL
	function getDomain(url: string): string {
		const domain = url.replace('http://', '').replace('https://', '').split(/[/?#]/)[0];

		if (domain.startsWith('www.')) {
			return domain.slice(4);
		}
		return domain;
	}

	// Helper function to check if text is a URL and return the domain
	function formattedTitle(title: string): string {
		if (title.startsWith('http')) {
			return getDomain(title);
		}

		return title;
	}

	const getDisplayTitle = (title: string) => {
		if (!title) return 'N/A';
		if (title.length > 30) {
			return title.slice(0, 15) + '...' + title.slice(-10);
		}
		return title;
	};
</script>

{#if sourceIds}
	{#if (token?.ids ?? []).length == 1}
		{@const tokenId = token.ids[0]}
		{@const identifier = token.citationIdentifiers ? token.citationIdentifiers[0] : tokenId - 1}
		{@const sourceInfo = getSourceInfo(tokenId - 1)}
		<Source id={identifier} title={sourceInfo.name} url={sourceInfo.url} {onClick} />
	{:else}
		{@const firstSourceInfo = getSourceInfo(token.ids[0] - 1)}
		<LinkPreview.Root openDelay={0} bind:open={openPreview}>
			<LinkPreview.Trigger>
				<button
					aria-label={`${getDisplayTitle(formattedTitle(decodeString(sourceIds[token.ids[0] - 1])))} +${(token?.ids ?? []).length - 1} more sources`}
					class="text-[10px] w-fit translate-y-[2px] px-2 py-0.5 dark:bg-white/5 dark:text-white/80 dark:hover:text-white bg-gray-50 text-black/80 hover:text-black transition rounded-xl"
					on:click={() => {
						openPreview = !openPreview;
					}}
				>
					<span class="line-clamp-1">
						{getDisplayTitle(formattedTitle(decodeString(firstSourceInfo.name)))}
						<span class="dark:text-white/50 text-black/50">+{(token?.ids ?? []).length - 1}</span>
					</span>
				</button>
			</LinkPreview.Trigger>
<<<<<<< HEAD
			<LinkPreview.Content
				class="z-[999]"
				align="start"
				strategy="fixed"
				sideOffset={6}
				el={containerElement}
			>
				<div class="bg-gray-50 dark:bg-gray-850 rounded-xl p-1 cursor-pointer">
					{#each token.citationIdentifiers ?? token.ids as identifier}
						{@const tokenId =
							typeof identifier === 'string' ? parseInt(identifier.split('#')[0]) : identifier}
						{@const sourceInfo = getSourceInfo(tokenId - 1)}
						<div class="">
							<Source id={identifier} title={sourceInfo.name} url={sourceInfo.url} {onClick} />
						</div>
					{/each}
				</div>
			</LinkPreview.Content>
=======
			<LinkPreview.Portal>
				<LinkPreview.Content class="z-[999]" align="start" strategy="fixed" sideOffset={6}>
					<div class="bg-gray-50 dark:bg-gray-850 rounded-xl p-1 cursor-pointer">
						{#each token.citationIdentifiers ?? token.ids as identifier}
							{@const id =
								typeof identifier === 'string' ? parseInt(identifier.split('#')[0]) : identifier}
							<div class="">
								<Source id={identifier} title={sourceIds[id - 1]} {onClick} />
							</div>
						{/each}
					</div>
				</LinkPreview.Content>
			</LinkPreview.Portal>
>>>>>>> v0.9.6
		</LinkPreview.Root>
	{/if}
{:else}
	<span>{token.raw}</span>
{/if}
