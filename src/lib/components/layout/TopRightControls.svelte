<script lang="ts">
	import { getContext } from 'svelte';
	import GlobalLanguageSelector from '../common/GlobalLanguageSelector.svelte';
	import UserMenu from './Sidebar/UserMenu.svelte';
	import {
		user,
		mobile,
		showControls,
		showArchivedChats,
		showSidebar,
		suggestionCycle,
		config
	} from '$lib/stores';
	import Tooltip from '../common/Tooltip.svelte';
	import AdjustmentsHorizontal from '../icons/AdjustmentsHorizontal.svelte';
	import PencilSquare from '../icons/PencilSquare.svelte';
	import QuestionMarkCircle from '../icons/QuestionMarkCircle.svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import HelpMenu from './Help/HelpMenu.svelte';
	import ShortcutsModal from '../chat/ShortcutsModal.svelte';
	import IssueModal from '../common/IssueModal.svelte';
	import SuggestionModal from '../common/SuggestionModal.svelte';

	export let shareEnabled = false;
	export let chat = null;

	const i18n = getContext('i18n');

	// Check if we're on a main route (/ or /c/)
	$: isControlsEnabled = $page.url.pathname === '/' || $page.url.pathname.includes('/c/');

	// Determine if we should show the new chat button
	$: showNewChatButton = !$showSidebar;

	// Reset controls when leaving main routes
	$: if (!isControlsEnabled && $showControls) {
		showControls.set(false);
	}

	const handleNewChat = () => {
		suggestionCycle.update((n) => n + 1);
		goto('/');
	};

	// Help functionality
	let showShortcuts = false;
	let showIssue = false;
	let showSuggestion = false;

	$: SurveyUrl = $i18n.language === 'fr-CA' ? $config?.survey_url_fr : $config?.survey_url;

	$: DocsUrl = $i18n.language === 'fr-CA' ? $config?.docs_url_fr : $config?.docs_url;
</script>

<div class="fixed top-0 right-0 px-2 py-[7px] z-50 flex items-center gap-1">
	<div class="flex items-center gap-1">
		{#if isControlsEnabled && $user && !$mobile && ($user.role === 'admin' || $user?.permissions?.chat?.controls)}
			<Tooltip content={$i18n.t('Controls')}>
				<button
					class="flex cursor-pointer px-2 py-2 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-850 transition"
					on:click={async () => {
						await showControls.set(!$showControls);
					}}
					aria-label="Controls"
				>
					<div class="m-auto self-center">
						<AdjustmentsHorizontal className="size-5" strokeWidth="0.5" />
					</div>
				</button>
			</Tooltip>
		{/if}

		{#if showNewChatButton}
			<Tooltip content={$i18n.t('New Chat')}>
				<button
					id="new-chat-button"
					class="flex cursor-pointer px-2 py-2 rounded-xl text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
					on:click={handleNewChat}
					aria-label="New Chat"
				>
					<div class="m-auto self-center">
						<PencilSquare className="size-5" strokeWidth="2" />
					</div>
				</button>
			</Tooltip>
		{/if}

		<!-- Help Button -->
		<div class="flex">
			<button
				id="show-shortcuts-button"
				class="hidden"
				on:click={() => {
					showShortcuts = !showShortcuts;
				}}
			/>
			<HelpMenu
				showDocsHandler={() => {
					window.open(DocsUrl, '_blank');
				}}
				showShortcutsHandler={() => {
					showShortcuts = !showShortcuts;
				}}
				showSurveyHandler={() => {
					window.open(SurveyUrl, '_blank');
				}}
				showIssueHandler={() => {
					showIssue = true;
				}}
				showSuggestionHandler={() => {
					showSuggestion = true;
				}}
			>
				<Tooltip content={$i18n.t('Help')} placement="bottom">
					<div class="group flex cursor-pointer p-2 rounded-xl bg-white dark:bg-gray-900 transition hover:bg-gray-100 dark:hover:bg-gray-800">
						<div class="flex items-center justify-center text-gray-900 dark:text-white">
							<QuestionMarkCircle className="size-5" strokeWidth="2" />
						</div>
					</div>
				</Tooltip>
			</HelpMenu>
		</div>

		<!-- Keep GlobalLanguageSelector and UserMenu together -->
		<div class="flex items-center gap-1">
			<GlobalLanguageSelector />
			{#if $user !== undefined}
				<div
					class="select-none flex rounded-xl p-2 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
				>
					<UserMenu
						role={$user.role}
						on:show={(e) => {
							if (e.detail === 'archived-chat') {
								showArchivedChats.set(true);
							}
						}}
					>
						<img
							src={$user.profile_image_url}
							class="size-6 object-cover rounded-full"
							alt="User profile"
							draggable="false"
						/>
					</UserMenu>
				</div>
			{/if}
		</div>
	</div>
</div>

<ShortcutsModal bind:show={showShortcuts} />
<IssueModal bind:show={showIssue} />
<SuggestionModal bind:show={showSuggestion} />
