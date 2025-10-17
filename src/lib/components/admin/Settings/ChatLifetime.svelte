<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const dispatch = createEventDispatcher();
	const i18n = getContext<Writable<i18nType>>('i18n');

	import {
		getChatLifetimeConfig,
		updateChatLifetimeConfig,
		triggerComprehensiveCleanup,
		getChatLifetimeSchedule,
		type ChatLifetimeConfig,
		type ChatLifetimeScheduleInfo
	} from '$lib/apis/configs';
	import { getChatList } from '$lib/apis/chats';
	import { getPinnedChatList } from '$lib/apis/chats';
	import { chats, currentChatPage, pinnedChats } from '$lib/stores';

	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	export let saveHandler: Function;

	let loading = false;
	let cleanupLoading = false;
	let showConfirm = false;
	let confirmTitle = '';
	let confirmMessage = '';
	let onConfirm = () => {};
	let scheduleInfo: ChatLifetimeScheduleInfo | null = null;
	let config: ChatLifetimeConfig = {
		enabled: false,
		days: 30,
		preserve_pinned: true,
		preserve_archived: false
	};

	const updateChatLifetimeConfigHandler = async () => {
		loading = true;

		try {
			await updateChatLifetimeConfig(localStorage.token, config);
			toast.success($i18n.t('Chat lifetime settings updated successfully'));

			// Refresh schedule info after config update
			await loadScheduleInfo();

			if (saveHandler) {
				saveHandler();
			}
		} catch (error) {
			toast.error($i18n.t('Failed to update chat lifetime settings'));
			console.error('Error updating chat lifetime config:', error);
		}

		loading = false;
	};

	const loadScheduleInfo = async () => {
		if (localStorage.token) {
			try {
				scheduleInfo = await getChatLifetimeSchedule(localStorage.token);
			} catch (error) {
				console.error('Error loading schedule info:', error);
				scheduleInfo = null;
			}
		}
	};

	const runComprehensiveCleanup = async () => {
		cleanupLoading = true;
		try {
			// For comprehensive cleanup, the server handles the conditional logic
			// based on CHAT_LIFETIME_ENABLED config, so we just pass the current settings
			const result = await triggerComprehensiveCleanup(localStorage.token, {
				max_age_days: config.days,
				include_chat_cleanup: true,
				preserve_pinned: config.preserve_pinned,
				preserve_archived: config.preserve_archived
			});

			if (result) {
				const chatsDeleted = result.cleanup_results?.expired_chats?.chats_deleted || 0;
				const webSearchCleaned =
					result.cleanup_results?.web_search_vectors?.collections_cleaned || 0;
				const filesCleaned = result.cleanup_results?.chat_files?.files_deleted || 0;

				if (chatsDeleted > 0 || webSearchCleaned > 0 || filesCleaned > 0) {
					if (config.enabled) {
						toast.success(
							$i18n.t(
								'Comprehensive cleanup completed: {{chatsDeleted}} expired chats deleted, {{webSearchCleaned}} web search collections cleaned, {{filesCleaned}} files cleaned',
								{
									chatsDeleted,
									webSearchCleaned,
									filesCleaned
								}
							)
						);
					} else {
						toast.success(
							$i18n.t(
								'Comprehensive cleanup completed: {{chatsDeleted}} chats deleted (all chats), {{webSearchCleaned}} web search collections cleaned, {{filesCleaned}} files cleaned',
								{
									chatsDeleted,
									webSearchCleaned,
									filesCleaned
								}
							)
						);
					}
				} else {
					if (config.enabled) {
						toast.success($i18n.t('Comprehensive cleanup completed - no expired data found'));
					} else {
						toast.success($i18n.t('Comprehensive cleanup completed - no data found for cleanup'));
					}
				}

				// Only refresh the chat list if chats were actually deleted
				if (chatsDeleted > 0) {
					const updatedChats = await getChatList(localStorage.token, $currentChatPage);
					const updatedPinnedChats = await getPinnedChatList(localStorage.token);
					chats.set(updatedChats);
					pinnedChats.set(updatedPinnedChats);

					// Force a reactive update by updating both stores in the next tick
					setTimeout(() => {
						chats.update((c) => [...c]);
						pinnedChats.update((c) => [...c]);
					}, 100);
				}
			}
		} catch (error) {
			toast.error($i18n.t('Comprehensive cleanup failed'));
			console.error('Error running comprehensive cleanup:', error);
		}
		cleanupLoading = false;
	};

	const confirmComprehensiveCleanup = () => {
		showConfirm = true;
		confirmTitle = $i18n.t('Run Comprehensive Cleanup');
		confirmMessage = $i18n.t(
			'Are you sure you want to run comprehensive cleanup? Since chat lifetime is disabled, this will clean up ALL chats, orphaned files, and old vector collections (except Knowledge Bases).'
		);
		onConfirm = runComprehensiveCleanup;
	};

	onMount(async () => {
		if (localStorage.token) {
			try {
				config = await getChatLifetimeConfig(localStorage.token);
				await loadScheduleInfo();
			} catch (error) {
				console.error('Error loading chat lifetime config:', error);
				toast.error($i18n.t('Failed to load chat lifetime settings'));
			}
		}
	});
