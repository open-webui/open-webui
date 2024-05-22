<script lang="ts">
	import { user, chats, settings, showSettings, chatId, tags, showFilesListSidebar } from '$lib/stores';
	import { onMount, getContext } from 'svelte';

	const i18n = getContext('i18n');

	import { WEBUI_BASE_URL } from '$lib/constants';
	import Tooltip from '../common/Tooltip.svelte';

	const BREAKPOINT = 1678;

	let navElement;

	onMount(async () => {
		showFilesListSidebar.set(window.innerWidth > BREAKPOINT);

		let touchstart;
		let touchend;

		function checkDirection() {
			const screenWidth = window.innerWidth;
			const swipeDistance = Math.abs(touchend.screenX - touchstart.screenX);
			
			if (touchstart.clientX < 40 && swipeDistance >= screenWidth / 8) {
				if (touchend.screenX < touchstart.screenX) {
					showFilesListSidebar.set(false);
				}
				if (touchend.screenX > touchstart.screenX) {
					showFilesListSidebar.set(true);
				}
			}
		}

		const onTouchStart = (e) => {
			touchstart = e.changedTouches[0];
			console.log(touchstart.clientX);
		};

		const onTouchEnd = (e) => {
			touchend = e.changedTouches[0];
			checkDirection();
		};

		const onResize = () => {
			if ($showFilesListSidebar && window.innerWidth < BREAKPOINT) {
				showFilesListSidebar.set(false);
			}
		};

		window.addEventListener('touchstart', onTouchStart);
		window.addEventListener('touchend', onTouchEnd);
		window.addEventListener('resize', onResize);

		return () => {
			window.removeEventListener('touchstart', onTouchStart);
			window.removeEventListener('touchend', onTouchEnd);
			window.removeEventListener('resize', onResize);
		};
	});

</script>

<div
	bind:this={navElement}
	id="sidebar"
	class="h-screen max-h-[100dvh] min-h-screen {$showFilesListSidebar
		? 'lg:fixed w-[260px]'
		: '-translate-x-[-260px] w-[0px]'} bg-gray-50 text-gray-900 dark:bg-gray-950 dark:text-gray-200 text-sm transition fixed z-50 top-0 right-0 rounded-r-2xl
        "
	data-state={$showFilesListSidebar}
>
	<div
		id="sidebar-handle"
		class="fixed right-0 top-[50dvh] -translate-y-1/2 transition-transform translate-x-[-255px] md:translate-x-[-260px] rotate-0"
	>
		<Tooltip
			placement="right"
			content={`${$showFilesListSidebar ? $i18n.t('Close') : $i18n.t('Open')} ${$i18n.t('sidebar')}`}
			touch={false}
		>
			<button
				id="sidebar-toggle-button"
				class=" group"
				on:click={() => {
					showFilesListSidebar.set(!$showFilesListSidebar);
				}}
				><span class="" data-state="closed"
					><div
						class="flex h-[72px] w-8 items-center justify-center opacity-50 group-hover:opacity-100 transition"
					>
						<div class="flex h-6 w-6 flex-col items-center">
							<div
								class="h-3 w-1 rounded-full bg-[#0f0f0f] dark:bg-white rotate-0 translate-y-[0.15rem] {$showFilesListSidebar
									? 'group-hover:rotate-[-15deg]'
									: 'group-hover:rotate-[15deg]'}"
							/>
							<div
								class="h-3 w-1 rounded-full bg-[#0f0f0f] dark:bg-white rotate-0 translate-y-[-0.15rem] {$showFilesListSidebar
									? 'group-hover:rotate-[15deg]'
									: 'group-hover:rotate-[-15deg]'}"
							/>
						</div>
					</div>
				</span>
			</button>
		</Tooltip>
	</div>
	<div
		class="py-2.5 my-auto flex flex-col h-screen max-h-[100dvh] w-[260px] {$showFilesListSidebar
			? ''
			: 'invisible'}"
	>
		<div class="px-2 flex justify-center space-x-2">
			<a
				id="sidebar-new-chat-button"
				class="flex-grow flex justify-between rounded-xl px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-900 transition"
				href="/"
			>
				<div class="flex self-center">
					<div class="self-center mr-1.5">
						<img
							src="{WEBUI_BASE_URL}/static/favicon.png"
							class=" size-6 -translate-x-1.5 rounded-full"
							alt="logo"
						/>
					</div>

					<div class=" self-center font-medium text-sm">{$i18n.t('Files List')}</div>
				</div>

				
			</a>
		</div>

		<div class="px-2 flex justify-center mt-0.5">
			<a
				class="flex-grow flex space-x-3 rounded-xl px-3.5 py-2 hover:bg-gray-100 dark:hover:bg-gray-900 transition"
				href="/"
			>
				<div class="flex self-center">
					<div class=" self-center font-medium text-sm">1. File.docx</div>
				</div>
			</a>
		</div>

		<div class="px-2 flex justify-center mt-0.5">
			<a
				class="flex-grow flex space-x-3 rounded-xl px-3.5 py-2 hover:bg-gray-100 dark:hover:bg-gray-900 transition"
				href="/"
			>
				<div class="flex self-center">
					<div class=" self-center font-medium text-sm">2. File.pdf</div>
				</div>
			</a>
		</div>

		<div class="px-2 flex justify-center mt-0.5">
			<a
				class="flex-grow flex space-x-3 rounded-xl px-3.5 py-2 hover:bg-gray-100 dark:hover:bg-gray-900 transition"
				href="/"
			>
				<div class="flex self-center">
					<div class=" self-center font-medium text-sm">3. File.xlsx</div>
				</div>
			</a>
		</div>

		<div class="px-2 flex justify-center mt-0.5">
			<a
				class="flex-grow flex space-x-3 rounded-xl px-3.5 py-2 hover:bg-gray-100 dark:hover:bg-gray-900 transition"
				href="/"
			>
				<div class="flex self-center">
					<div class=" self-center font-medium text-sm">4. xxxx.text</div>
				</div>
			</a>
		</div>


	</div>

</div>

<style>
	.scrollbar-none:active::-webkit-scrollbar-thumb,
	.scrollbar-none:focus::-webkit-scrollbar-thumb,
	.scrollbar-none:hover::-webkit-scrollbar-thumb {
		visibility: visible;
	}
	.scrollbar-none::-webkit-scrollbar-thumb {
		visibility: hidden;
	}
</style>
