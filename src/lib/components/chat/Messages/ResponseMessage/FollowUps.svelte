<script lang="ts">
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import KatexRenderer from '$lib/components/chat/Messages/Markdown/KatexRenderer.svelte';
	import { onMount, tick, getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let followUps: string[] = [];
	export let onClick: (followUp: string) => void = () => {};

	// Parse text to identify LaTeX segments
	// Returns an array of { type: 'text' | 'latex', content: string, displayMode: boolean }
	function parseLatex(text: string): Array<{ type: 'text' | 'latex'; content: string; displayMode: boolean }> {
		const result: Array<{ type: 'text' | 'latex'; content: string; displayMode: boolean }> = [];

		// Combined regex for $$ (display) and $ (inline) LaTeX
		// Match $$ first (display mode), then $ (inline mode)
		const regex = /(\$\$[\s\S]*?\$\$|\$[^\$\n]+?\$)/g;

		let lastIndex = 0;
		let match;

		while ((match = regex.exec(text)) !== null) {
			// Add text before the match
			if (match.index > lastIndex) {
				result.push({
					type: 'text',
					content: text.slice(lastIndex, match.index),
					displayMode: false
				});
			}

			// Add the LaTeX match
			const latexContent = match[0];
			const isDisplayMode = latexContent.startsWith('$$');

			// Remove delimiters
			const cleanContent = isDisplayMode
				? latexContent.slice(2, -2).trim()
				: latexContent.slice(1, -1).trim();

			result.push({
				type: 'latex',
				content: cleanContent,
				displayMode: isDisplayMode
			});

			lastIndex = regex.lastIndex;
		}

		// Add remaining text after last match
		if (lastIndex < text.length) {
			result.push({
				type: 'text',
				content: text.slice(lastIndex),
				displayMode: false
			});
		}

		return result;
	}
</script>

<div class="mt-4">
	<div class="text-sm font-medium">
		{$i18n.t('Follow up')}
	</div>

	<div class="flex flex-col text-left gap-1 mt-1.5">
		{#each followUps as followUp, idx (idx)}
			<!-- svelte-ignore a11y-no-static-element-interactions -->
			<!-- svelte-ignore a11y-click-events-have-key-events -->
			<Tooltip content={followUp} placement="top-start" className="line-clamp-1">
				<div
					class=" py-1.5 bg-transparent text-left text-sm flex items-center gap-2 text-gray-500 dark:text-gray-400 hover:text-black dark:hover:text-white transition cursor-pointer"
					on:click={() => onClick(followUp)}
					aria-label={followUp}
				>
					<div class="line-clamp-1">
						{#each parseLatex(followUp) as segment}
							{#if segment.type === 'latex'}
								<KatexRenderer content={segment.content} displayMode={segment.displayMode} />
							{:else}
								{segment.content}
							{/if}
						{/each}
					</div>
				</div>
			</Tooltip>

			{#if idx < followUps.length - 1}
				<hr class="border-gray-50 dark:border-gray-850" />
			{/if}
		{/each}
	</div>
</div>
