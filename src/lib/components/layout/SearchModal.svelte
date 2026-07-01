<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onDestroy, onMount, tick } from 'svelte';
	const i18n = getContext('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import SearchInput from './Sidebar/SearchInput.svelte';
	import {
		getChatById,
		getChatList,
		getChatListBySearchText,
		cloneChatById,
		deleteChatById,
		archiveChatById,
		updateChatById,
		updateChatFolderIdById,
		getPinnedChatList,
		getAllTags
	} from '$lib/apis/chats';
	import Spinner from '../common/Spinner.svelte';

	import dayjs from '$lib/dayjs';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import calendar from 'dayjs/plugin/calendar';
	import Loader from '../common/Loader.svelte';
	import { createMessagesList } from '$lib/utils';
	import { getOutputText } from '$lib/components/chat/Messages/structuredOutput';
	import {
		config,
		user,
		chats,
		chatId as currentChatId,
		pinnedChats,
		currentChatPage,
		tags
	} from '$lib/stores';
	import Messages from '../chat/Messages.svelte';
	import { goto } from '$app/navigation';
	import PencilSquare from '../icons/PencilSquare.svelte';
	import PageEdit from '../icons/PageEdit.svelte';

	import ChatMenu from './Sidebar/ChatMenu.svelte';
	import ShareChatModal from '../chat/ShareChatModal.svelte';
	import DeleteConfirmDialog from '../common/ConfirmDialog.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Sparkles from '../icons/Sparkles.svelte';
	import ArchiveBox from '../icons/ArchiveBox.svelte';
	import GarbageBin from '../icons/GarbageBin.svelte';
	import { generateTitle } from '$lib/apis';
	dayjs.extend(calendar);
	dayjs.extend(localizedFormat);

	export let show = false;
	export let onClose = () => {};

	let showShareChatModal = false;
	let showDeleteConfirm = false;
	let menuChatId = '';
	let menuChatTitle = '';

	let editingChatId = null;
	let editingChatTitle = '';

	let shiftKey = false;

	const onShiftKeyDown = (e) => {
		if (e.key === 'Shift') shiftKey = true;
	};

	const onShiftKeyUp = (e) => {
		if (e.key === 'Shift') shiftKey = false;
	};
	let generating = false;

	const refreshSidebar = async () => {
		currentChatPage.set(1);
		await chats.set(await getChatList(localStorage.token, $currentChatPage));
		await pinnedChats.set(await getPinnedChatList(localStorage.token));
	};

	const cloneChatHandler = async (id) => {
		const chat = chatList?.find((c) => c.id === id);
		const res = await cloneChatById(
			localStorage.token,
			id,
			$i18n.t('Clone of {{TITLE}}', {
				TITLE: chat?.title ?? 'Chat'
			})
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			await refreshSidebar();
			await searchHandler();
		}
	};

	const archiveChatHandler = async (id) => {
		try {
			await archiveChatById(localStorage.token, id);

			chatList = chatList?.filter((c) => c.id !== id) ?? null;

			if ($currentChatId === id) {
				await goto('/');
				currentChatId.set('');
			}

			await refreshSidebar();
			toast.success($i18n.t('Chat archived.'));
		} catch (error) {
			toast.error($i18n.t('Failed to archive chat.'));
		}
	};

	const deleteChatHandler = async (id) => {
		const res = await deleteChatById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			chatList = chatList?.filter((c) => c.id !== id) ?? null;
			tags.set(await getAllTags(localStorage.token));

			if ($currentChatId === id) {
				await goto('/');
				currentChatId.set('');
			}

			await refreshSidebar();
		}
	};

	const moveChatHandler = async (chatId, folderId) => {
		if (chatId && folderId) {
			const res = await updateChatFolderIdById(localStorage.token, chatId, folderId).catch(
				(error) => {
					toast.error(`${error}`);
					return null;
				}
			);

			if (res) {
				chatList = chatList?.filter((c) => c.id !== chatId) ?? null;
				await refreshSidebar();
				toast.success($i18n.t('Chat moved successfully'));
			}
		}
	};

	const renameHandler = async (id) => {
		editingChatId = id;
		editingChatTitle = chatList?.find((c) => c.id === id)?.title ?? '';

		await tick();
		const input = document.getElementById(`search-chat-title-input-${id}`);
		if (input) {
			input.focus();
			input.select();
		}
	};

	const confirmRename = async () => {
		if (!editingChatId) return;

		const trimmed = editingChatTitle.trim();
		if (trimmed === '') {
			toast.error($i18n.t('Title cannot be an empty string.'));
			return;
		}

		await updateChatById(localStorage.token, editingChatId, { title: trimmed });

		if (chatList) {
			chatList = chatList.map((c) => (c.id === editingChatId ? { ...c, title: trimmed } : c));
		}

		editingChatId = null;
		editingChatTitle = '';
		await refreshSidebar();
	};

	const cancelRename = () => {
		editingChatId = null;
		editingChatTitle = '';
	};

	const generateTitleHandler = async () => {
		if (!editingChatId || generating) return;

		generating = true;
		const chat = await getChatById(localStorage.token, editingChatId).catch(() => null);

		if (!chat) {
			toast.error($i18n.t('Failed to load chat'));
			generating = false;
			return;
		}

		const chatContent = chat.chat;
		const history = chatContent?.history;
		let msgList = [];

		if (history?.messages && history?.currentId) {
			msgList = createMessagesList(history, history.currentId).map((m: any) => ({
				role: m.role,
				content: getOutputText(m.output) || m.content || ''
			}));
		} else {
			msgList = (chatContent?.messages ?? []).map((m: any) => ({
				role: m.role,
				content: getOutputText(m.output) || m.content || ''
			}));
		}

		let model = '';
		if (history?.messages && history?.currentId) {
			let currentId = history.currentId;
			while (currentId) {
				const msg = history.messages[currentId];
				if (!msg) break;
				if (msg.role === 'assistant' && msg.model) {
					model = msg.model;
					break;
				}
				currentId = msg.parentId;
			}
		}
		if (!model) {
			model = chatContent?.models?.at(0) ?? '';
		}

		editingChatTitle = '';

		const generatedTitle = await generateTitle(localStorage.token, model, msgList).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		if (generatedTitle) {
			editingChatTitle = generatedTitle;
		}

		generating = false;

		if (generatedTitle) {
			await confirmRename();
		}
	};

	let actions = [
		{
			label: $i18n.t('Start a new conversation'),
			onClick: async () => {
				await goto(`/${query ? `?q=${query}` : ''}`);
				show = false;
				onClose();
			},
			icon: PencilSquare
		}
	];

	let query = '';
	let page = 1;

	let chatList = null;

	let chatListLoading = false;
	let allChatsLoaded = false;

	let searchDebounceTimeout;

	let selectedIdx = null;
	let selectedChat = null;

	let selectedModels = [''];
	let history = null;
	let messages = null;

	const searchFilterPrefixes = ['tag:', 'folder:', 'pinned:', 'archived:', 'shared:'];

	const getSnippetQuery = (query: string) => {
		return query
			.trim()
			.split(/\s+/)
			.filter(
				(word) => !searchFilterPrefixes.some((prefix) => word.toLowerCase().startsWith(prefix))
			)
			.join(' ')
			.trim();
	};

	const getHighlightedSnippet = (snippet: string, query: string) => {
		const match = getSnippetQuery(query).toLowerCase();
		const matchIndex = match ? snippet.toLowerCase().indexOf(match) : -1;

		if (matchIndex === -1) {
			return [{ text: snippet, highlight: false }];
		}

		const start = Math.max(matchIndex - 60, 0);
		const end = Math.min(matchIndex + match.length + 80, snippet.length);
		const visibleSnippet = `${start > 0 ? '...' : ''}${snippet.slice(start, end)}${
			end < snippet.length ? '...' : ''
		}`;
		const index = visibleSnippet.toLowerCase().indexOf(match);

		return [
			{ text: visibleSnippet.slice(0, index), highlight: false },
			{ text: visibleSnippet.slice(index, index + match.length), highlight: true },
			{ text: visibleSnippet.slice(index + match.length), highlight: false }
		].filter((part) => part.text);
	};

	$: if (!chatListLoading && chatList) {
		loadChatPreview(selectedIdx);
	}

	const loadChatPreview = async (selectedIdx) => {
		if (!chatList || chatList.length === 0 || selectedIdx === null) {
			selectedChat = null;
			messages = null;
			history = null;
			selectedModels = [''];
			return;
		}

		const selectedChatIdx = selectedIdx - actions.length;
		if (selectedChatIdx < 0 || selectedChatIdx >= chatList.length) {
			selectedChat = null;
			messages = null;
			history = null;
			selectedModels = [''];
			return;
		}

		const chatId = chatList[selectedChatIdx].id;

		const chat = await getChatById(localStorage.token, chatId).catch(async (error) => {
			return null;
		});

		if (chat) {
			if (chat?.chat?.history) {
				selectedModels =
					(chat?.chat?.models ?? undefined) !== undefined
						? chat?.chat?.models
						: [chat?.chat?.models ?? ''];

				history = chat?.chat?.history;
				messages = createMessagesList(chat?.chat?.history, chat?.chat?.history?.currentId);

				// scroll to the bottom of the messages container
				await tick();
				const messagesContainerElement = document.getElementById('chat-preview');
				if (messagesContainerElement) {
					messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
				}
			} else {
				messages = [];
			}
		} else {
			toast.error($i18n.t('Failed to load chat preview'));
			selectedChat = null;
			messages = null;
			history = null;
			selectedModels = [''];
			return;
		}
	};

	const searchHandler = async () => {
		if (!show) {
			return;
		}

		if (searchDebounceTimeout) {
			clearTimeout(searchDebounceTimeout);
		}

		page = 1;
		chatList = null;
		if (query === '') {
			chatList = await getChatList(localStorage.token, page);
		} else {
			searchDebounceTimeout = setTimeout(async () => {
				chatList = await getChatListBySearchText(localStorage.token, query, page);

				if ((chatList ?? []).length === 0) {
					allChatsLoaded = true;
				} else {
					allChatsLoaded = false;
				}
			}, 500);
		}

		selectedChat = null;
		messages = null;
		history = null;
		selectedModels = [''];

		if ((chatList ?? []).length === 0) {
			allChatsLoaded = true;
		} else {
			allChatsLoaded = false;
		}
	};

	const loadMoreChats = async () => {
		chatListLoading = true;
		page += 1;

		let newChatList = [];

		if (query) {
			newChatList = await getChatListBySearchText(localStorage.token, query, page);
		} else {
			newChatList = await getChatList(localStorage.token, page);
		}

		// once the bottom of the list has been reached (no results) there is no need to continue querying
		allChatsLoaded = newChatList.length === 0;

		if (newChatList.length > 0) {
			const existingIds = new Set(chatList.map((c) => c.id));
			const uniqueNewChats = newChatList.filter((c) => !existingIds.has(c.id));
			chatList = [...chatList, ...uniqueNewChats];
		}

		chatListLoading = false;
	};

	$: if (show) {
		searchHandler();
	} else {
		editingChatId = null;
		editingChatTitle = '';
		generating = false;
	}

	const onKeyDown = (e) => {
		// Ignore keydown fired while confirming an IME composition (e.g. Japanese/Chinese/Korean)
		// so confirming the composition with Enter doesn't trigger search actions (#26172).
		if (e.isComposing || e.keyCode === 229) {
			return;
		}

		const searchOptions = document.getElementById('search-options-container');
		if (searchOptions || !show) {
			return;
		}

		// Don't handle navigation/activation keys while editing a chat title
		if (editingChatId) {
			return;
		}

		if (e.code === 'Escape') {
			show = false;
			onClose();
		} else if (e.code === 'Enter') {
			const item = document.querySelector(`[data-arrow-selected="true"]`);
			if (item) {
				item?.click();
				show = false;
			}

			return;
		} else if (e.code === 'ArrowDown') {
			const searchInput = document.getElementById('search-input');

			if (searchInput) {
				// check if focused on the search input
				if (document.activeElement === searchInput) {
					searchInput.blur();
					selectedIdx = 0;
					return;
				}
			}

			selectedIdx = Math.min(selectedIdx + 1, (chatList ?? []).length - 1 + actions.length);
		} else if (e.code === 'ArrowUp') {
			if (selectedIdx === 0) {
				const searchInput = document.getElementById('search-input');

				if (searchInput) {
					// check if focused on the search input
					if (document.activeElement !== searchInput) {
						searchInput.focus();
						selectedIdx = 0;
						return;
					}
				}
			}

			selectedIdx = Math.max(selectedIdx - 1, 0);
		}

		const item = document.querySelector(`[data-arrow-selected="true"]`);
		item?.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
	};

	onMount(() => {
		actions = [
			...actions,
			...(($config?.features?.enable_notes ?? false) &&
			($user?.role === 'admin' || ($user?.permissions?.features?.notes ?? true))
				? [
						{
							label: $i18n.t('Create a new note'),
							onClick: async () => {
								await goto(`/notes?content=${query}`);
								show = false;
								onClose();
							},
							icon: PageEdit
						}
					]
				: [])
		];

		document.addEventListener('keydown', onKeyDown);
		document.addEventListener('keydown', onShiftKeyDown);
		document.addEventListener('keyup', onShiftKeyUp);
	});

	onDestroy(() => {
		if (searchDebounceTimeout) {
			clearTimeout(searchDebounceTimeout);
		}
		document.removeEventListener('keydown', onKeyDown);
		document.removeEventListener('keydown', onShiftKeyDown);
		document.removeEventListener('keyup', onShiftKeyUp);
	});
