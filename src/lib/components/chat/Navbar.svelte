<script lang="ts">
	import { getContext, type Snippet } from 'svelte';

	import {
		WEBUI_NAME,
		banners,
		chatId,
		config,
		mobile,
		selectedFolder,
		selectedTerminalId,
		showSidebar,
		showTabs,
		temporaryChat,
		user
	} from '$lib/stores';

	import { slide } from 'svelte/transition';

	import Tooltip from '../common/Tooltip.svelte';
	import AdjustmentsHorizontal from '../icons/AdjustmentsHorizontal.svelte';

	import PencilSquare from '../icons/PencilSquare.svelte';
	import Banner from '../common/Banner.svelte';
	import Sidebar from '../icons/Sidebar.svelte';

	import ChatBubbleDotted from '../icons/ChatBubbleDotted.svelte';
	import ChatBubbleDottedChecked from '../icons/ChatBubbleDottedChecked.svelte';

	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import ChatPlus from '../icons/ChatPlus.svelte';
	import ChatCheck from '../icons/ChatCheck.svelte';
	import SplitPanel from '../icons/SplitPanel.svelte';
	import { isTemporaryChatId } from '$lib/utils/chatId';
	import ChatParticipants from '$lib/components/common/ChatParticipants.svelte';

	const i18n: any = getContext('i18n');

	export let initNewChat: Function;
	export let onTemporaryChange: ((value: boolean) => void) | null = null;
	export let liveParticipants: { id: string; name: string }[] = [];
	export let scrollTop = 0;

	export let chat: any;
	export let history: any;
	export let title = '';
	export let tabbed = false;
	export let tabTitleEditor: Snippet | undefined = undefined;
	export let tabActions: Snippet | undefined = undefined;
	export let tabBarActions: Snippet | undefined = undefined;
	/** The chat menu, owned by Chat so main and side chats share it. */
	export let chatMenu: Snippet | undefined = undefined;
	$: tabActions = renderChatActions;
	$: tabBarActions = renderTabBarActions;
	export let onSaveTempChat: () => {};
	export let deleteChatHandler: (id: string) => void;

	let closedBannerIds = [];

	const getDismissedBannerIds = (): string[] => {
		try {
			return JSON.parse(localStorage.getItem('dismissedBannerIds') ?? '[]');
		} catch {
			return [];
		}
	};
</script>

