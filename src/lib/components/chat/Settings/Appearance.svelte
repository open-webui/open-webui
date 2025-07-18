<script lang="ts">
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { settings } from '$lib/stores';
	
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');
	
	export let saveSettings: Function;
	
	const saveHandler = () => {
		// Future appearance settings can be saved here
		dispatch('save');
	};
</script>

<form
	id="tab-appearance"
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		saveHandler();
	}}
>
	<div class="space-y-3 overflow-y-scroll max-h-[28rem] lg:max-h-full">
		<div class="space-y-6">
			<!-- Other appearance settings can go here -->
			<div class="text-center text-gray-500 dark:text-gray-400">
				<p>Background patterns have been moved to General settings.</p>
			</div>
		</div>
	</div>
	
	<!-- Save Button -->
	<div class="flex justify-end text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>