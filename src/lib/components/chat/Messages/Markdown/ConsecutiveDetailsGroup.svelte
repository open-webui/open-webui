<script lang="ts">
	import { decode } from 'html-entities';
	import { getContext } from 'svelte';
	import { slide } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';

	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';
	import CheckCircle from '$lib/components/icons/CheckCircle.svelte';
	import FullHeightIframe from '$lib/components/common/FullHeightIframe.svelte';

	import { settings } from '$lib/stores';
	import { getToolFamilySummary } from '$lib/utils/toolPresentation';

	const i18n = getContext('i18n');

	export let id = '';
	export let tokens: Array<{
		summary?: string;
		attributes?: {
			type?: string;
			name?: string;
			done?: string;
			duration?: string;
			embeds?: string;
			arguments?: string;
		};
	}> = [];

	export let messageDone = true;

	let open = false;

	function parseJSONString(str: string) {
		try {
			return parseJSONString(JSON.parse(str));
		} catch (e) {
			return str;
		}
	}

	$: toolCallCount = tokens.filter((t) => t?.attributes?.type === 'tool_calls').length;
	$: reasoningCount = tokens.filter((t) => t?.attributes?.type === 'reasoning').length;
	$: hasPending =
		!messageDone &&
		tokens.some((t) => t?.attributes?.done !== undefined && t?.attributes?.done !== 'true');

	$: codeInterpreterCount = tokens.filter((t) => t?.attributes?.type === 'code_interpreter').length;

	// Collect all embeds from tool_calls tokens
	$: allEmbeds = (() => {
		const result: Array<{ name: string; embed: string; args: string }> = [];
		for (const t of tokens) {
			if (t?.attributes?.type !== 'tool_calls') continue;
			const raw = decode(t.attributes?.embeds ?? '');
			try {
				const parsed = parseJSONString(raw);
				if (Array.isArray(parsed) && parsed.length > 0) {
					for (const embed of parsed) {
						result.push({
							name: t.attributes?.name ?? '',
							embed,
							args: decode(t.attributes?.arguments ?? '')
						});
					}
				}
			} catch {}
		}
		return result;
	})();

	$: summaryText = (() => {
		const parts = [];
		const joinSummaryParts = (items: string[]) =>
			items
				.map((item, index) => (index === 0 ? item : item.charAt(0).toLowerCase() + item.slice(1)))
				.join(', ');

		if (toolCallCount > 0) {
			const toolNames = tokens
				.filter((t) => t?.attributes?.type === 'tool_calls')
				.map((t) => t?.attributes?.name ?? 'tool');

			const familySummary = getToolFamilySummary(toolNames, hasPending, $i18n.t.bind($i18n));
			if (familySummary) {
				parts.push(familySummary);
			}
		}

		if (codeInterpreterCount > 0) {
			if (hasPending) {
				parts.push($i18n.t('Running analysis'));
			} else if (codeInterpreterCount === 1) {
				parts.push($i18n.t('Ran {{COUNT}} analysis', { COUNT: codeInterpreterCount }));
			} else {
				parts.push($i18n.t('Ran {{COUNT}} analyses', { COUNT: codeInterpreterCount }));
			}
		}

		if (reasoningCount > 0 && toolCallCount === 0 && codeInterpreterCount === 0) {
			parts.push(hasPending ? $i18n.t('Thinking...') : $i18n.t('Thought'));
		}

		return parts.length > 0
			? joinSummaryParts(parts)
			: hasPending
				? $i18n.t('Exploring')
				: $i18n.t('Explored');
	})();
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
					>{summaryText}</span
				>
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

	{#if allEmbeds.length > 0}
		{#each allEmbeds as embedItem, idx}
			<div id={`${id}-embed-${idx}`}>
				<FullHeightIframe
					src={embedItem.embed}
					args={embedItem.args}
					allowScripts={true}
					allowForms={$settings?.iframeSandboxAllowForms ?? false}
					allowSameOrigin={$settings?.iframeSandboxAllowSameOrigin ?? false}
					allowPopups={true}
				/>
			</div>
		{/each}
	{/if}
</div>
