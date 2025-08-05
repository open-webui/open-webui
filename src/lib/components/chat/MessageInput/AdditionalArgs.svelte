<script lang="ts">
	import XMark from '../../icons/XMark.svelte';
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let additionalArgs = {};
	export let onReset: () => void = () => {};
</script>

{#if additionalArgs && typeof additionalArgs === 'object' && Object.keys(additionalArgs).length > 0}
	<div
		class="flex items-center justify-between w-full p-2 bg-gray-50 dark:bg-gray-800 rounded-lg mb-2"
	>
		{#if additionalArgs.editPaths && additionalArgs.editPaths.length > 0}
			<div class="flex-1 text-sm text-gray-700 dark:text-gray-300 pr-2">
				{additionalArgs.editPaths[0]}
			</div>
		{/if}
		<button
			class="flex-shrink-0 p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-full transition-colors"
			on:click={onReset}
			aria-label="Reset additional args"
			title="Reset additional args"
		>
			<XMark className="size-4" />
		</button>
	</div>
{/if}
