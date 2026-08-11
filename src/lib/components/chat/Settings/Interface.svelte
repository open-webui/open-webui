<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import InterfaceSettings from '$lib/components/common/InterfaceSettings.svelte';

	const dispatch = createEventDispatcher();
	const i18n: any = getContext('i18n');

	export let saveSettings: Function;
	export let personalSettingsValue: Record<string, any> = {};

	let interfaceSettings: any;
</script>

<form
	id="tab-interface"
	class="flex flex-col h-full justify-between text-sm"
	on:submit|preventDefault={async () => {
		await interfaceSettings?.save();
		dispatch('save');
	}}
>
	<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">{$i18n.t('Interface')}</h2>

	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		<InterfaceSettings bind:this={interfaceSettings} {saveSettings} {personalSettingsValue} />
	</div>

	<div class="shrink-0 flex justify-end text-sm font-normal">
		<button
			class="px-3.5 py-1.5 text-sm font-normal bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