</script>

<ShareChatModal bind:show={showShareChatModal} chatId={menuChatId} />

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete chat?')}
	on:confirm={() => {
		deleteChatHandler(menuChatId);
	}}
>
	<div class="text-sm text-gray-500 flex-1 line-clamp-3">
		{$i18n.t('This will delete')} <span class="font-semibold">{menuChatTitle}</span>.
	</div>
</DeleteConfirmDialog>

<Modal size="xl" bind:show>
	<div class="py-3 dark:text-gray-300 text-gray-700">
		<div class="px-4 pb-1.5">
			<SearchInput
				bind:value={query}
				on:input={searchHandler}
				placeholder={$i18n.t('Search')}
				showClearButton={true}
				onFocus={() => {
					selectedIdx = null;
					messages = null;
				}}
				onKeydown={(e) => {
					console.log('e', e);

					if (e.code === 'Enter' && (chatList ?? []).length > 0) {
						const item = document.querySelector(`[data-arrow-selected="true"]`);
						if (item) {
							item?.click();
						}

						show = false;
						return;
					} else if (e.code === 'ArrowDown') {
						selectedIdx = Math.min(selectedIdx + 1, (chatList ?? []).length - 1 + actions.length);
					} else if (e.code === 'ArrowUp') {
						selectedIdx = Math.max(selectedIdx - 1, 0);
					} else {
						selectedIdx = 0;
					}

					const item = document.querySelector(`[data-arrow-selected="true"]`);
					item?.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
				}}
			/>
		</div>

		<!-- <hr class="border-gray-50 dark:border-gray-850/30 my-1" /> -->

		<div class="flex px-4 pb-1">
			<div
				class="flex flex-col overflow-y-auto h-96 md:h-[40rem] max-h-full scrollbar-hidden w-full flex-1 pr-2"
			>
				<div class="w-full text-xs text-gray-500 dark:text-gray-500 font-medium pb-2 px-2">
					{$i18n.t('Actions')}
				</div>

				{#each actions as action, idx (action.label)}
					<button
						class=" w-full flex items-center rounded-xl text-sm py-2 px-3 hover:bg-gray-50 dark:hover:bg-gray-850 {selectedIdx ===
						idx
							? 'bg-gray-50 dark:bg-gray-850'
							: ''}"
						data-arrow-selected={selectedIdx === idx ? 'true' : undefined}
						dragabble="false"
						on:mouseenter={() => {
							selectedIdx = idx;
						}}
						on:click={async () => {
							await action.onClick();
						}}
					>
						<div class="pr-2">
							<svelte:component this={action.icon} />
						</div>
						<div class=" flex-1 text-left">
							<div class="text-ellipsis line-clamp-1 w-full">
								{$i18n.t(action.label)}
							</div>
						</div>
					</button>
				{/each}

				{#if chatList}
					<hr class="border-gray-50 dark:border-gray-850/30 my-3" />

					{#if chatList.length === 0}
						<div class="text-xs text-gray-500 dark:text-gray-400 text-center px-5 py-4">
							{$i18n.t('No results found')}
						</div>
					{/if}

					{#each chatList as chat, idx (chat.id)}
						{#if idx === 0 || (idx > 0 && chat.time_range !== chatList[idx - 1].time_range)}
							<div
								class="w-full text-xs text-gray-500 dark:text-gray-500 font-medium {idx === 0
									? ''
									: 'pt-5'} pb-2 px-2"
							>
								{$i18n.t(chat.time_range)}
								<!-- localisation keys for time_range to be recognized from the i18next parser (so they don't get automatically removed):
							{$i18n.t('Today')}
							{$i18n.t('Yesterday')}
							{$i18n.t('Previous 7 days')}
							{$i18n.t('Previous 30 days')}
							{$i18n.t('January')}
							{$i18n.t('February')}
							{$i18n.t('March')}
							{$i18n.t('April')}
							{$i18n.t('May')}
							{$i18n.t('June')}
							{$i18n.t('July')}
							{$i18n.t('August')}
							{$i18n.t('September')}
							{$i18n.t('October')}
							{$i18n.t('November')}
							{$i18n.t('December')}
							-->
							</div>
						{/if}

						<!-- svelte-ignore a11y-no-static-element-interactions -->
						<div
							class="w-full flex justify-between items-center rounded-xl text-sm py-2 pl-3 pr-32 hover:bg-gray-50 dark:hover:bg-gray-850 group/item relative {selectedIdx ===
							idx + actions.length
								? 'bg-gray-50 dark:bg-gray-850'
								: ''}"
							data-arrow-selected={selectedIdx === idx + actions.length ? 'true' : undefined}
							on:mouseenter={() => {
								selectedIdx = idx + actions.length;
							}}
						>
							{#if editingChatId === chat.id}
								<div class="flex-1 min-w-0">
									<input
										id="search-chat-title-input-{chat.id}"
										bind:value={editingChatTitle}
										class="bg-transparent w-full outline-none"
										placeholder={generating ? $i18n.t('Generating...') : ''}
										disabled={generating}
										on:keydown={(e) => {
											e.stopPropagation();
											if (e.key === 'Enter') {
												e.preventDefault();
												confirmRename();
											} else if (e.key === 'Escape') {
												e.preventDefault();
												cancelRename();
											}
										}}
										on:blur={() => {
											if (!generating) {
												confirmRename();
											}
										}}
									/>
								</div>

								<div class="flex items-center shrink-0 pl-1">
									<Tooltip content={$i18n.t('Generate')}>
										<button
											class="self-center dark:hover:text-white transition disabled:cursor-not-allowed"
											disabled={generating}
											on:mousedown|preventDefault={() => {}}
											on:click|preventDefault|stopPropagation={() => {
												generateTitleHandler();
											}}
										>
											{#if generating}
												<Spinner className="size-4" />
											{:else}
												<Sparkles strokeWidth="2" />
											{/if}
										</button>
									</Tooltip>
								</div>
							{:else}
								<a
									class="flex-1 min-w-0"
									href="/c/{chat.id}"
									draggable="false"
									on:click={async () => {
										await goto(`/c/${chat.id}`);
										show = false;
										onClose();
									}}
								>
									<div class="text-ellipsis line-clamp-1 w-full">
										{chat?.title}
									</div>
									{#if chat?.snippet}
										<div class="text-xs text-gray-500 dark:text-gray-400 line-clamp-2 mt-0.5">
											{#each getHighlightedSnippet(chat.snippet, query) as part}
												{#if part.highlight}
													<mark
														class="rounded bg-yellow-200/70 px-0.5 text-inherit dark:bg-yellow-500/30"
													>
														{part.text}
													</mark>
												{:else}
													{part.text}
												{/if}
											{/each}
										</div>
									{/if}
								</a>
							{/if}

							<div
								class="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-3 pl-6 shrink-0"
							>
								<div class="text-gray-500 dark:text-gray-400 text-xs">
									{$i18n.t(
										dayjs(chat?.updated_at * 1000).calendar(null, {
											sameDay: '[Today]',
											nextDay: '[Tomorrow]',
											nextWeek: 'dddd',
											lastDay: '[Yesterday]',
											lastWeek: '[Last] dddd',
											sameElse: 'L'
										})
									)}
								</div>

								{#if editingChatId !== chat.id}
									{#if shiftKey}
										<div class="flex items-center space-x-1.5">
											<Tooltip content={$i18n.t('Archive')} className="flex items-center">
												<button
													class="self-center dark:hover:text-white transition"
													on:click|stopPropagation={() => {
														archiveChatHandler(chat.id);
													}}
													type="button"
												>
													<ArchiveBox className="size-4 translate-y-[0.5px]" strokeWidth="2" />
												</button>
											</Tooltip>

											<Tooltip content={$i18n.t('Delete')}>
												<button
													class="self-center dark:hover:text-white transition"
													on:click|stopPropagation={() => {
														deleteChatHandler(chat.id);
													}}
													type="button"
												>
													<GarbageBin strokeWidth="2" />
												</button>
											</Tooltip>
										</div>
									{:else}
										<div class="flex items-center">
											<ChatMenu
												chatId={chat.id}
												shareHandler={() => {
													menuChatId = chat.id;
													showShareChatModal = true;
												}}
												{moveChatHandler}
												cloneChatHandler={() => {
													cloneChatHandler(chat.id);
												}}
												archiveChatHandler={() => {
													archiveChatHandler(chat.id);
												}}
												renameHandler={() => {
													renameHandler(chat.id);
												}}
												deleteHandler={() => {
													menuChatId = chat.id;
													menuChatTitle = chat.title;
													showDeleteConfirm = true;
												}}
												onClose={() => {}}
												onPinChange={async () => {
													await refreshSidebar();
													await searchHandler();
												}}
											>
												<button
													aria-label="Chat Menu"
													class="self-center dark:hover:text-white transition"
												>
													<svg
														xmlns="http://www.w3.org/2000/svg"
														viewBox="0 0 16 16"
														fill="currentColor"
														class="w-4 h-4"
													>
														<path
															d="M2 8a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0ZM6.5 8a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0ZM12.5 6.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3Z"
														/>
													</svg>
												</button>
											</ChatMenu>
										</div>
									{/if}
								{/if}
							</div>
						</div>
					{/each}

					{#if !allChatsLoaded}
						<Loader
							on:visible={(e) => {
								if (!chatListLoading) {
									loadMoreChats();
								}
							}}
						>
							<div class="w-full flex justify-center py-4 text-xs animate-pulse items-center gap-2">
								<Spinner className=" size-4" />
								<div class=" ">{$i18n.t('Loading...')}</div>
							</div>
						</Loader>
					{/if}
				{:else}
					<div class="w-full h-full flex justify-center items-center">
						<Spinner className="size-5" />
					</div>
				{/if}
			</div>
			<div
				id="chat-preview"
				class="hidden md:flex md:flex-1 w-full overflow-y-auto h-96 md:h-[40rem] scrollbar-hidden @container"
			>
				{#if messages === null}
					<div
						class="w-full h-full flex justify-center items-center text-gray-500 dark:text-gray-400 text-sm"
					>
						{$i18n.t('Select a conversation to preview')}
					</div>
				{:else}
					<div class="w-full h-full flex flex-col">
						<Messages
							className="h-full flex pt-4 pb-8 w-full"
							chatId={`chat-preview-${selectedChat?.id ?? ''}`}
							user={$user}
							readOnly={true}
							{selectedModels}
							bind:history
							bind:messages
							autoScroll={true}
							sendMessage={() => {}}
							continueResponse={() => {}}
							regenerateResponse={() => {}}
						/>
					</div>
				{/if}
			</div>
		</div>
	</div>
</Modal>
