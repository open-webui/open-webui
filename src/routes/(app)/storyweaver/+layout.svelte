<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { WEBUI_NAME, showSidebar, mobile, user } from '$lib/stores';
	import { currentNovel, loadNovels, loadCurrentNovel } from '$lib/stores/sw';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		if (!$user) {
			goto('/');
			return;
		}

		// Charger le roman courant depuis la session backend
		// (appelé une fois depuis le layout racine)
		// @ts-ignore — token disponible sur le user object OpenWebUI
		const token = localStorage.getItem('token');
		if (token) {
			await Promise.all([loadCurrentNovel(token), loadNovels(token)]);
		}

		loaded = true;
	});

	$: isNovels = $page.url.pathname === '/storyweaver';
	$: isKB = $page.url.pathname.includes('/kb');
</script>

<svelte:head>
	<title>StoryWeaver • {$WEBUI_NAME}</title>
</svelte:head>

{#if loaded}
	<div
		class="relative flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
			? 'md:max-w-[calc(100%-var(--sidebar-width))]'
			: ''} max-w-full"
	>
		<!-- Nav bar -->
		<nav class="px-2.5 pt-1.5 backdrop-blur-xl drag-region select-none">
			<div class="flex items-center gap-1">
				{#if $mobile}
					<div class="{$showSidebar ? 'md:hidden' : ''} self-center flex flex-none items-center">
						<Tooltip
							content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
							interactive={true}
						>
							<button
								id="sidebar-toggle-button"
								class="cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
								aria-label={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
								on:click={() => showSidebar.set(!$showSidebar)}
							>
								<div class="self-center p-1.5"><Sidebar /></div>
							</button>
						</Tooltip>
					</div>
				{/if}

				<div class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium rounded-full bg-transparent py-1 touch-auto pointer-events-auto">
					<!-- 📚 Romans -->
					<a
						draggable="false"
						href="/storyweaver"
						aria-current={isNovels ? 'page' : null}
						class="min-w-fit p-1.5 flex items-center gap-1.5 {isNovels
							? ''
							: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition select-none"
					>
						<span>📚</span>
						<span>Romans</span>
					</a>

					<!-- 📖 Knowledge Base (si roman sélectionné) -->
					{#if $currentNovel}
						<a
							draggable="false"
							href="/storyweaver/{$currentNovel.id}/kb"
							aria-current={isKB ? 'page' : null}
							class="min-w-fit p-1.5 flex items-center gap-1.5 {isKB
								? ''
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition select-none"
						>
							<span>📖</span>
							<span>Base de Connaissances</span>
						</a>
					{/if}
				</div>

				<!-- Roman courant badge -->
				{#if $currentNovel}
					<div class="ml-auto flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 pr-2">
						<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 font-medium">
							✍️ {$currentNovel.title}
						</span>
					</div>
				{/if}
			</div>
		</nav>

		<!-- Contenu des pages -->
		<div class="pb-1 px-3 md:px-[18px] flex-1 max-h-full overflow-y-auto" id="storyweaver-container">
			<slot />
		</div>
	</div>
{/if}
