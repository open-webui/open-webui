<script lang="ts">
	// @ts-ignore
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { downloadDatabase } from '$lib/apis/utils';
	import { onMount, getContext } from 'svelte';
	import {
		config,
		user,
		chats,
		scrollPaginationEnabled,
		currentChatPage,
		pinnedChats
	} from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import {
		getAllUserChats,
		archiveAllChats,
		deleteAllChats,
		getAllChats,
		getChatList,
		getPinnedChatList,
		importChats
	} from '$lib/apis/chats';
	import { getAllUsers } from '$lib/apis/users';
	import { exportConfig, importConfig } from '$lib/apis/configs';
	import { getImportOrigin, convertOpenAIChats } from '$lib/utils';
	import ArchivedChatsModal from '$lib/components/layout/ArchivedChatsModal.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';

	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let saveHandler: () => void;

	// Collapsible section states
	let expandedSections = {
		myChats: true,
		database: true
	};

	// User data controls state
	let importFiles: FileList | undefined;
	let showArchiveConfirm = false;
	let showDeleteConfirm = false;
	let showArchivedChatsModal = false;
	let chatImportInputElement: HTMLInputElement;

	// Handle chat import
	$: if (importFiles) {
		console.log(importFiles);

		let reader = new FileReader();
		reader.onload = (event) => {
			let chatsData = JSON.parse(event.target?.result as string);
			console.log(chatsData);
			if (getImportOrigin(chatsData) == 'openai') {
				try {
					chatsData = convertOpenAIChats(chatsData);
				} catch (error) {
					console.log('Unable to import chats:', error);
				}
			}
			importChatsHandler(chatsData);
		};

		if (importFiles.length > 0) {
			reader.readAsText(importFiles[0]);
		}
	}

	const importChatsHandler = async (_chats: any[]) => {
		const res = await importChats(
			localStorage.token,
			_chats.map((chat) => {
				if (chat.chat) {
					return {
						chat: chat.chat,
						meta: chat.meta ?? {},
						pinned: false,
						folder_id: chat?.folder_id ?? null,
						created_at: chat?.created_at ?? null,
						updated_at: chat?.updated_at ?? null
					};
				} else {
					return {
						chat: chat,
						meta: {},
						pinned: false,
						folder_id: null,
						created_at: chat?.created_at ?? null,
						updated_at: chat?.updated_at ?? null
					};
				}
			})
		);
		if (res) {
			toast.success(`Successfully imported ${res.length} chats.`);
		}

		currentChatPage.set(1);
		await chats.set(await getChatList(localStorage.token, $currentChatPage));
		pinnedChats.set(await getPinnedChatList(localStorage.token));
		scrollPaginationEnabled.set(true);
	};

	const exportChats = async () => {
		let blob = new Blob([JSON.stringify(await getAllChats(localStorage.token))], {
			type: 'application/json'
		});
		saveAs(blob, `chat-export-${Date.now()}.json`);
	};

	const archiveAllChatsHandler = async () => {
		await goto('/');
		await archiveAllChats(localStorage.token).catch((error) => {
			toast.error(`${error}`);
		});

		currentChatPage.set(1);
		await chats.set(await getChatList(localStorage.token, $currentChatPage));
		pinnedChats.set([]);
		scrollPaginationEnabled.set(true);
	};

	const deleteAllChatsHandler = async () => {
		await goto('/');
		await deleteAllChats(localStorage.token).catch((error) => {
			toast.error(`${error}`);
		});

		currentChatPage.set(1);
		await chats.set(await getChatList(localStorage.token, $currentChatPage));
		scrollPaginationEnabled.set(true);
	};

	const handleArchivedChatsChange = async () => {
		currentChatPage.set(1);
		await chats.set(await getChatList(localStorage.token, $currentChatPage));
		scrollPaginationEnabled.set(true);
	};

	const exportAllUserChats = async () => {
		let blob = new Blob([JSON.stringify(await getAllUserChats(localStorage.token))], {
			type: 'application/json'
		});
		saveAs(blob, `all-chats-export-${Date.now()}.json`);
	};

	const exportUsers = async () => {
		const users = await getAllUsers(localStorage.token);

		const headers = ['id', 'name', 'email', 'role'];

		const csv = [
			headers.join(','),
			...users.users.map((user: any) => {
				return headers
					.map((header) => {
						if (user[header] === null || user[header] === undefined) {
							return '';
						}
						return `"${String(user[header]).replace(/"/g, '""')}"`;
					})
					.join(',');
			})
		].join('\n');

		const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
		saveAs(blob, 'users.csv');
	};

	onMount(async () => {
		// permissions = await getUserPermissions(localStorage.token);
	});
