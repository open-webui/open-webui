<script lang="ts">
	import { v4 as uuidv4 } from 'uuid';

	import { getContext, onMount } from 'svelte';
	import { models } from '$lib/stores';

	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import { stringify } from 'postcss';
	import { getPipelines } from '$lib/apis';
	const i18n: Writable<i18nType> = getContext('i18n');

	export let saveHandler: Function;

	let pipelines = [];
	let selectedPipelineIdx = 0;

	onMount(async () => {
		pipelines = await getPipelines(localStorage.token);
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		saveHandler();
	}}
>
	<div class=" space-y-3 pr-1.5 overflow-y-scroll max-h-80 h-full">
		<div class=" space-y-3 pr-1.5">
			<div class="flex w-full justify-between mb-2">
				<div class=" self-center text-sm font-semibold">
					{$i18n.t('Pipeline Valves')}
				</div>
			</div>
			<div class="flex flex-col space-y-1">
				{#each pipelines as pipeline}
					<div class=" flex justify-between">
						{JSON.stringify(pipeline)}
					</div>
				{/each}
			</div>
		</div>
	</div>
	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
			type="submit"
		>
			Save
		</button>
	</div>
</form>
