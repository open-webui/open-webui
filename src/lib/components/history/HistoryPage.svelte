<script lang="ts">
	import { onMount, getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	import { showSidebar, sidebarPinned, user, WEBUI_NAME } from '$lib/stores';
	import { getChatList, getPinnedChatList, deleteChatById, archiveChatById } from '$lib/apis/chats';
	import { getSpaces } from '$lib/apis/spaces';
	import type { Space } from '$lib/apis/spaces';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	interface Chat {
		id: string;
		title: string;
		updated_at: number;
		created_at: number;
		time_range?: string;
	}

	let loading = true;

	let pinnedChats: Chat[] = [];
	let recentChats: Chat[] = [];
	let privateSpaces: Space[] = [];
	let sharedSpaces: Space[] = [];

	let deleteChat: Chat | null = null;
	let showDeleteConfirm = false;

	onMount(async () => {
		await loadHistory();
	});

	const loadHistory = async () => {
		loading = true;

		try {
			const [pinnedRes, recentRes, privateRes, sharedRes] = await Promise.all([
				getPinnedChatList(localStorage.token).catch(() => []),
				getChatList(localStorage.token, 1, false, false).catch(() => []),
				getSpaces(localStorage.token, null, 'private').catch(() => ({ items: [], total: 0 })),
				getSpaces(localStorage.token, null, 'shared').catch(() => ({ items: [], total: 0 }))
			]);

			pinnedChats = pinnedRes || [];
			recentChats = (recentRes || []).slice(0, 10); // Show first 10 recent
			privateSpaces = privateRes.items || [];
			sharedSpaces = sharedRes.items || [];
		} catch (err) {
			console.error('Failed to load history:', err);
		}

		loading = false;
	};

	const formatTimeAgo = (timestamp: number): string => {
		const now = Date.now() / 1000;
		const diff = now - timestamp;

		if (diff < 60) return $i18n.t('Just now');
		if (diff < 3600) return $i18n.t('{{count}}m ago', { count: Math.floor(diff / 60) });
		if (diff < 86400) return $i18n.t('{{count}}h ago', { count: Math.floor(diff / 3600) });
		if (diff < 604800) return $i18n.t('{{count}}d ago', { count: Math.floor(diff / 86400) });

		const date = new Date(timestamp * 1000);
		return date.toLocaleDateString();
	};

	const handleDelete = async () => {
		if (!deleteChat) return;

		try {
			await deleteChatById(localStorage.token, deleteChat.id);
			toast.success($i18n.t('Chat deleted'));
			await loadHistory();
		} catch (err) {
			toast.error($i18n.t('Failed to delete chat'));
		}

		deleteChat = null;
		showDeleteConfirm = false;
	};

	const handleArchive = async (chat: Chat) => {
		try {
			await archiveChatById(localStorage.token, chat.id);
			toast.success($i18n.t('Chat archived'));
			await loadHistory();
		} catch (err) {
			toast.error($i18n.t('Failed to archive chat'));
		}
	};

	$: totalItems =
		pinnedChats.length + recentChats.length + privateSpaces.length + sharedSpaces.length;
</script>

<svelte:head>
	<title>{$i18n.t('History')} | {$WEBUI_NAME}</title>
</svelte:head>

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete Chat')}
	message={$i18n.t('Are you sure you want to delete this chat? This action cannot be undone.')}
	on:confirm={handleDelete}
/>

{#if loading}
	<div
		class="h-screen max-h-[100dvh] w-full flex items-center justify-center"
		class:md:max-w-[calc(100%-var(--sidebar-width))]={$sidebarPinned}
	>
		<div class="flex flex-col items-center gap-3">
			<Spinner className="size-6" />
			<span class="text-sm text-gray-400 dark:text-gray-500">{$i18n.t('Loading history...')}</span>
		</div>
	</div>
{:else}
	<div
		class="h-screen max-h-[100dvh] w-full flex flex-col"
		class:md:max-w-[calc(100%-var(--sidebar-width))]={$sidebarPinned}
	>
		<!-- Header -->
		<div
			class="sticky top-0 z-20 backdrop-blur-xl bg-white/80 dark:bg-gray-900/80 border-b border-gray-100 dark:border-gray-800/50"
		>
			<div class="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
				<div class="flex items-center gap-3">
					<h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
						{$i18n.t('History')}
					</h1>
				</div>

				<button
					class="px-3.5 py-1.5 rounded-lg bg-black dark:bg-white text-white dark:text-black hover:bg-gray-800 dark:hover:bg-gray-100 transition text-xs font-medium flex items-center gap-1.5"
					on:click={() => goto('/')}
				>
					<svg
						class="size-3.5"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
					>
						<path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
					</svg>
					{$i18n.t('New Chat')}
				</button>
			</div>
		</div>

		<!-- Content -->
		<div class="flex-1 overflow-y-auto">
			{#if totalItems === 0}
				<div class="flex flex-col items-center justify-center h-full px-4">
					<div class="text-center max-w-sm">
						<div class="text-5xl mb-4">💬</div>
						<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
							{$i18n.t('No history yet')}
						</h2>
						<p class="text-sm text-gray-500 dark:text-gray-400 leading-relaxed mb-6">
							{$i18n.t(
								'Your chat history will appear here. Start a conversation to see it in your history.'
							)}
						</p>
						<button
							class="px-4 py-2.5 rounded-xl bg-black dark:bg-white text-white dark:text-black hover:bg-gray-800 dark:hover:bg-gray-100 transition text-sm font-medium inline-flex items-center gap-2"
							on:click={() => goto('/')}
						>
							<svg
								class="size-4"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
							</svg>
							{$i18n.t('Start a conversation')}
						</button>
					</div>
				</div>
			{:else}
				<div class="max-w-6xl mx-auto px-4 sm:px-6 py-6 space-y-8">
					<!-- Pinned Chats -->
					{#if pinnedChats.length > 0}
						<section>
							<div class="flex items-center gap-2 mb-4">
								<svg
									class="size-4 text-amber-500 dark:text-amber-400"
									viewBox="0 0 24 24"
									fill="currentColor"
								>
									<path
										fill-rule="evenodd"
										d="M10.788 3.21c.448-1.077 1.976-1.077 2.424 0l2.082 5.006 5.404.434c1.164.093 1.636 1.545.749 2.305l-4.117 3.527 1.257 5.273c.271 1.136-.964 2.033-1.96 1.425L12 18.354 7.373 21.18c-.996.608-2.231-.29-1.96-1.425l1.257-5.273-4.117-3.527c-.887-.76-.415-2.212.749-2.305l5.404-.434 2.082-5.005Z"
										clip-rule="evenodd"
									/>
								</svg>
								<h2
									class="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500"
								>
									{$i18n.t('Pinned')}
								</h2>
							</div>
							<div class="space-y-1">
								{#each pinnedChats as chat (chat.id)}
									<a
										href="/c/{chat.id}"
										class="group flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
									>
										<div
											class="w-9 h-9 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0"
										>
											<svg
												class="size-4 text-gray-400 dark:text-gray-500"
												viewBox="0 0 24 24"
												fill="none"
												stroke="currentColor"
												stroke-width="1.5"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 0 1 .865-.501 48.172 48.172 0 0 0 3.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z"
												/>
											</svg>
										</div>
										<div class="min-w-0 flex-1">
											<h3
												class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate group-hover:text-gray-700 dark:group-hover:text-white transition"
											>
												{chat.title}
											</h3>
											<p class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
												{formatTimeAgo(chat.updated_at)}
											</p>
										</div>
										<div
											class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
										>
											<Tooltip content={$i18n.t('Archive')}>
								<button
									aria-label={$i18n.t('Archive')}
													class="p-1.5 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition"
													on:click|preventDefault|stopPropagation={() => handleArchive(chat)}
												>
													<svg
														class="size-4"
														viewBox="0 0 24 24"
														fill="none"
														stroke="currentColor"
														stroke-width="1.5"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															d="m20.25 7.5-.625 10.632a2.25 2.25 0 0 1-2.247 2.118H6.622a2.25 2.25 0 0 1-2.247-2.118L3.75 7.5m8.25 3v6.75m0 0-3-3m3 3 3-3M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125Z"
														/>
													</svg>
												</button>
											</Tooltip>
											<Tooltip content={$i18n.t('Delete')}>
								<button
									aria-label={$i18n.t('Delete')}
													class="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition"
													on:click|preventDefault|stopPropagation={() => {
														deleteChat = chat;
														showDeleteConfirm = true;
													}}
												>
													<svg
														class="size-4"
														viewBox="0 0 24 24"
														fill="none"
														stroke="currentColor"
														stroke-width="1.5"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
														/>
													</svg>
												</button>
											</Tooltip>
										</div>
									</a>
								{/each}
							</div>
						</section>
					{/if}

					<!-- Recent Chats -->
					{#if recentChats.length > 0}
						<section>
							<div class="flex items-center justify-between mb-4">
								<div class="flex items-center gap-2">
									<svg
										class="size-4 text-gray-400 dark:text-gray-500"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="1.5"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
										/>
									</svg>
									<h2
										class="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500"
									>
										{$i18n.t('Recent')}
									</h2>
									<span class="text-xs text-gray-300 dark:text-gray-600">{recentChats.length}</span>
								</div>
							</div>
							<div class="space-y-1">
								{#each recentChats as chat (chat.id)}
									<a
										href="/c/{chat.id}"
										class="group flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
									>
										<div
											class="w-9 h-9 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0"
										>
											<svg
												class="size-4 text-gray-400 dark:text-gray-500"
												viewBox="0 0 24 24"
												fill="none"
												stroke="currentColor"
												stroke-width="1.5"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 0 1 .865-.501 48.172 48.172 0 0 0 3.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z"
												/>
											</svg>
										</div>
										<div class="min-w-0 flex-1">
											<h3
												class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate group-hover:text-gray-700 dark:group-hover:text-white transition"
											>
												{chat.title}
											</h3>
											<p class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
												{formatTimeAgo(chat.updated_at)}
											</p>
										</div>
										<div
											class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
										>
											<Tooltip content={$i18n.t('Archive')}>
								<button
									aria-label={$i18n.t('Archive')}
													class="p-1.5 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition"
													on:click|preventDefault|stopPropagation={() => handleArchive(chat)}
												>
													<svg
														class="size-4"
														viewBox="0 0 24 24"
														fill="none"
														stroke="currentColor"
														stroke-width="1.5"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															d="m20.25 7.5-.625 10.632a2.25 2.25 0 0 1-2.247 2.118H6.622a2.25 2.25 0 0 1-2.247-2.118L3.75 7.5m8.25 3v6.75m0 0-3-3m3 3 3-3M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125Z"
														/>
													</svg>
												</button>
											</Tooltip>
											<Tooltip content={$i18n.t('Delete')}>
								<button
									aria-label={$i18n.t('Delete')}
													class="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition"
													on:click|preventDefault|stopPropagation={() => {
														deleteChat = chat;
														showDeleteConfirm = true;
													}}
												>
													<svg
														class="size-4"
														viewBox="0 0 24 24"
														fill="none"
														stroke="currentColor"
														stroke-width="1.5"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
														/>
													</svg>
												</button>
											</Tooltip>
										</div>
									</a>
								{/each}
							</div>
						</section>
					{/if}

					<!-- Private Spaces -->
					{#if privateSpaces.length > 0}
						<section>
							<div class="flex items-center justify-between mb-4">
								<div class="flex items-center gap-2">
									<svg
										class="size-4 text-gray-400 dark:text-gray-500"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="1.5"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z"
										/>
									</svg>
									<h2
										class="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500"
									>
										{$i18n.t('Private Spaces')}
									</h2>
									<span class="text-xs text-gray-300 dark:text-gray-600"
										>{privateSpaces.length}</span
									>
								</div>
								<a
									href="/spaces"
									class="text-xs text-accent-500 hover:text-accent-600 dark:text-accent-400 dark:hover:text-accent-300 transition"
								>
									{$i18n.t('View All')}
								</a>
							</div>
							<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
								{#each privateSpaces.slice(0, 6) as space (space.id)}
									<a
										href="/spaces/{space.slug}"
										class="group text-left p-4 rounded-xl border border-gray-200 dark:border-gray-700/60 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800/50 hover:border-gray-300 dark:hover:border-gray-600 transition-all"
									>
										<div class="flex items-start gap-3">
											{#if space.emoji}
												<span class="text-2xl flex-shrink-0 mt-0.5">{space.emoji}</span>
											{:else}
												<div
													class="w-8 h-8 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0 mt-0.5"
												>
													<svg
														class="size-4 text-gray-400 dark:text-gray-500"
														viewBox="0 0 24 24"
														fill="none"
														stroke="currentColor"
														stroke-width="1.5"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z"
														/>
													</svg>
												</div>
											{/if}
											<div class="min-w-0 flex-1">
												<h3
													class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate group-hover:text-gray-700 dark:group-hover:text-white transition"
												>
													{space.name}
												</h3>
												{#if space.description}
													<p class="text-xs text-gray-500 dark:text-gray-400 mt-1 truncate">
														{space.description}
													</p>
												{/if}
											</div>
										</div>
									</a>
								{/each}
							</div>
						</section>
					{/if}

					<!-- Shared Spaces -->
					{#if sharedSpaces.length > 0}
						<section>
							<div class="flex items-center justify-between mb-4">
								<div class="flex items-center gap-2">
									<svg
										class="size-4 text-gray-400 dark:text-gray-500"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="1.5"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z"
										/>
									</svg>
									<h2
										class="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500"
									>
										{$i18n.t('Shared Spaces')}
									</h2>
									<span class="text-xs text-gray-300 dark:text-gray-600">{sharedSpaces.length}</span
									>
								</div>
								<a
									href="/spaces"
									class="text-xs text-accent-500 hover:text-accent-600 dark:text-accent-400 dark:hover:text-accent-300 transition"
								>
									{$i18n.t('View All')}
								</a>
							</div>
							<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
								{#each sharedSpaces.slice(0, 6) as space (space.id)}
									<a
										href="/spaces/{space.slug}"
										class="group text-left p-4 rounded-xl border border-gray-200 dark:border-gray-700/60 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800/50 hover:border-gray-300 dark:hover:border-gray-600 transition-all"
									>
										<div class="flex items-start gap-3">
											{#if space.emoji}
												<span class="text-2xl flex-shrink-0 mt-0.5">{space.emoji}</span>
											{:else}
												<div
													class="w-8 h-8 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0 mt-0.5"
												>
													<svg
														class="size-4 text-gray-400 dark:text-gray-500"
														viewBox="0 0 24 24"
														fill="none"
														stroke="currentColor"
														stroke-width="1.5"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z"
														/>
													</svg>
												</div>
											{/if}
											<div class="min-w-0 flex-1">
												<h3
													class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate group-hover:text-gray-700 dark:group-hover:text-white transition"
												>
													{space.name}
												</h3>
												{#if space.description}
													<p class="text-xs text-gray-500 dark:text-gray-400 mt-1 truncate">
														{space.description}
													</p>
												{/if}
											</div>
										</div>
									</a>
								{/each}
							</div>
						</section>
					{/if}
				</div>
			{/if}
		</div>
	</div>
{/if}
