<script lang="ts">
	import { getBackendConfig } from '$lib/apis';
	import { setDefaultPromptSuggestions } from '$lib/apis/configs';
	import Switch from '$lib/components/common/Switch.svelte';
	import { config, functions, models, settings, tools, user } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import ManageModal from './Personalization/ManageModal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let saveSettings: Function;

	let tab = 'tools';
	let selectedId = '';

	$: if (tab) {
		selectedId = '';
	}
	onMount(async () => {});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		dispatch('save');
	}}
>
	<div class="flex flex-col pr-1.5 overflow-y-scroll max-h-[25rem]">
		<div class="flex text-center text-sm font-medium rounded-xl bg-transparent/10 p-1 mb-2">
			<button
				class="w-full rounded-lg p-1.5 {tab === 'tools' ? 'bg-gray-50 dark:bg-gray-850' : ''}"
				type="button"
				on:click={() => {
					tab = 'tools';
				}}>{$i18n.t('Tools')}</button
			>

			<button
				class="w-full rounded-lg p-1 {tab === 'functions' ? 'bg-gray-50 dark:bg-gray-850' : ''}"
				type="button"
				on:click={() => {
					tab = 'functions';
				}}>{$i18n.t('Functions')}</button
			>
		</div>

		<div class="space-y-1 px-1">
			<div class="flex gap-2">
				<div class="flex-1">
					<select
						class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
						bind:value={selectedId}
						on:change={async () => {
							await tick();
						}}
					>
						<option value="" selected disabled class="bg-gray-100 dark:bg-gray-700"
							>{$i18n.t('Select a tool/function')}</option
						>

						{#each $tools as tool, toolIdx}
							<option value={tool.id} class="bg-gray-100 dark:bg-gray-700">{tool.name}</option>
						{/each}
					</select>
				</div>
			</div>
		</div>

		<div>
			<div class="flex items-center justify-between mb-1" />
		</div>
	</div>

	<div class="flex justify-end text-sm font-medium">
		<button
			class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
