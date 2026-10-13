<script lang="ts">
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import type { Embed } from '$lib/apis/apps';

	export let embed: Embed;

	let failedThumbnail: string | null = null;
	$: accent = embed.color == null ? undefined : `#${embed.color.toString(16).padStart(6, '0')}`;
</script>

<div
	class="app-embed @container relative w-full max-w-[520px] min-w-0 rounded-lg border border-gray-200 bg-gray-50/70 px-4.5 py-3 text-xs wrap-anywhere dark:border-white/8 dark:bg-white/[0.035] [&_p]:m-0 [&_p+p]:mt-1.5 [&_pre]:whitespace-pre-wrap [&_pre]:wrap-anywhere [&_h1]:my-1.5 [&_h1]:text-xs [&_h2]:my-1.5 [&_h2]:text-xs [&_h3]:my-1.5 [&_h3]:text-xs [&_h4]:my-1.5 [&_h4]:text-xs [&_h5]:my-1.5 [&_h5]:text-xs [&_h6]:my-1.5 [&_h6]:text-xs"
>
	{#if accent}
		<svg class="pointer-events-none absolute inset-0 size-full rounded-lg" aria-hidden="true">
			<rect width="3" height="100%" fill={accent} />
		</svg>
	{/if}
	{#if embed.author?.name}
		<div class="mb-1.5 text-xs font-medium text-gray-500 dark:text-gray-400">
			{embed.author.name}
		</div>
	{/if}
	<div class="flex min-w-0 items-start gap-3">
		<div class="min-w-0 flex-1 space-y-1.5">
			{#if embed.title}
				<div class="text-sm font-semibold leading-5">
					{#if embed.url}
						<a href={embed.url} target="_blank" rel="noopener noreferrer" class="hover:underline"
							>{embed.title}</a
						>
					{:else}{embed.title}{/if}
				</div>
			{/if}
			{#if embed.description}
				<Markdown content={embed.description} allowEmbeds={false} allowHtml={false} />
			{/if}
		</div>
		{#if embed.thumbnail?.url && failedThumbnail !== embed.thumbnail.url}
			<img
				src={embed.thumbnail.url}
				alt=""
				class="size-12 shrink-0 rounded-lg object-contain"
				loading="lazy"
				referrerpolicy="no-referrer"
				on:error={() => (failedThumbnail = embed.thumbnail?.url ?? null)}
			/>
		{/if}
	</div>
	{#if embed.fields?.length}
		<div class="embed-fields mt-3 grid grid-cols-1 gap-x-4 gap-y-2.5 @min-[361px]:grid-cols-3">
			{#each embed.fields as field}
				<div class="min-w-0 {field.inline ? '' : 'col-span-full'}">
					<div class="mb-0.5 text-xs font-semibold">{field.name}</div>
					<Markdown content={field.value} allowEmbeds={false} allowHtml={false} />
				</div>
			{/each}
		</div>
	{/if}
	{#if embed.footer?.text}
		<div class="mt-3 text-xs text-gray-500 dark:text-gray-400">{embed.footer.text}</div>
	{/if}
</div>
