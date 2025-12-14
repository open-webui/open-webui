<script lang="ts">
	import { onMount, tick, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import dayjs from 'dayjs';

	import { settings, chatId, WEBUI_NAME, models, config, user as sessionUser } from '$lib/stores';
	import { convertMessagesToHistory, createMessagesList } from '$lib/utils';

	import { cloneSharedChatById, createNewChat, getChatByShareId } from '$lib/apis/chats';

	import Messages from '$lib/components/chat/Messages.svelte';

	import { getUserById, getUserSettings } from '$lib/apis/users';
	import { getModels } from '$lib/apis';
	import { toast } from 'svelte-sonner';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import {
		decryptSharePayload,
		encryptChatContent,
		getOrCreateUMK,
		importShareKey
	} from '$lib/utils/crypto/envelope';
	import { v4 as uuidv4 } from 'uuid';
	import { type Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n: Writable<i18nType> = getContext('i18n');
	dayjs.extend(localizedFormat);

	let loaded = false;

	let autoScroll = true;
	let processing = '';
	let messagesContainerElement: HTMLDivElement;

	// let chatId = $page.params.id;
	let showModelSelector = false;
	let selectedModels = [''];

	let chat = null;
	let owner = null;

	let title = '';
	let timestamp: number | null = null;
	let files = [];

	let messages = [];
	let history = {
		messages: {},
		currentId: null
	};

	let encryptedShare = false;
	let missingShareKey = false;
	let shareDecryptError: string | null = null;
	let decryptedShareChat = null;
	let shareMeta = null;

	$: messages = createMessagesList(history, history.currentId);

	$: if ($page.params.id) {
		(async () => {
			if (await loadSharedChat()) {
				await tick();
				loaded = true;
			} else {
				await goto('/');
			}
		})();
	}

	//////////////////////////
	// Web functions
	//////////////////////////

	const getShareKeyFromHash = () => {
		const hash = window.location.hash.startsWith('#')
			? window.location.hash.slice(1)
			: window.location.hash;
		const params = new URLSearchParams(hash);
		const key = params.get('k');
		return key && key.trim() ? key.trim() : null;
	};

	const splitChatForEncryption = (plainChat: any, newChatId: string) => {
		const meta = {
			id: newChatId,
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

	const loadSharedChat = async () => {
		const userSettings = await getUserSettings(localStorage.token).catch((error) => {
			console.error(error);
			return null;
		});

		if (userSettings) {
			settings.set(userSettings.ui);
		} else {
			let localStorageSettings = {} as Parameters<(typeof settings)['set']>[0];

			try {
				localStorageSettings = JSON.parse(localStorage.getItem('settings') ?? '{}');
			} catch (e: unknown) {
				console.error('Failed to parse settings from localStorage', e);
			}

			settings.set(localStorageSettings);
		}

		await models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
		await chatId.set($page.params.id);
		chat = await getChatByShareId(localStorage.token, $chatId).catch(async (error) => {
			await goto('/');
			return null;
		});

		if (chat) {
			owner = await getUserById(localStorage.token, chat.user_id).catch((error) => {
				console.error(error);
				return null;
			});

			const chatContent = chat.chat;

			if (chatContent) {
				encryptedShare = false;
				missingShareKey = false;
				shareDecryptError = null;
				decryptedShareChat = null;
				shareMeta = null;

				if (typeof chatContent === 'object' && chatContent?.share) {
					encryptedShare = true;
					shareMeta = chatContent?.meta ?? null;

					const keyB64Url = getShareKeyFromHash();
					if (!keyB64Url) {
						missingShareKey = true;
						title = shareMeta?.title ?? chat.title ?? '';
						timestamp = shareMeta?.timestamp ?? null;
						selectedModels = shareMeta?.models ?? [''];
						history = { messages: {}, currentId: null };
						return true;
					}

					try {
						const shareKey = await importShareKey(keyB64Url);
						const decrypted = await decryptSharePayload(shareKey, chatContent.share, $chatId);
						decryptedShareChat = decrypted;

						selectedModels =
							(decrypted?.models ?? undefined) !== undefined
								? decrypted.models
								: [decrypted?.models ?? ''];
						history =
							(decrypted?.history ?? undefined) !== undefined
								? decrypted.history
								: convertMessagesToHistory(decrypted.messages);
						title = decrypted?.title ?? shareMeta?.title ?? '';
						timestamp = decrypted?.timestamp ?? shareMeta?.timestamp ?? null;
					} catch (error) {
						console.error(error);
						shareDecryptError = $i18n.t(
							'Unable to decrypt this shared chat. Check that your link is complete.'
						);
						title = shareMeta?.title ?? chat.title ?? '';
						timestamp = shareMeta?.timestamp ?? null;
						selectedModels = shareMeta?.models ?? [''];
						history = { messages: {}, currentId: null };
						return true;
					}
				} else {
					selectedModels =
						(chatContent?.models ?? undefined) !== undefined
							? chatContent.models
							: [chatContent.models ?? ''];
					history =
						(chatContent?.history ?? undefined) !== undefined
							? chatContent.history
							: convertMessagesToHistory(chatContent.messages);
					title = chatContent.title;
					timestamp = chatContent?.timestamp ?? null;
				}

				autoScroll = true;
				await tick();

				if (messages.length > 0 && messages.at(-1)?.id && messages.at(-1)?.id in history.messages) {
					history.messages[messages.at(-1)?.id].done = true;
				}
				await tick();

				return true;
			} else {
				return null;
			}
		}
	};

	const cloneSharedChat = async () => {
		if (!chat) return;

		if (encryptedShare) {
			if (missingShareKey || shareDecryptError || !decryptedShareChat) {
				toast.error($i18n.t('Missing decryption key for this shared chat'));
				return;
			}

			const policy = $config?.features?.chat_encryption ?? null;
			const encryptionEnabled =
				(policy?.required ?? false) || ($settings?.chatEncryptionEnabled ?? false);

			const newChatId = uuidv4();
			const plainChat = {
				...(decryptedShareChat ?? {}),
				id: newChatId,
				originalChatId: chat.id,
				branchPointMessageId: decryptedShareChat?.history?.currentId ?? null,
				title: $i18n.t('Clone of {{title}}', {
					title: decryptedShareChat?.title ?? chat.title ?? ''
				}),
				timestamp: Date.now()
			};

			try {
				const created = encryptionEnabled
					? await (async () => {
							if (!$sessionUser?.id) throw new Error('Missing session user');
							const { key } = await getOrCreateUMK();
							const { meta, content } = splitChatForEncryption(plainChat, newChatId);
							const encrypted = await encryptChatContent(key, newChatId, $sessionUser.id, content);
							return createNewChat(localStorage.token, { enc: encrypted.enc, meta }, null);
						})()
					: await createNewChat(localStorage.token, plainChat, null);

				if (created) {
					goto(`/c/${created.id}`);
				}
			} catch (error) {
				console.error(error);
				toast.error($i18n.t('Failed to clone shared chat'));
			}

			return;
		}

		const res = await cloneSharedChatById(localStorage.token, chat.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			goto(`/c/${res.id}`);
		}
	};
</script>

<svelte:head>
	<title>
		{title
			? `${title.length > 30 ? `${title.slice(0, 30)}...` : title} • ${$WEBUI_NAME}`
			: `${$WEBUI_NAME}`}
	</title>
</svelte:head>

{#if loaded}
	<div
		class="h-screen max-h-[100dvh] w-full flex flex-col text-gray-700 dark:text-gray-100 bg-white dark:bg-gray-900"
	>
		<div class="flex flex-col flex-auto justify-center relative">
			<div class=" flex flex-col w-full flex-auto overflow-auto h-0" id="messages-container">
				<div
					class="pt-5 px-2 w-full {($settings?.widescreenMode ?? null)
						? 'max-w-full'
						: 'max-w-5xl'} mx-auto"
				>
					<div class="px-3">
						<div class=" text-2xl font-medium line-clamp-1">
							{title}
						</div>

						<div class="flex text-sm justify-between items-center mt-1">
							<div class="text-gray-400">
								{timestamp ? dayjs(timestamp).format('LLL') : ''}
							</div>
						</div>
					</div>
				</div>

				<div class=" h-full w-full flex flex-col py-2">
					<div class="w-full">
						{#if missingShareKey}
							<div class="px-6 py-10 text-center text-gray-500 dark:text-gray-400">
								<div class="text-lg font-medium mb-2">{$i18n.t('Missing decryption key')}</div>
								<div class="text-sm">
									{$i18n.t(
										'This shared chat requires a decryption key in the URL fragment (#k=…). Ask the sender for the full link.'
									)}
								</div>
							</div>
						{:else if shareDecryptError}
							<div class="px-6 py-10 text-center text-gray-500 dark:text-gray-400">
								<div class="text-lg font-medium mb-2">{$i18n.t('Unable to decrypt')}</div>
								<div class="text-sm">{shareDecryptError}</div>
							</div>
						{:else}
							<Messages
								className="h-full flex pt-4 pb-8 "
								user={owner}
								chatId={$chatId}
								readOnly={true}
								{selectedModels}
								{processing}
								bind:history
								bind:messages
								bind:autoScroll
								bottomPadding={files.length > 0}
								sendMessage={() => {}}
								continueResponse={() => {}}
								regenerateResponse={() => {}}
							/>
						{/if}
					</div>
				</div>
			</div>

			<div
				class="absolute bottom-0 right-0 left-0 flex justify-center w-full bg-linear-to-b from-transparent to-white dark:to-gray-900"
			>
				<div class="pb-5">
					<button
						class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
						on:click={cloneSharedChat}
						disabled={encryptedShare && (missingShareKey || shareDecryptError)}
					>
						{$i18n.t('Clone Chat')}
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}
