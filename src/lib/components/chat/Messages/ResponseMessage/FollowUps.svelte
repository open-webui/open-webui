<script lang="ts">
	import { onMount, tick, getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let followUps: string[] = [];
	export let onClick: (followUp: string) => void = () => {};
</script>

<div class="mt-2">
	<div class="text-xs text-gray-500 font-medium">
		{$i18n.t('Follow up')}
	</div>

	<div class="flex flex-col text-left gap-1 mt-1.5">
		{#each followUps as followUp, idx (idx)}
			<button
				class=" mr-2 py-1 bg-transparent text-left text-xs"
				on:click={() => onClick(followUp)}
				title={followUp}
				aria-label={followUp}
			>
				{followUp}
			</button>
		{/each}
	</div>
</div>
