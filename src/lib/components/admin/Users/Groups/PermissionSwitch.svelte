<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import Switch from '$lib/components/common/Switch.svelte';
	import Warning from '$lib/components/common/Warning.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	export let label = '';
	export let state = false;
	export let defaultState = undefined;
	export let tooltip = '';
</script>

<div class="flex w-full flex-col">
	{#if tooltip}
		<Tooltip content={tooltip} placement="top-start" className="flex w-full justify-between pr-2">
			<div class="self-center text-xs font-medium">
				{label}
			</div>
			<Switch bind:state />
		</Tooltip>
	{:else}
		<div class="flex w-full justify-between pr-2">
			<div class="self-center text-xs font-medium">
				{label}
			</div>
			<Switch bind:state />
		</div>
	{/if}
	{#if defaultState && !state}
		<div class="pb-1 pl-1 pr-2 pt-1">
			<Warning
				text={$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
			/>
		</div>
	{/if}
</div>