</script>

<ArchivedChatsModal bind:show={showArchivedChatsModal} onUpdate={handleArchivedChatsChange} />

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		saveHandler();
	}}
>
	<div class="space-y-3 overflow-y-auto scrollbar-hidden h-full">
		<div class="max-w-5xl mx-auto">
			<!-- User Data Controls Section (visible to all users) -->
			<div class="mb-4">
				<div class="bg-gray-50 dark:bg-gray-850 rounded-lg p-5 border border-gray-100 dark:border-gray-800">
					<!-- Section Header -->
					<button
						type="button"
						class="w-full flex items-center justify-between"
						on:click={() => expandedSections.myChats = !expandedSections.myChats}
					>
						<div class="flex items-center gap-2.5">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5 text-gray-500 dark:text-gray-400">
								<path fill-rule="evenodd" d="M4.804 21.644A6.707 6.707 0 006 21.75a6.721 6.721 0 003.583-1.029c.774.182 1.584.279 2.417.279 5.322 0 9.75-3.97 9.75-9 0-5.03-4.428-9-9.75-9s-9.75 3.97-9.75 9c0 2.409 1.025 4.587 2.674 6.192.232.226.277.428.254.543a3.73 3.73 0 01-.814 1.686.75.75 0 00.44 1.223zM8.25 10.875a1.125 1.125 0 100 2.25 1.125 1.125 0 000-2.25zM10.875 12a1.125 1.125 0 112.25 0 1.125 1.125 0 01-2.25 0zm4.875-1.125a1.125 1.125 0 100 2.25 1.125 1.125 0 000-2.25z" clip-rule="evenodd" />
							</svg>
							<div class="text-sm font-medium text-gray-800 dark:text-gray-100">
								{$i18n.t('My Chats')}
							</div>
						</div>
						<div class="text-gray-500">
							{#if expandedSections.myChats}
								<ChevronUp className="w-5 h-5" />
							{:else}
								<ChevronDown className="w-5 h-5" />
							{/if}
						</div>
					</button>

					{#if expandedSections.myChats}
						<hr class="border-gray-100 dark:border-gray-800 my-4" />

						<div class="flex flex-col">
							<input
								id="chat-import-input"
								bind:this={chatImportInputElement}
								bind:files={importFiles}
								type="file"
								accept=".json"
								hidden
							/>
						<button
							type="button"
							class="flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
							on:click={() => {
								chatImportInputElement.click();
							}}
						>
							<div class="self-center mr-3">
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 16 16"
									fill="currentColor"
									class="w-4 h-4"
								>
									<path
										fill-rule="evenodd"
										d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 9.5a.75.75 0 0 1-.75-.75V8.06l-.72.72a.75.75 0 0 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0l2 2a.75.75 0 1 1-1.06 1.06l-.72-.72v2.69a.75.75 0 0 1-.75.75Z"
										clip-rule="evenodd"
									/>
								</svg>
							</div>
							<div class="self-center text-sm font-medium">{$i18n.t('Import Chats')}</div>
						</button>

						{#if $user?.role === 'admin' || ($user?.permissions?.chat?.export ?? true)}
							<button
								type="button"
								class="flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
								on:click={() => {
									exportChats();
								}}
							>
								<div class="self-center mr-3">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 16 16"
										fill="currentColor"
										class="w-4 h-4"
									>
										<path
											fill-rule="evenodd"
											d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 3.5a.75.75 0 0 1 .75.75v2.69l.72-.72a.75.75 0 1 1 1.06 1.06l-2 2a.75.75 0 0 1-1.06 0l-2-2a.75.75 0 0 1 1.06-1.06l.72.72V6.25A.75.75 0 0 1 8 5.5Z"
											clip-rule="evenodd"
										/>
									</svg>
								</div>
								<div class="self-center text-sm font-medium">{$i18n.t('Export Chats')}</div>
							</button>
						{/if}
					</div>

					<hr class="border-gray-100 dark:border-gray-800 my-3" />

					<div class="flex flex-col">
						<button
							type="button"
							class="flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
							on:click={() => {
								showArchivedChatsModal = true;
							}}
						>
							<div class="self-center mr-3">
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 24 24"
									fill="currentColor"
									class="size-4"
								>
									<path
										d="M3.375 3C2.339 3 1.5 3.84 1.5 4.875v.75c0 1.036.84 1.875 1.875 1.875h17.25c1.035 0 1.875-.84 1.875-1.875v-.75C22.5 3.839 21.66 3 20.625 3H3.375Z"
									/>
									<path
										fill-rule="evenodd"
										d="m3.087 9 .54 9.176A3 3 0 0 0 6.62 21h10.757a3 3 0 0 0 2.995-2.824L20.913 9H3.087ZM12 10.5a.75.75 0 0 1 .75.75v4.94l1.72-1.72a.75.75 0 1 1 1.06 1.06l-3 3a.75.75 0 0 1-1.06 0l-3-3a.75.75 0 1 1 1.06-1.06l1.72 1.72v-4.94a.75.75 0 0 1 .75-.75Z"
										clip-rule="evenodd"
									/>
								</svg>
							</div>
							<div class="self-center text-sm font-medium">{$i18n.t('Archived Chats')}</div>
						</button>

						{#if showArchiveConfirm}
							<div class="flex justify-between rounded-md items-center py-2 px-3.5 w-full transition">
								<div class="flex items-center space-x-3">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 16 16"
										fill="currentColor"
										class="w-4 h-4"
									>
										<path d="M2 3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3Z" />
										<path
											fill-rule="evenodd"
											d="M13 6H3v6a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V6ZM5.72 7.47a.75.75 0 0 1 1.06 0L8 8.69l1.22-1.22a.75.75 0 1 1 1.06 1.06L9.06 9.75l1.22 1.22a.75.75 0 1 1-1.06 1.06L8 10.81l-1.22 1.22a.75.75 0 0 1-1.06-1.06l1.22-1.22-1.22-1.22a.75.75 0 0 1 0-1.06Z"
											clip-rule="evenodd"
										/>
									</svg>
									<span>{$i18n.t('Are you sure?')}</span>
								</div>

								<div class="flex space-x-1.5 items-center">
									<button
										type="button"
										class="hover:text-white transition"
										on:click={() => {
											archiveAllChatsHandler();
											showArchiveConfirm = false;
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											class="w-4 h-4"
										>
											<path
												fill-rule="evenodd"
												d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
												clip-rule="evenodd"
											/>
										</svg>
									</button>
									<button
										type="button"
										class="hover:text-white transition"
										on:click={() => {
											showArchiveConfirm = false;
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											class="w-4 h-4"
										>
											<path
												d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
											/>
										</svg>
									</button>
								</div>
							</div>
						{:else}
							<button
								type="button"
								class="flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
								on:click={() => {
									showArchiveConfirm = true;
								}}
							>
								<div class="self-center mr-3">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 24 24"
										fill="currentColor"
										class="size-4"
									>
										<path
											d="M3.375 3C2.339 3 1.5 3.84 1.5 4.875v.75c0 1.036.84 1.875 1.875 1.875h17.25c1.035 0 1.875-.84 1.875-1.875v-.75C22.5 3.839 21.66 3 20.625 3H3.375Z"
										/>
										<path
											fill-rule="evenodd"
											d="m3.087 9 .54 9.176A3 3 0 0 0 6.62 21h10.757a3 3 0 0 0 2.995-2.824L20.913 9H3.087Zm6.163 3.75A.75.75 0 0 1 10 12h4a.75.75 0 0 1 0 1.5h-4a.75.75 0 0 1-.75-.75Z"
											clip-rule="evenodd"
										/>
									</svg>
								</div>
								<div class="self-center text-sm font-medium">{$i18n.t('Archive All Chats')}</div>
							</button>
						{/if}

						{#if showDeleteConfirm}
							<div class="flex justify-between rounded-md items-center py-2 px-3.5 w-full transition">
								<div class="flex items-center space-x-3">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 16 16"
										fill="currentColor"
										class="w-4 h-4"
									>
										<path d="M2 3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3Z" />
										<path
											fill-rule="evenodd"
											d="M13 6H3v6a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V6ZM5.72 7.47a.75.75 0 0 1 1.06 0L8 8.69l1.22-1.22a.75.75 0 1 1 1.06 1.06L9.06 9.75l1.22 1.22a.75.75 0 1 1-1.06 1.06L8 10.81l-1.22 1.22a.75.75 0 0 1-1.06-1.06l1.22-1.22-1.22-1.22a.75.75 0 0 1 0-1.06Z"
											clip-rule="evenodd"
										/>
									</svg>
									<span>{$i18n.t('Are you sure?')}</span>
								</div>

								<div class="flex space-x-1.5 items-center">
									<button
										type="button"
										class="hover:text-white transition"
										on:click={() => {
											deleteAllChatsHandler();
											showDeleteConfirm = false;
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											class="w-4 h-4"
										>
											<path
												fill-rule="evenodd"
												d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
												clip-rule="evenodd"
											/>
										</svg>
									</button>
									<button
										type="button"
										class="hover:text-white transition"
										on:click={() => {
											showDeleteConfirm = false;
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											class="w-4 h-4"
										>
											<path
												d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
											/>
										</svg>
									</button>
								</div>
							</div>
						{:else}
							<button
								type="button"
								class="flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
								on:click={() => {
									showDeleteConfirm = true;
								}}
							>
								<div class="self-center mr-3">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 16 16"
										fill="currentColor"
										class="w-4 h-4"
									>
										<path
											fill-rule="evenodd"
											d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm7 7a.75.75 0 0 1-.75.75h-4.5a.75.75 0 0 1 0-1.5h4.5A.75.75 0 0 1 11 9Z"
											clip-rule="evenodd"
										/>
									</svg>
								</div>
								<div class="self-center text-sm font-medium">{$i18n.t('Delete All Chats')}</div>
							</button>
						{/if}
						</div>
					{/if}
				</div>
			</div>

			<!-- Admin-only Database Section -->
			{#if $user?.role === 'admin'}
			<div class="mb-4">
				<div class="bg-gray-50 dark:bg-gray-850 rounded-lg p-5 border border-gray-100 dark:border-gray-800">
					<!-- Section Header -->
					<button
						type="button"
						class="w-full flex items-center justify-between"
						on:click={() => expandedSections.database = !expandedSections.database}
					>
						<div class="flex items-center gap-2.5">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5 text-gray-500 dark:text-gray-400">
								<path d="M12 2.25c-5.385 0-9.75 1.679-9.75 3.75v12c0 2.071 4.365 3.75 9.75 3.75s9.75-1.679 9.75-3.75V6c0-2.071-4.365-3.75-9.75-3.75zM12 6c4.142 0 7.5 1.007 7.5 2.25S16.142 10.5 12 10.5 4.5 9.493 4.5 8.25 7.858 6 12 6zm7.5 12c0 1.243-3.358 2.25-7.5 2.25S4.5 19.243 4.5 18v-2.625c1.65.975 4.5 1.625 7.5 1.625s5.85-.65 7.5-1.625V18zm0-4.5c0 1.243-3.358 2.25-7.5 2.25S4.5 14.743 4.5 13.5v-2.625c1.65.975 4.5 1.625 7.5 1.625s5.85-.65 7.5-1.625V13.5z" />
							</svg>
							<div class="text-sm font-medium text-gray-800 dark:text-gray-100">
								{$i18n.t('Database')}
							</div>
						</div>
						<div class="text-gray-500">
							{#if expandedSections.database}
								<ChevronUp className="w-5 h-5" />
							{:else}
								<ChevronDown className="w-5 h-5" />
							{/if}
						</div>
					</button>

					{#if expandedSections.database}
						<hr class="border-gray-100 dark:border-gray-800 my-4" />

						<input
						id="config-json-input"
						hidden
						type="file"
						accept=".json"
						on:change={(e) => {
							const target = e.target as HTMLInputElement;
							const file = target.files?.[0];
							if (!file) return;

							const reader = new FileReader();

							reader.onload = async (e) => {
								const result = e.target?.result as string;
								if (!result) return;

								const res = await importConfig(localStorage.token, JSON.parse(result)).catch(
									(error) => {
										toast.error(`${error}`);
									}
								);

								if (res) {
									toast.success($i18n.t('Config imported successfully'));
								}
								target.value = '';
							};

							reader.readAsText(file);
						}}
					/>

					<div class="space-y-2">
						<div class="text-xs font-medium text-gray-500">{$i18n.t('Config')}</div>
						<button
							type="button"
							class="flex rounded-md py-2 px-3 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
							on:click={async () => {
								const input = document.getElementById('config-json-input');
								if (input) input.click();
							}}
						>
							<div class=" self-center mr-3">
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 16 16"
									fill="currentColor"
									class="w-4 h-4"
								>
									<path d="M2 3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3Z" />
									<path
										fill-rule="evenodd"
										d="M13 6H3v6a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V6ZM8.75 7.75a.75.75 0 0 0-1.5 0v2.69L6.03 9.22a.75.75 0 0 0-1.06 1.06l2.5 2.5a.75.75 0 0 0 1.06 0l2.5-2.5a.75.75 0 1 0-1.06-1.06l-1.22 1.22V7.75Z"
										clip-rule="evenodd"
									/>
								</svg>
							</div>
							<div class=" self-center text-sm font-medium">
								{$i18n.t('Import Config from JSON File')}
							</div>
						</button>

						<button
							type="button"
							class="flex rounded-md py-2 px-3 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
							on:click={async () => {
								const config = await exportConfig(localStorage.token);
								const blob = new Blob([JSON.stringify(config)], {
									type: 'application/json'
								});
								saveAs(blob, `config-${Date.now()}.json`);
							}}
						>
							<div class=" self-center mr-3">
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 16 16"
									fill="currentColor"
									class="w-4 h-4"
								>
									<path d="M2 3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3Z" />
									<path
										fill-rule="evenodd"
										d="M13 6H3v6a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V6ZM8.75 7.75a.75.75 0 0 0-1.5 0v2.69L6.03 9.22a.75.75 0 0 0-1.06 1.06l2.5 2.5a.75.75 0 0 0 1.06 0l2.5-2.5a.75.75 0 1 0-1.06-1.06l-1.22 1.22V7.75Z"
										clip-rule="evenodd"
									/>
								</svg>
							</div>
							<div class=" self-center text-sm font-medium">
								{$i18n.t('Export Config to JSON File')}
							</div>
						</button>
					</div>

					<hr class="border-gray-100 dark:border-gray-800 my-3" />

					{#if $config?.features.enable_admin_export ?? true}
						<div class="space-y-2">
							<div class="text-xs font-medium text-gray-500">{$i18n.t('Exports')}</div>
							<div class="flex w-full justify-between">
								<!-- <div class=" self-center text-xs font-medium">{$i18n.t('Allow Chat Deletion')}</div> -->

								<button
									class="flex rounded-md py-1.5 px-3 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
									type="button"
									on:click={() => {
										// exportAllUserChats();

										downloadDatabase(localStorage.token).catch((error) => {
											toast.error(`${error}`);
										});
									}}
								>
									<div class=" self-center mr-3">
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 16 16"
											fill="currentColor"
											class="w-4 h-4"
										>
											<path
												d="M2 3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3Z"
											/>
											<path
												fill-rule="evenodd"
												d="M13 6H3v6a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V6ZM8.75 7.75a.75.75 0 0 0-1.5 0v2.69L6.03 9.22a.75.75 0 0 0-1.06 1.06l2.5 2.5a.75.75 0 0 0 1.06 0l2.5-2.5a.75.75 0 1 0-1.06-1.06l-1.22 1.22V7.75Z"
												clip-rule="evenodd"
											/>
										</svg>
									</div>
									<div class=" self-center text-sm font-medium">{$i18n.t('Download Database')}</div>
								</button>
							</div>

							<button
								class="flex rounded-md py-2 px-3 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
								on:click={() => {
									exportAllUserChats();
								}}
							>
								<div class=" self-center mr-3">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 16 16"
										fill="currentColor"
										class="w-4 h-4"
									>
										<path d="M2 3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3Z" />
										<path
											fill-rule="evenodd"
											d="M13 6H3v6a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V6ZM8.75 7.75a.75.75 0 0 0-1.5 0v2.69L6.03 9.22a.75.75 0 0 0-1.06 1.06l2.5 2.5a.75.75 0 0 0 1.06 0l2.5-2.5a.75.75 0 1 0-1.06-1.06l-1.22 1.22V7.75Z"
											clip-rule="evenodd"
										/>
									</svg>
								</div>
								<div class=" self-center text-sm font-medium">
									{$i18n.t('Export All Chats (All Users)')}
								</div>
							</button>

							<button
								class="flex rounded-md py-2 px-3 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
								on:click={() => {
									exportUsers();
								}}
							>
								<div class=" self-center mr-3">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 16 16"
										fill="currentColor"
										class="w-4 h-4"
									>
										<path d="M2 3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3Z" />
										<path
											fill-rule="evenodd"
											d="M13 6H3v6a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V6ZM8.75 7.75a.75.75 0 0 0-1.5 0v2.69L6.03 9.22a.75.75 0 0 0-1.06 1.06l2.5 2.5a.75.75 0 0 0 1.06 0l2.5-2.5a.75.75 0 1 0-1.06-1.06l-1.22 1.22V7.75Z"
											clip-rule="evenodd"
										/>
									</svg>
								</div>
								<div class=" self-center text-sm font-medium">
									{$i18n.t('Export Users')}
								</div>
							</button>
						</div>
						{/if}
					{/if}
				</div>
			</div>
			{/if}
		</div>
	</div>
</form>
