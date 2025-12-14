<script lang="ts">
	import { getContext } from 'svelte';
	import { models, config, user } from '$lib/stores';
	import { v4 as uuidv4 } from 'uuid';
	import { type Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import { toast } from 'svelte-sonner';
	import { deleteSharedChatById, getChatById, shareChatById } from '$lib/apis/chats';
	import { copyToClipboard } from '$lib/utils';
	import {
		decryptChatContent,
		encryptSharePayload,
		generateShareKey,
		getOrCreateUMK
	} from '$lib/utils/crypto/envelope';

	import Modal from '../common/Modal.svelte';
	import Link from '../icons/Link.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let chatId;

	let chat = null;
	let shareUrl = null;
	const i18n: Writable<i18nType> = getContext('i18n');

	const getPlainChatForSharing = async (_chat) => {
		if (!_chat?.chat) return null;

		const storedChat = _chat.chat;
		if (storedChat?.enc && storedChat?.meta) {
			if (!$user?.id) {
				throw new Error('Missing user context for decrypting chat');
			}

			const { key } = await getOrCreateUMK();
			const decrypted = await decryptChatContent(key, storedChat.enc, chatId, $user.id);

			const plain = { ...(storedChat.meta ?? {}), ...(decrypted ?? {}) };
			plain.title = plain.title ?? _chat.title ?? $i18n.t('New Chat');
			plain.timestamp = plain.timestamp ?? Date.now();
			return plain;
		}

		const plain = { ...(storedChat ?? {}) };
		plain.title = plain.title ?? _chat.title ?? $i18n.t('New Chat');
		plain.timestamp = plain.timestamp ?? Date.now();
		return plain;
	};

	const shareLocalChat = async () => {
		const shareId = chat?.share_id ?? uuidv4();
		const plainChat = await getPlainChatForSharing(chat);
		if (!plainChat) {
			throw new Error('Missing chat content');
		}

		const { key: shareKey, keyB64Url } = await generateShareKey();
		const { share } = await encryptSharePayload(shareKey, shareId, plainChat);

		const sharedChat = await shareChatById(localStorage.token, chatId, {
			share_id: shareId,
			share,
			meta: {
				title: plainChat.title,
				timestamp: plainChat.timestamp,
				models: plainChat.models ?? []
			}
		});

		shareUrl = `${window.location.origin}/s/${sharedChat.id}#k=${keyB64Url}`;
		chat = await getChatById(localStorage.token, chatId);
		return shareUrl;
	};

	const shareChat = async () => {
		const _chat = await getPlainChatForSharing(chat);
		if (!_chat) return;

		toast.success($i18n.t('Redirecting you to Open WebUI Community'));
		const url = 'https://openwebui.com';
		// const url = 'http://localhost:5173';

		const tab = await window.open(`${url}/chats/upload`, '_blank');
		window.addEventListener(
			'message',
			(event) => {
				if (event.origin !== url) return;
				if (event.data === 'loaded') {
					tab.postMessage(
						JSON.stringify({
							chat: _chat,
							models: $models.filter((m) => (_chat.models ?? []).includes(m.id))
						}),
						'*'
					);
				}
			},
			false
		);
	};

	export let show = false;

	const isDifferentChat = (_chat) => {
		if (!chat) {
			return true;
		}
		if (!_chat) {
			return false;
		}
		return chat.id !== _chat.id || chat.share_id !== _chat.share_id;
	};

	$: if (show) {
		(async () => {
			if (chatId) {
				const _chat = await getChatById(localStorage.token, chatId);
				if (isDifferentChat(_chat)) {
					chat = _chat;
				}
			} else {
				chat = null;
				console.log(chat);
			}
		})();
	}
</script>

<Modal bind:show size="md">
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-0.5">
			<div class=" text-lg font-medium self-center">{$i18n.t('Share Chat')}</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		{#if chat}
			<div class="px-5 pt-4 pb-5 w-full flex flex-col justify-center">
				<div class=" text-sm dark:text-gray-300 mb-1">
					{#if chat.share_id}
						{$i18n.t('You have shared this chat')}
						<span class=" underline">{$i18n.t('before')}</span>.
						{$i18n.t(
							'Creating a new link will rotate the decryption key. Anyone with the full link can read the shared chat.'
						)}
						{$i18n.t('Click here to')}
						<button
							class="underline"
							on:click={async () => {
								const res = await deleteSharedChatById(localStorage.token, chatId);

								if (res) {
									chat = await getChatById(localStorage.token, chatId);
								}
							}}
							>{$i18n.t('delete this link')}
						</button>
						{$i18n.t('and create a new shared link.')}
					{:else}
						{$i18n.t(
							"Messages you send after creating your link won't be shared. Users with the URL will be able to view the shared chat."
						)}
						<div class="mt-2 text-xs text-gray-500 dark:text-gray-400">
							{$i18n.t(
								'This link includes a decryption key in the URL fragment (#k=…). Anyone with the full link can read the chat.'
							)}
						</div>
					{/if}

					{#if chat?.chat?.enc}
						<div class="mt-2 text-xs text-gray-500 dark:text-gray-400">
							{$i18n.t('This chat will be decrypted in your browser to create the share link.')}
						</div>
					{/if}
				</div>

				<div class="flex justify-end">
					<div class="flex flex-col items-end space-x-1 mt-3">
						<div class="flex gap-1">
							{#if $config?.features.enable_community_sharing}
								<button
									class="self-center flex items-center gap-1 px-3.5 py-2 text-sm font-medium bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:text-white dark:hover:bg-gray-800 transition rounded-full"
									type="button"
									on:click={() => {
										shareChat();
										show = false;
									}}
								>
									{$i18n.t('Share to Open WebUI Community')}
								</button>
							{/if}

							<button
								class="self-center flex items-center gap-1 px-3.5 py-2 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
								type="button"
								id="copy-and-share-chat-button"
								on:click={async () => {
									try {
										const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);

										if (isSafari) {
											const getUrlPromise = async () => {
												const url = await shareLocalChat();
												return new Blob([url], { type: 'text/plain' });
											};

											await navigator.clipboard.write([
												new ClipboardItem({
													'text/plain': getUrlPromise()
												})
											]);
										} else {
											copyToClipboard(await shareLocalChat());
										}

										toast.success($i18n.t('Copied shared chat URL to clipboard!'));
										show = false;
									} catch (error) {
										console.error(error);
										toast.error($i18n.t('Failed to create share link'));
									}
								}}
							>
								<Link />

								{#if chat.share_id}
									{$i18n.t('Update and Copy Link')}
								{:else}
									{$i18n.t('Copy Link')}
								{/if}
							</button>
						</div>
					</div>
				</div>
			</div>
		{/if}
	</div>
</Modal>