{#snippet renderTemporaryChatToggle()}
	{#if $user?.role === 'user' ? ($user?.permissions?.chat?.temporary ?? true) && !($user?.permissions?.chat?.temporary_enforced ?? false) : true}
		{#if !chat?.id}
			<Tooltip content={$i18n.t(`Temporary Chat`)}>
				<button
					class="flex size-6 cursor-pointer items-center justify-center rounded-lg text-base-500 transition hover:bg-base-50/40 hover:text-base-700 dark:text-base-400 dark:hover:bg-base-800/40 dark:hover:text-base-200"
					id="temporary-chat-button"
					on:click={() => onTemporaryChange?.(!$temporaryChat)}
					aria-label={$i18n.t(`Temporary Chat`)}
				>
					{#if $temporaryChat}
						<ChatBubbleDottedChecked className="size-4" strokeWidth="1.5" />
					{:else}
						<ChatBubbleDotted className="size-4" strokeWidth="1.5" />
					{/if}
				</button>
			</Tooltip>
		{/if}
	{/if}
{/snippet}

{#snippet renderTabBarActions()}
	{@render renderTemporaryChatToggle()}
	{#if liveParticipants.length > 0}
		<div class="flex h-6 shrink-0 items-center px-1">
			<ChatParticipants participants={liveParticipants} mode="presence" avatarClass="size-4" />
		</div>
	{/if}
{/snippet}

{#snippet renderChatActions()}
	{#if !tabbed}{@render renderTemporaryChatToggle()}{/if}
	{#if $user?.role === 'user' ? ($user?.permissions?.chat?.temporary ?? true) && !($user?.permissions?.chat?.temporary_enforced ?? false) : true}
		{#if chat?.id && $temporaryChat}
			<Tooltip content={$i18n.t(`Save Chat`)}>
				<button
					class="flex size-6 cursor-pointer items-center justify-center rounded-lg text-base-500 transition hover:bg-base-50/40 hover:text-base-700 dark:text-base-400 dark:hover:bg-base-800/40 dark:hover:text-base-200"
					id="save-temporary-chat-button"
					on:click={async () => {
						onSaveTempChat();
					}}
					aria-label={$i18n.t(`Save Chat`)}
				>
					<ChatCheck className="size-4.5" strokeWidth="1.5" />
				</button>
			</Tooltip>
		{/if}
	{/if}

	{#if $mobile && !$temporaryChat && chat && chat.id}
		<Tooltip content={$i18n.t('New Chat')}>
			<button
				class="flex size-6 {$showSidebar
					? 'md:hidden'
					: ''} cursor-pointer items-center justify-center rounded-lg text-base-500 transition hover:bg-base-50/40 hover:text-base-700 dark:text-base-400 dark:hover:bg-base-800/40 dark:hover:text-base-200"
				on:click={() => {
					initNewChat();
				}}
				aria-label={$i18n.t('New Chat')}
			>
				<ChatPlus className="size-4" strokeWidth="1.5" />
			</button>
		</Tooltip>
	{/if}

	{#if !tabbed && liveParticipants.length > 0}
		<div class="flex h-6 shrink-0 items-center px-1">
			<ChatParticipants participants={liveParticipants} mode="presence" avatarClass="size-4" />
		</div>
	{/if}

	{@render chatMenu?.()}
{/snippet}

<button
	id="new-chat-button"
	class="hidden"
	on:click={() => {
		initNewChat();
	}}
	aria-label={$i18n.t('New Chat')}
/>

<nav
	class="sticky top-0 z-30 w-full {$mobile ? 'pt-1.5' : ''} {tabbed
		? 'pb-0.5'
		: $selectedFolder && !history.currentId
			? 'shrink-0 pb-1'
			: 'pb-1 -mb-12'} flex flex-col items-center drag-region"
>
	<div class:hidden={tabbed} class="flex items-center w-full {$mobile ? 'px-1.5' : 'pl-1.5 pr-1'}">
		<div
			id="navbar-bg-gradient-to-b"
			class="{chat?.id
				? 'visible'
				: 'invisible'} bg-linear-to-b via-40% to-97% from-white/90 via-white/50 to-transparent dark:from-base-900/90 dark:via-base-900/50 dark:to-transparent pointer-events-none absolute inset-0 -bottom-10 z-[-1]"
		></div>

		<div class=" flex max-w-full w-full mx-auto bg-transparent">
			<div class="flex items-center w-full max-w-full">
				{#if $mobile && !$showSidebar}
					<div class="mr-1 flex flex-none items-center self-start">
						<Tooltip content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}>
							<button
								id="sidebar-toggle-button"
								class="flex cursor-pointer rounded-lg text-base-500 transition hover:bg-base-50/40 hover:text-base-700 dark:text-base-400 dark:hover:bg-base-800/40 dark:hover:text-base-200"
								on:click={() => {
									showSidebar.set(!$showSidebar);
								}}
								aria-label={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
							>
								<div class="self-center p-1.5">
									<Sidebar className="size-4" />
								</div>
							</button>
						</Tooltip>
					</div>
				{/if}

				<div
					class="flex-1 min-w-0 overflow-hidden max-w-full md:mt-0.5 md:py-0.5 pl-1 {$showSidebar
						? 'ml-1'
						: ''}"
				>
					{#if chat?.id}
						<div class="flex max-w-full min-w-0 items-center gap-2 mr-2">
							{#if tabTitleEditor && !tabbed}
								{@render tabTitleEditor()}
							{:else}
								<h1
									class="min-w-0 truncate md:py-1 text-left text-[0.9375rem] font-normal text-base-700 dark:text-base-300"
								>
									{title || chat?.chat?.title || $i18n.t('New Chat')}
								</h1>
							{/if}

							{#if !$temporaryChat && ($user?.role === 'admin' || ($user?.permissions?.chat?.delete ?? true))}
								<button
									id="delete-chat-button"
									aria-label={$i18n.t('Delete')}
									class="hidden"
									on:click={() => {
										deleteChatHandler(chat.id);
									}}
								>
									<EllipsisHorizontal className="size-4.5" strokeWidth="1.5" />
								</button>
							{/if}
						</div>
					{:else}
						<h1 class="sr-only">{$i18n.t('New Chat')}</h1>
						<div class="pointer-events-none invisible flex max-w-full min-w-0 items-center gap-2">
							<div
								class="min-w-0 truncate md:py-1 text-left text-[0.9375rem] font-normal text-base-700 dark:text-base-300"
							>
								{$i18n.t('New Chat')}
							</div>
						</div>
					{/if}
				</div>

				<div class="lg:mr-1 flex flex-none items-center gap-2 self-center">
					<!-- <div class="md:hidden flex self-center w-[0.0625rem] h-5 mx-2 bg-base-300 dark:bg-stone-700" /> -->

					{#if !tabbed}{@render renderChatActions()}{/if}

					{#if history.currentId || $selectedTerminalId || $user?.role === 'admin' || ($user?.role === 'user' && ($user.permissions?.chat?.side_chat ?? false))}
						<Tooltip content={$i18n.t('Tabs')}>
							<button
								class="flex size-6 cursor-pointer items-center justify-center rounded-lg text-base-500 transition hover:bg-base-50/40 hover:text-base-700 dark:text-base-400 dark:hover:bg-base-800/40 dark:hover:text-base-200"
								on:click={() => showTabs.set(!$showTabs)}
								aria-label={$i18n.t('Tabs')}
								aria-expanded={!!$showTabs}
							>
								<SplitPanel className="size-4.5" strokeWidth="1" />
							</button>
						</Tooltip>
					{/if}
				</div>
			</div>
		</div>
	</div>

	{#if !tabbed && $temporaryChat && isTemporaryChatId($chatId)}
		<div class=" w-full z-30 text-center">
			<div class="text-xs text-base-500">{$i18n.t('Temporary Chat')}</div>
		</div>
	{/if}

	<div class="absolute top-full left-0 right-0 h-fit">
		{#if !$selectedFolder && !history.currentId && !$chatId && ($banners.length > 0 || ($config?.license_metadata?.type ?? null) === 'trial' || (($config?.license_metadata?.seats ?? null) !== null && $config?.user_count > $config?.license_metadata?.seats))}
			<div class=" w-full z-30">
				<div
					class=" flex flex-col gap-1 w-full max-h-28 overflow-y-auto overscroll-contain md:max-h-none md:overflow-visible"
				>
					{#if ($config?.license_metadata?.type ?? null) === 'trial'}
						<Banner
							className="px-[11px] rounded-lg"
							banner={{
								type: 'info',
								title: $i18n.t('Trial License'),
								content: $i18n.t(
									'You are currently using a trial license. Please contact support to upgrade your license.'
								)
							}}
						/>
					{/if}

					{#if ($config?.license_metadata?.seats ?? null) !== null && $config?.user_count > $config?.license_metadata?.seats}
						<Banner
							className="px-[11px] rounded-lg"
							banner={{
								type: 'error',
								title: $i18n.t('License Error'),
								content: $i18n.t(
									'Exceeded the number of seats in your license. Please contact support to increase the number of seats.'
								)
							}}
						/>
					{/if}

					{#each $banners.filter((b) => ![...getDismissedBannerIds(), ...closedBannerIds].includes(b.id)) as banner (banner.id)}
						<Banner
							className="px-[11px] rounded-lg"
							{banner}
							on:dismiss={(e) => {
								const bannerId = e.detail;

								if (banner.dismissible) {
									localStorage.setItem(
										'dismissedBannerIds',
										JSON.stringify(
											[bannerId, ...getDismissedBannerIds()].filter((id) =>
												$banners.find((b) => b.id === id)
											)
										)
									);
								} else {
									closedBannerIds = [...closedBannerIds, bannerId];
								}
							}}
						/>
					{/each}
				</div>
			</div>
		{/if}
	</div>
</nav>
