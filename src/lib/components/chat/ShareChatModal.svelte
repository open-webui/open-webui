<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { models, config } from '$lib/stores';

	import { toast } from 'svelte-sonner';
	import { deleteSharedChatById, getChatById, shareChatById } from '$lib/apis/chats';
	import { copyToClipboard } from '$lib/utils';

	import Modal from '../common/Modal.svelte';
	import Link from '../icons/Link.svelte';

	export let chatId;

	let chat = null;
	let shareUrl = null;
	const i18n = getContext('i18n');

	const shareLocalChat = async () => {
		const _chat = chat;

		const sharedChat = await shareChatById(localStorage.token, chatId);
		shareUrl = `${window.location.origin}/s/${sharedChat.id}`;
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
		<div class=" flex justify-between px-[16px] py-[16px]">
			<div class="text-neutrals-800 text-[18px] leading-[26px] font-medium self-center">{$i18n.t('Share Chat')}</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 18 18" fill="none">
  <path d="M14.4608 13.6648C14.513 13.7171 14.5545 13.7792 14.5828 13.8474C14.6111 13.9157 14.6256 13.9889 14.6256 14.0628C14.6256 14.1367 14.6111 14.2099 14.5828 14.2782C14.5545 14.3465 14.513 14.4085 14.4608 14.4608C14.4085 14.513 14.3465 14.5545 14.2782 14.5828C14.2099 14.6111 14.1367 14.6256 14.0628 14.6256C13.9889 14.6256 13.9157 14.6111 13.8474 14.5828C13.7792 14.5545 13.7171 14.513 13.6648 14.4608L9.00031 9.79555L4.33578 14.4608C4.23023 14.5663 4.08708 14.6256 3.93781 14.6256C3.78855 14.6256 3.64539 14.5663 3.53984 14.4608C3.4343 14.3552 3.375 14.2121 3.375 14.0628C3.375 13.9135 3.4343 13.7704 3.53984 13.6648L8.20508 9.00031L3.53984 4.33578C3.4343 4.23023 3.375 4.08708 3.375 3.93781C3.375 3.78855 3.4343 3.64539 3.53984 3.53984C3.64539 3.4343 3.78855 3.375 3.93781 3.375C4.08708 3.375 4.23023 3.4343 4.33578 3.53984L9.00031 8.20508L13.6648 3.53984C13.7704 3.4343 13.9135 3.375 14.0628 3.375C14.2121 3.375 14.3552 3.4343 14.4608 3.53984C14.5663 3.64539 14.6256 3.78855 14.6256 3.93781C14.6256 4.08708 14.5663 4.23023 14.4608 4.33578L9.79555 9.00031L14.4608 13.6648Z" fill="#36383B"/>
</svg>
			</button>
		</div>

		{#if chat}
			<div class="px-[16px] py-[16px] w-full flex flex-col justify-center">
				<div class="text-neutrals-700 text-[16px] leading-[24px] dark:text-gray-300">
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
								class="self-center flex items-center gap-1 px-3.5 py-2 text-sm font-medium bg-primary-400 hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
								type="button"
								id="copy-and-share-chat-button"
								on:click={async () => {
									const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);

									if (isSafari) {
										// Oh, Safari, you're so special, let's give you some extra love and attention
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
									show = false;
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
