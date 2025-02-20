<script lang="ts">
	import { onMount, tick, getContext } from 'svelte';

	const i18n = getContext('i18n');

	import ShortcutsModal from '../chat/ShortcutsModal.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import HelpMenu from './Help/HelpMenu.svelte';

	let showShortcuts = false;

	const getSurveyUrl = () => {
		const locale = localStorage.getItem('locale') || 'en-GB';
		const langPrefix = locale.startsWith('fr') ? 'fr' : 'en';
		return `https://forms-formulaires.alpha.canada.ca/${langPrefix}/id/cm6tm7j9h005cyr69fq8g86xd`;
	};

	const getDocsUrl = () => {
		const locale = localStorage.getItem('locale') || 'en-GB';
		return locale.startsWith('fr')
			? 'https://gcxgce.sharepoint.com/teams/1000538/SitePages/CANchat_FR.aspx'
			: 'https://gcxgce.sharepoint.com/teams/1000538/SitePages/CANchat.aspx';
	};
</script>

<div class=" hidden lg:flex fixed bottom-0 right-0 px-2 py-2 z-20">
	<button
		id="show-shortcuts-button"
		class="hidden"
		on:click={() => {
			showShortcuts = !showShortcuts;
		}}
	/>

	<HelpMenu
		showDocsHandler={() => {
			window.open(getDocsUrl(), '_blank');
		}}
		showShortcutsHandler={() => {
			showShortcuts = !showShortcuts;
		}}
		showSurveyHandler={() => {
			window.open(getSurveyUrl(), '_blank');
		}}
	>
		<Tooltip content={$i18n.t('Help')} placement="left">
			<div
				class="text-gray-600 dark:text-gray-300 bg-gray-300/20 size-5 flex items-center justify-center text-[0.7rem] rounded-full"
			>
				?
			</div>
		</Tooltip>
	</HelpMenu>
</div>

<ShortcutsModal bind:show={showShortcuts} />
