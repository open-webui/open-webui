<script lang="ts">
	import { getContext } from 'svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import type { WebSearchReadiness } from '$lib/utils/models';

	const i18n = getContext('i18n');

	export let readiness: WebSearchReadiness;

	// Hover details, built from the (stable) reason codes. The wording lives here, in a .svelte
	// file, so the i18n parser can extract it; the helper itself stays translation-free.
	// Referencing $i18n and readiness directly keeps this reactive to both language and model.
	$: details = [
		readiness.reasons.includes('size_low') || readiness.reasons.includes('size_experimental')
			? $i18n.t('Small local models are often unreliable at Web Search tool calls.')
			: '',
		readiness.reasons.includes('context_low') || readiness.reasons.includes('context_limited')
			? $i18n.t('A low context length can truncate web search results.')
			: '',
		$i18n.t('For more reliable agentic Web Search, use a 14B+ model with at least 8k context.')
	]
		.filter((line) => line !== '')
		.join('<br>');
</script>

{#if readiness.state === 'limited'}
	<Tooltip content={details} placement="top-start" className="w-fit">
		<div class="flex items-center gap-1.5 mt-1.5 text-xs text-yellow-600 dark:text-yellow-500">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="size-3.5 shrink-0"
				aria-hidden="true"
			>
				<path
					fill-rule="evenodd"
					d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z"
					clip-rule="evenodd"
				/>
			</svg>
			<span>{$i18n.t('Web Search may be unreliable on this model')}</span>
		</div>
	</Tooltip>
{/if}