</script>

<ConfirmDialog
	bind:show={showConfirm}
	title={confirmTitle}
	message={confirmMessage}
	on:confirm={onConfirm}
/>

<div class="flex flex-col h-full justify-between space-y-3 text-sm">
	<div class=" space-y-3">
		<div>
			<div class="text-sm font-medium">{$i18n.t('Chat Lifetime Management')}</div>
			<div class=" text-xs text-gray-400">
				{$i18n.t(
					'Configure automatic cleanup of old conversations to manage storage and comply with retention policies.'
				)}
			</div>
		</div>

		<hr class=" dark:border-gray-850" />

		<div class=" space-y-3">
			<div class="flex flex-col w-full space-y-2">
				<div class="flex justify-between items-center">
					<div class="text-xs font-medium">
						{$i18n.t('Enable Chat Lifetime')}
					</div>
					<Switch
						state={config.enabled}
						on:change={(e) => {
							config.enabled = e.detail;
						}}
					/>
				</div>
				<Tooltip
					content={$i18n.t(
						'When enabled, chats older than the specified number of days will be automatically deleted during cleanup operations.'
					)}
				>
					<div class="text-xs text-gray-400">
						{$i18n.t(
							'When enabled, chats older than the specified number of days will be automatically deleted during cleanup operations.'
						)}
					</div>
				</Tooltip>
			</div>

			{#if config.enabled}
				<div class=" space-y-1">
					<div class="flex w-full">
						<div class="flex w-full justify-between">
							<div class="self-center text-xs font-medium">{$i18n.t('Chat Lifetime (Days)')}</div>
							<div class="self-center text-xs text-gray-400">
								{$i18n.t('{{COUNT}} days', { COUNT: config.days })}
							</div>
						</div>
					</div>

					<div class="flex w-full">
						<div class="flex w-full">
							<input
								class="w-full rounded-lg py-1.5 px-4 text-sm bg-transparent border dark:border-gray-600"
								type="range"
								bind:value={config.days}
								min="1"
								max="365"
								step="1"
							/>
						</div>
					</div>
					<div class="text-xs text-gray-400">
						{$i18n.t(
							'Chats older than this number of days will be eligible for deletion. Default is 30 days.'
						)}
					</div>
				</div>

				<div class="flex flex-col w-full space-y-2">
					<div class="flex justify-between items-center">
						<div class="text-xs font-medium">
							{$i18n.t('Preserve Pinned Chats')}
						</div>
						<Switch
							state={config.preserve_pinned}
							on:change={(e) => {
								config.preserve_pinned = e.detail;
							}}
						/>
					</div>
					<div class="text-xs text-gray-400">
						{$i18n.t(
							'When enabled, pinned chats will be excluded from automatic cleanup even if they exceed the lifetime threshold.'
						)}
					</div>
				</div>

				<div class="flex flex-col w-full space-y-2">
					<div class="flex justify-between items-center">
						<div class="text-xs font-medium">
							{$i18n.t('Preserve Archived Chats')}
						</div>
						<Switch
							state={config.preserve_archived}
							on:change={(e) => {
								config.preserve_archived = e.detail;
							}}
						/>
					</div>
					<div class="text-xs text-gray-400">
						{$i18n.t(
							'When enabled, archived chats will be excluded from automatic cleanup even if they exceed the lifetime threshold.'
						)}
					</div>
				</div>
			{/if}
		</div>

		<hr class=" dark:border-gray-850" />

		<div class=" space-y-3">
			<div class="text-xs font-medium">
				{#if config.enabled}
					{$i18n.t('Automatic Cleanup Operations')}
				{:else}
					{$i18n.t('Manual Cleanup Operations')}
				{/if}
			</div>
			<div class=" text-xs text-gray-400">
				{#if config.enabled}
					{$i18n.t(
						'Automatic cleanup is active based on your configured lifetime settings. No manual intervention required.'
					)}
				{:else}
					{$i18n.t('Manual cleanup required since automatic lifetime management is disabled.')}
				{/if}
			</div>

			{#if config.enabled && scheduleInfo}
				<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 space-y-2">
					<div class="text-xs font-medium text-gray-700 dark:text-gray-300">
						{$i18n.t('Automation Status')}
					</div>
					<div class="text-xs text-gray-600 dark:text-gray-400 space-y-1">
						<div>
							{$i18n.t('Status')}:
							<span class="font-medium capitalize"
								>{$i18n.t(
									scheduleInfo.status.charAt(0).toUpperCase() + scheduleInfo.status.slice(1)
								) || scheduleInfo.status}</span
							>
						</div>
						{#if scheduleInfo.schedule}
							<div>
								{$i18n.t('Schedule')}:
								<span class="font-medium"
									>{$i18n.t(scheduleInfo.schedule) || scheduleInfo.schedule}</span
								>
							</div>
						{/if}
						{#if scheduleInfo.next_run}
							<div>
								{$i18n.t('Next Run')}:
								<span class="font-medium">{new Date(scheduleInfo.next_run).toLocaleString()}</span>
							</div>
						{/if}
						{#if scheduleInfo.error}
							<div class="text-red-600 dark:text-red-400">
								{$i18n.t('Error')}: {scheduleInfo.error}
							</div>
						{/if}
					</div>
				</div>
			{/if}

			{#if !config.enabled}
				<div class="flex w-full">
					<button
						class="w-full px-3.5 py-1.5 text-sm font-medium bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 transition rounded-full disabled:opacity-50"
						disabled={cleanupLoading}
						on:click={confirmComprehensiveCleanup}
					>
						{#if cleanupLoading}
							<div class="flex items-center justify-center space-x-2">
								<div
									class="animate-spin rounded-full h-3 w-3 border-b-2 border-gray-700 dark:border-gray-200"
								></div>
								<span>{$i18n.t('Running Cleanup...')}</span>
							</div>
						{:else}
							{$i18n.t('Run Comprehensive Cleanup')}
						{/if}
					</button>
				</div>

				<div class="text-sm text-gray-400">
					<div>
						{$i18n.t(
							'Comprehensive Cleanup: Removes ALL chats, ALL files, and ALL vector collections except Knowledge Bases immediately (lifetime disabled)'
						)}
					</div>
				</div>
			{/if}
		</div>
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			on:click={updateChatLifetimeConfigHandler}
			disabled={loading}
		>
			{loading ? $i18n.t('Saving...') : $i18n.t('Save')}
		</button>
	</div>
</div>
