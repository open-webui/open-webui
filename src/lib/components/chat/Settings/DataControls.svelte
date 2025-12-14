<script lang="ts">
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import {
		chats,
		config,
		user,
		settings,
		scrollPaginationEnabled,
		currentChatPage,
		pinnedChats
	} from '$lib/stores';

	import {
		archiveAllChats,
		deleteAllChats,
		getAllChats,
		getChatList,
		getPinnedChatList,
		importChats,
		updateChatById
	} from '$lib/apis/chats';
	import { copyToClipboard, getImportOrigin, convertOpenAIChats } from '$lib/utils';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import ArchivedChatsModal from '$lib/components/layout/ArchivedChatsModal.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import {
		encryptChatContent,
		exportRecoveryKey,
		getOrCreateUMK,
		importRecoveryKey
	} from '$lib/utils/crypto/envelope';

	const i18n = getContext('i18n');

	export let saveSettings: Function;

	let chatEncryptionEnabled = false;
	$: encryptionPolicy = $config?.features?.chat_encryption ?? null;
	$: encryptionRequired = encryptionPolicy?.required ?? false;
	$: if (encryptionRequired) {
		chatEncryptionEnabled = true;
	}

	onMount(() => {
		chatEncryptionEnabled = encryptionRequired || ($settings?.chatEncryptionEnabled ?? false);
	});

	const enableChatEncryption = async () => {
		const { fingerprint } = await getOrCreateUMK();
		await saveSettings({ chatEncryptionEnabled: true, chatEncryptionUmkFingerprint: fingerprint });
		chatEncryptionEnabled = true;
	};

	const disableChatEncryption = async () => {
		await saveSettings({ chatEncryptionEnabled: false });
		chatEncryptionEnabled = false;
	};

	const exportRecoveryKeyHandler = async () => {
		try {
			const key = await exportRecoveryKey();
			copyToClipboard(key);
			toast.success($i18n.t('Recovery key copied to clipboard'));
		} catch (error) {
			console.error(error);
			toast.error($i18n.t('Failed to export recovery key'));
		}
	};

	const importRecoveryKeyHandler = async () => {
		const value = prompt($i18n.t('Paste your recovery key')) ?? '';
		if (!value.trim()) return;

		try {
			const { fingerprint } = await importRecoveryKey(value);
			await saveSettings({
				chatEncryptionEnabled: true,
				chatEncryptionUmkFingerprint: fingerprint
			});
			chatEncryptionEnabled = true;
			toast.success($i18n.t('Recovery key imported'));
		} catch (error) {
			console.error(error);
			toast.error($i18n.t('Failed to import recovery key'));
		}
	};

	let encryptAllInProgress = false;
	let encryptAllTotal = 0;
	let encryptAllDone = 0;
	let encryptAllErrors = 0;
	let cancelEncryptAll = false;

	const splitChatForEncryption = (plainChat: any, chatId: string) => {
		const meta = {
			id: chatId,
			title: plainChat?.title ?? 'New Chat',
			models: plainChat?.models ?? [],
			timestamp: plainChat?.timestamp ?? Date.now()
		};

		const content = { ...(plainChat ?? {}) };
		delete content.id;
		delete content.title;
		delete content.models;
		delete content.timestamp;

		return { meta, content };
	};

	const encryptAllChatsHandler = async () => {
		if (encryptAllInProgress) return;
		cancelEncryptAll = false;
		encryptAllInProgress = true;
		encryptAllTotal = 0;
		encryptAllDone = 0;
		encryptAllErrors = 0;

		try {
			const { key, fingerprint } = await getOrCreateUMK();
			if (!encryptionRequired && !($settings?.chatEncryptionEnabled ?? false)) {
				await saveSettings({
					chatEncryptionEnabled: true,
					chatEncryptionUmkFingerprint: fingerprint
				});
				chatEncryptionEnabled = true;
			}

			const allChats = await getAllChats(localStorage.token);
			const legacyChats = (allChats ?? []).filter((c) => c?.chat && !c.chat?.enc);
			encryptAllTotal = legacyChats.length;

			for (const c of legacyChats) {
				if (cancelEncryptAll) break;

				try {
					const plainChat = c.chat;
					const { meta, content } = splitChatForEncryption(
						{ ...plainChat, title: plainChat?.title ?? c.title ?? 'New Chat' },
						c.id
					);

					const encrypted = await encryptChatContent(key, c.id, $user.id, content);
					await updateChatById(localStorage.token, c.id, { enc: encrypted.enc, meta });
					encryptAllDone += 1;
				} catch (error) {
					console.error(error);
					encryptAllErrors += 1;
				}
			}

			currentChatPage.set(1);
			await chats.set(await getChatList(localStorage.token, $currentChatPage));
			pinnedChats.set(await getPinnedChatList(localStorage.token));
			scrollPaginationEnabled.set(true);

			if (cancelEncryptAll) {
				toast.info($i18n.t('Encryption canceled'));
			} else if (encryptAllErrors > 0) {
				toast.warning(
					$i18n.t('Encrypted {{done}} chats, {{errors}} failed', {
						done: encryptAllDone,
						errors: encryptAllErrors
					})
				);
			} else {
				toast.success(
					$i18n.t('Encrypted {{count}} chats', {
						count: encryptAllDone
					})
				);
			}
		} finally {
			encryptAllInProgress = false;
		}
	};

	// Chats
	let importFiles;

	let showArchiveConfirm = false;
	let showDeleteConfirm = false;
	let showArchivedChatsModal = false;

	let chatImportInputElement: HTMLInputElement;

	$: if (importFiles) {
		console.log(importFiles);

		let reader = new FileReader();
		reader.onload = (event) => {
			let chats = JSON.parse(event.target.result);
			console.log(chats);
			if (getImportOrigin(chats) == 'openai') {
				try {
					chats = convertOpenAIChats(chats);
				} catch (error) {
					console.log('Unable to import chats:', error);
				}
			}
			importChatsHandler(chats);
		};

		if (importFiles.length > 0) {
			reader.readAsText(importFiles[0]);
		}
	}

	const importChatsHandler = async (_chats) => {
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
					// Legacy format
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
</script>

<ArchivedChatsModal bind:show={showArchivedChatsModal} onUpdate={handleArchivedChatsChange} />

<div id="tab-chats" class="flex flex-col h-full justify-between space-y-3 text-sm">
	<div class=" space-y-2 overflow-y-scroll max-h-[28rem] md:max-h-full">
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
				class=" flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={() => {
					chatImportInputElement.click();
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
							fill-rule="evenodd"
							d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 9.5a.75.75 0 0 1-.75-.75V8.06l-.72.72a.75.75 0 0 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0l2 2a.75.75 0 1 1-1.06 1.06l-.72-.72v2.69a.75.75 0 0 1-.75.75Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<div class=" self-center text-sm font-medium">{$i18n.t('Import Chats')}</div>
			</button>

			{#if $user?.role === 'admin' || ($user.permissions?.chat?.export ?? true)}
				<button
					class=" flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
					on:click={() => {
						exportChats();
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
								fill-rule="evenodd"
								d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 3.5a.75.75 0 0 1 .75.75v2.69l.72-.72a.75.75 0 1 1 1.06 1.06l-2 2a.75.75 0 0 1-1.06 0l-2-2a.75.75 0 0 1 1.06-1.06l.72.72V6.25A.75.75 0 0 1 8 5.5Z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<div class=" self-center text-sm font-medium">{$i18n.t('Export Chats')}</div>
				</button>
			{/if}
		</div>

		<hr class=" border-gray-100/30 dark:border-gray-850/30" />

		<div class="flex flex-col space-y-2">
			<div id="chat-encryption-label" class="py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs">{$i18n.t('Encrypt Chats')}</div>
				<div class="flex items-center gap-2 p-1">
					<Switch
						ariaLabelledbyId="chat-encryption-label"
						tooltip={encryptionRequired ? $i18n.t('Required') : true}
						bind:state={chatEncryptionEnabled}
						on:change={async (e) => {
							if (encryptionRequired) {
								chatEncryptionEnabled = true;
								return;
							}

							if (e.detail) {
								await enableChatEncryption();
							} else {
								await disableChatEncryption();
							}
						}}
					/>
				</div>
			</div>

			{#if chatEncryptionEnabled}
				<div class="text-xs text-gray-500 dark:text-gray-400 px-3.5">
					{$i18n.t(
						'Encryption is stored in your browser. Export a recovery key to avoid data loss if you clear storage.'
					)}
				</div>

				<div class="flex gap-2 px-3.5">
					<button
						class="flex-1 flex justify-center rounded-md py-2 px-3.5 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
						on:click={exportRecoveryKeyHandler}
					>
						<div class="self-center text-sm font-medium">
							{$i18n.t('Export Recovery Key')}
						</div>
					</button>
					<button
						class="flex-1 flex justify-center rounded-md py-2 px-3.5 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
						on:click={importRecoveryKeyHandler}
					>
						<div class="self-center text-sm font-medium">
							{$i18n.t('Import Recovery Key')}
						</div>
					</button>
				</div>

				<div class="flex flex-col gap-2 px-3.5">
					<button
						class="flex justify-center rounded-md py-2 px-3.5 hover:bg-gray-200 dark:hover:bg-gray-800 transition disabled:opacity-60 disabled:cursor-not-allowed"
						on:click={encryptAllChatsHandler}
						disabled={encryptAllInProgress}
					>
						<div class="self-center text-sm font-medium">
							{encryptAllInProgress ? $i18n.t('Encrypting...') : $i18n.t('Encrypt All Chats')}
						</div>
					</button>

					{#if encryptAllInProgress}
						<div class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
							<div>
								{$i18n.t('Progress')}: {encryptAllDone}/{encryptAllTotal}
								{#if encryptAllErrors > 0}
									({$i18n.t('failed')}: {encryptAllErrors})
								{/if}
							</div>
							<button
								class="underline"
								on:click={() => {
									cancelEncryptAll = true;
								}}
							>
								{$i18n.t('Cancel')}
							</button>
						</div>
					{/if}
				</div>
			{/if}
		</div>

		<hr class=" border-gray-100/30 dark:border-gray-850/30" />

		<div class="flex flex-col">
			<button
				class=" flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={() => {
					showArchivedChatsModal = true;
				}}
			>
				<div class=" self-center mr-3">
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
				<div class=" self-center text-sm font-medium">{$i18n.t('Archived Chats')}</div>
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
					class=" flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
					on:click={() => {
						showArchiveConfirm = true;
					}}
				>
					<div class=" self-center mr-3">
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
					<div class=" self-center text-sm font-medium">{$i18n.t('Archive All Chats')}</div>
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
					class=" flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
					on:click={() => {
						showDeleteConfirm = true;
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
								fill-rule="evenodd"
								d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm7 7a.75.75 0 0 1-.75.75h-4.5a.75.75 0 0 1 0-1.5h4.5A.75.75 0 0 1 11 9Z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<div class=" self-center text-sm font-medium">{$i18n.t('Delete All Chats')}</div>
				</button>
			{/if}
		</div>
	</div>
</div>
