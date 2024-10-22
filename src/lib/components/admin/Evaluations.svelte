<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Plus from '../icons/Plus.svelte';
	import Collapsible from '../common/Collapsible.svelte';
	import Switch from '../common/Switch.svelte';
	import ChevronUp from '../icons/ChevronUp.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';
	const i18n = getContext('i18n');

	let loaded = false;
	let evaluationEnabled = true;

	let showModels = false;

	onMount(() => {
		loaded = true;
	});
</script>

{#if loaded}
	<div class="my-0.5 gap-1 flex flex-col md:flex-row justify-between">
		<div class="flex md:self-center text-lg font-medium px-0.5">
			{$i18n.t('Leaderboard')}
		</div>
	</div>
{/if}
