<script lang="ts">
	import { onMount, tick, getContext } from 'svelte';

	const i18n = getContext('i18n');

	import ShortcutsModal from '../chat/ShortcutsModal.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import HelpMenu from './Help/HelpMenu.svelte';

	let showShortcuts = false;
</script>

<div class=" hidden lg:flex fixed bottom-0 right-0 px-2 py-2 z-10">
	<button
		id="show-shortcuts-button"
		class="hidden"
		on:click={() => {
			showShortcuts = !showShortcuts;
		}}
	/>

	<HelpMenu
		showDocsHandler={() => {
			showShortcuts = !showShortcuts;
		}}
		showShortcutsHandler={() => {
			showShortcuts = !showShortcuts;
		}}
	>
		<Tooltip content={$i18n.t('Help')} placement="left">
			<button
				class="text-gray-600 dark:text-gray-300 bg-gray-300/20 size-5 flex items-center justify-center text-[0.7rem] rounded-full"
			>
				?
			</button>
		</Tooltip>
	</HelpMenu>
</div>

<ShortcutsModal bind:show={showShortcuts} />
