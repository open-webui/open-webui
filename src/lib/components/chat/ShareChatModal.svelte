<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { models, config } from '$lib/stores';

	import { toast } from 'svelte-sonner';
	import {
		deleteSharedChatById,
		getChatById,
		shareChatById,
		getChatAccessGrants,
		updateChatAccessGrants
	} from '$lib/apis/chats';
	import { copyToClipboard } from '$lib/utils';

	import Modal from '../common/Modal.svelte';
	import Link from '../icons/Link.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import AccessControl from '$lib/components/workspace/common/AccessControl.svelte';

	export let chatId;

	let chat = null;
	let shareUrl = null;
	let accessGrants: any[] = [];
	const i18n = getContext('i18n');

	const shareLocalChat = async () => {
		const _chat = chat;

		const sharedChat = await shareChatById(localStorage.token, chatId);
		shareUrl = `${window.location.origin}/s/${sharedChat.share_id}`;
		console.log(shareUrl);
		chat = await getChatById(localStorage.token, chatId);

		return shareUrl;
	};

	const shareChat = async () => {
		const _chat = chat.chat;
		console.log('share', _chat);

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
							models: $models.filter((m) => _chat.models.includes(m.id))
						}),
						'*'
					);
				}
			},
			false
		);
	};

	const loadAccessGrants = async () => {
		if (!chatId) return;
		try {
			accessGrants = (await getChatAccessGrants(localStorage.token, chatId)) ?? [];
		} catch (e) {
			console.error('Failed to load access grants', e);
			accessGrants = [];
		}
	};

	const saveAccessGrants = async () => {
		try {
			await updateChatAccessGrants(localStorage.token, chatId, accessGrants);
			toast.success($i18n.t('Access updated'));
		} catch (e) {
			toast.error(`${e}`);
		}
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
				await loadAccessGrants();
			} else {
				chat = null;
				accessGrants = [];
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
				aria-label={$i18n.t('Close')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		{#if chat}
			<div class="px-5 pt-4 pb-5 w-full flex flex-col">
				<div class="text-sm dark:text-gray-300">
					{#if chat.share_id}
						<a href="/s/{chat.share_id}" target="_blank"
							>{$i18n.t('You have shared this chat')}
							<span class=" underline">{$i18n.t('before')}</span>.</a
						>
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
					{/if}
				</div>

				{#if chat.share_id}
					<div class="mt-3">
						<AccessControl bind:accessGrants accessRoles={['read']} onChange={saveAccessGrants} />
					</div>
				{/if}

				<div class="flex justify-end gap-1 mt-3">
					{#if $config?.features.enable_community_sharing}
						<button
							class="flex items-center gap-1 px-3.5 py-2 text-sm font-medium bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:text-white dark:hover:bg-gray-800 transition rounded-full"
							type="button"
							on:click={() => {
								shareChat();
							}}
						>
							{$i18n.t('Share to Open WebUI Community')}
						</button>
					{/if}

					<button
						class="flex items-center gap-1 px-3.5 py-2 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
						type="button"
						id="copy-and-share-chat-button"
						on:click={async () => {
							const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);

							if (isSafari) {
								console.log('isSafari');

								const getUrlPromise = async () => {
									const url = await shareLocalChat();
									return new Blob([url], { type: 'text/plain' });
								};

								navigator.clipboard
									.write([
										new ClipboardItem({
											'text/plain': getUrlPromise()
										})
									])
									.then(() => {
										console.log('Async: Copying to clipboard was successful!');
										return true;
									})
									.catch((error) => {
										console.error('Async: Could not copy text: ', error);
										return false;
									});
							} else {
								copyToClipboard(await shareLocalChat());
							}

							toast.success($i18n.t('Copied shared chat URL to clipboard!'));
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
		{/if}
	</div>
</Modal>
