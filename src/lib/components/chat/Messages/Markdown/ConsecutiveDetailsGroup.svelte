<script lang="ts">
	import { getContext } from 'svelte';
	import { slide } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';

	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import WrenchSolid from '$lib/components/icons/WrenchSolid.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';
	import CheckCircle from '$lib/components/icons/CheckCircle.svelte';

	const i18n = getContext('i18n');

	export let id = '';
	export let tokens: Array<{
		summary?: string;
		attributes?: {
			type?: string;
			name?: string;
			done?: string;
			duration?: string;
		};
	}> = [];

	export let messageDone = true;

	let open = false;

	$: toolCallCount = tokens.filter((t) => t?.attributes?.type === 'tool_calls').length;
	$: reasoningCount = tokens.filter((t) => t?.attributes?.type === 'reasoning').length;
	$: hasPending =
		!messageDone &&
		tokens.some((t) => t?.attributes?.done !== undefined && t?.attributes?.done !== 'true');

	$: codeInterpreterCount = tokens.filter((t) => t?.attributes?.type === 'code_interpreter').length;

	$: summaryText = (() => {
		const parts = [];

		if (toolCallCount > 0) {
			// Group by tool name and show counts
			const nameCounts = {};
			tokens
				.filter((t) => t?.attributes?.type === 'tool_calls')
				.forEach((t) => {
					const name = t?.attributes?.name ?? 'tool';
					nameCounts[name] = (nameCounts[name] || 0) + 1;
				});

			const toolParts = Object.entries(nameCounts).map(([name, count]) =>
				count > 1 ? `${count} ${name}` : name
			);
			parts.push(...toolParts);
		}

		if (codeInterpreterCount > 0) {
			if (codeInterpreterCount === 1) {
				parts.push($i18n.t('Ran {{COUNT}} analysis', { COUNT: codeInterpreterCount }));
			} else {
				parts.push($i18n.t('Ran {{COUNT}} analyses', { COUNT: codeInterpreterCount }));
			}
		}

		const prefix = hasPending ? $i18n.t('Exploring') : $i18n.t('Explored');
		const detail = parts.join(', ');
		return detail;
	})();

	$: prefixText = hasPending ? $i18n.t('Exploring') : $i18n.t('Explored');
</script>

<div {id} class="w-full">
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<button
		class="w-fit text-left text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition cursor-pointer"
		aria-label={$i18n.t('Toggle details')}
		aria-expanded={open}
		on:click={() => {
			open = !open;
		}}
	>
		<div class="flex items-center gap-1.5">
			<!-- Status icon -->
			{#if hasPending}
				<div>
					<Spinner className="size-4" />
				</div>
			{:else if toolCallCount > 0}
				<div class="text-emerald-500 dark:text-emerald-400">
					<CheckCircle className="size-4" strokeWidth="2" />
				</div>
			{:else}
				<div class="text-gray-400 dark:text-gray-500">
					<Sparkles className="size-3.5" />
				</div>
			{/if}

			<!-- Summary text -->
			<div class="flex-1 line-clamp-1">
				<span class="text-gray-600 dark:text-gray-300 {hasPending ? 'shimmer' : ''}"
					>{prefixText}</span
				>
				{#if summaryText}
					<span class="text-gray-400 dark:text-gray-500">{summaryText}</span>
				{/if}
			</div>

			<!-- Chevron -->
			<div class="flex shrink-0 self-center text-gray-400 dark:text-gray-500">
				{#if open}
					<ChevronUp strokeWidth="3.5" className="size-3" />
				{:else}
					<ChevronDown strokeWidth="3.5" className="size-3" />
				{/if}
			</div>
		</div>
	</button>

	{#if open}
		<div transition:slide={{ duration: 300, easing: quintOut, axis: 'y' }}>
			<div class="mb-0.5 space-y-0.5">
				<slot name="content" />
			</div>
		</div>
	{/if}
</div>
