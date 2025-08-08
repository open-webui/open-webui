<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { models, config, sharedChats, sharedChatsUpdated } from '$lib/stores';

	import { toast } from 'svelte-sonner';
	import { deleteSharedChatById, getChatById, shareChatById } from '$lib/apis/chats';
	import { copyToClipboard } from '$lib/utils';
	import { v4 as uuidv4 } from 'uuid';

	import Modal from '../common/Modal.svelte';
	import Link from '../icons/Link.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import ArrowPath from '$lib/components/icons/ArrowPath.svelte';
	import ArrowDownTray from '$lib/components/icons/ArrowDownTray.svelte';
	import ArrowUpTray from '$lib/components/icons/ArrowUpTray.svelte';

	export let chatId;
	export let closeOnDelete = false;

	let chat = null;
	let shareUrl = null;
	let qrCodeUrl = '';
	let share_id = '';
	const i18n = getContext('i18n');

	const shareLocalChat = async () => {
		try {
			if (chat.share_id) {
				await deleteSharedChatById(localStorage.token, chatId);
			}

			const sharedChat = await shareChatById(localStorage.token, chatId, share_id);
			shareUrl = `${window.location.origin}/s/${sharedChat.id}`;
			qrCodeUrl = await QRCode.toDataURL(shareUrl);
			console.log(shareUrl);
			
			const updatedChat = await getChatById(localStorage.token, chatId);
			chat = updatedChat;
			share_id = chat.share_id; 

			sharedChatsUpdated.set(true);

			return shareUrl;
		} catch (error) {
			toast.error(error.detail);
			return null;
		}
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
					share_id = chat.share_id ?? ''; 

					if (chat.share_id) {
						qrCodeUrl = await QRCode.toDataURL(`${window.location.origin}/s/${chat.share_id}`);
					} else {
						qrCodeUrl = '';
					}
				}
			} else {
				chat = null;
				share_id = '';
				qrCodeUrl = '';
				console.log(chat);
			}
		})();
	} else {
		chat = null;
		share_id = '';
		qrCodeUrl = '';
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
			<div class="px-5 pt-4 pb-5 w-full flex flex-col">
				<div class=" text-sm dark:text-gray-300 mb-1">
					<div class="font-medium mb-2">How Sharing Works:</div>
					<ul class="list-disc list-inside space-y-1">
						<li>
							<strong>Creates a Snapshot:</strong>
							{$i18n.t(
								"Sharing creates a static, public snapshot of your conversation up to this point."
							)}
						</li>
						<li>
							<strong>Future Messages Not Included:</strong>
							{$i18n.t(
								"Any new messages you send after creating the link will not be added to the shared chat."
							)}
						</li>
						<li>
							<strong>Updating the Link:</strong>
							{$i18n.t(
								'You can update the link at any time to reflect the latest state of the conversation.'
							)}
						</li>
						<li>
							<strong>Link Persistence:</strong>
							{$i18n.t(
								'The link remains active as long as the original chat and the share link itself exist.'
							)}
						</li>
					</ul>
				</div>

				{#if chat.share_id}
					<div class="mt-2 flex items-center justify-between text-lg">
						<a
							href="/s/{chat.share_id}"
							target="_blank"
							class=" text-sm underline dark:text-gray-300 mb-1"
							>{$i18n.t('Current existing share link (click to view)')}</a
						>
						<button
							class="underline text-sm dark:text-white"
							on:click={async () => {
								const res = await deleteSharedChatById(localStorage.token, chatId);

								if (res) {
									chat = await getChatById(localStorage.token, chatId);
									share_id = '';
									qrCodeUrl = '';
									toast.success($i18n.t('Link deleted successfully'));
									sharedChatsUpdated.set(true);

									if (closeOnDelete) {
										show = false;
									}
								}
							}}
							>{$i18n.t('Delete Link')}
						</button>
					</div>
				{/if}

				<div class="mt-2 flex items-center gap-2">
					<div class="flex-1">
						<div
							class="flex items-center border rounded-lg dark:border-gray-700 focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500 overflow-hidden"
						>
							<span class="pl-3 pr-1 py-2 text-gray-500 dark:text-gray-400 select-none">/s/</span>
							<input
								class="flex-1 min-w-0 bg-transparent py-2 px-1 focus:outline-none dark:text-white"
								placeholder={$i18n.t('Enter a custom name (optional)')}
								bind:value={share_id}
								maxlength="144"
								on:input={() => {
									share_id = share_id
										.replace(/ /g, '-')
										.replace(/[^a-zA-Z0-9-._~]/g, '');
								}}
							/>
							<span class="pr-3 text-xs text-gray-500 dark:text-gray-400 shrink-0"
								>{share_id.length} / 144</span
							>
						</div>
					</div>
					<button
						class="flex items-center justify-center py-1.5 px-2.5 rounded-lg dark:text-white dark:hover:bg-gray-800 transition-colors"
						on:click={() => {
							share_id = uuidv4();
						}}
					>
						<ArrowPath className="size-6" />
					</button>
				</div>

				<div class="my-4 flex flex-col items-center justify-center">
					{#if qrCodeUrl}
						<a
							class="qr-code-container"
							href={qrCodeUrl}
							download="qrcode.png"
							on:click={() => {
								toast.success($i18n.t('Downloading QR code...'));
							}}
						>
							<img class="w-48 h-48 rounded-md" src={qrCodeUrl} alt="QR Code" />
						</a>
					{/if}
				</div>

				<div class="flex justify-center mt-3">
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
								<ArrowUpTray />
								{$i18n.t('Share to Open WebUI Community')}
							</button>
						{/if}

						<button
							class="self-center flex items-center gap-1 px-3.5 py-2 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
							type="button"
							id="copy-and-share-chat-button"
							on:click={async () => {
								const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);

								if (isSafari) {
									// Oh, Safari, you're so special, let's give you some extra love and attention
									console.log('isSafari');

									const getUrlPromise = async () => {
										const url = await shareLocalChat();
										if (url) {
											return new Blob([url], { type: 'text/plain' });
										}
										return new Blob([]);
									};

									navigator.clipboard
										.write([
											new ClipboardItem({
												'text/plain': getUrlPromise()
											})
										])
										.then(() => {
											console.log('Async: Copying to clipboard was successful!');
											toast.success($i18n.t('Copied shared chat URL to clipboard!'));
										})
										.catch((error) => {
											console.error('Async: Could not copy text: ', error);
										});
								} else {
									const url = await shareLocalChat();
									if (url) {
										copyToClipboard(url);
										toast.success($i18n.t('Copied shared chat URL to clipboard!'));
									}
								}
							}}
						>
							<Link />

							{$i18n.t(chat.share_id ? 'Update Link' : 'Create and Copy Link')}
						</button>
					</div>
				</div>
			</div>
		{/if}
	</div>
</Modal>

<style>
	.qr-code-container {
		position: relative;
		display: inline-block;
	}

	.qr-code-container::before {
		content: '';
		position: absolute;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		background-color: rgba(0, 0, 0, 0);
		transition: background-color 0.2s ease-in-out;
	}

	.qr-code-container:hover::before {
		background-color: rgba(0, 0, 0, 0.5);
	}

	.qr-code-container::after {
		content: '';
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		width: 48px;
		height: 48px;
		background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="white" class="w-12 h-12"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" /></svg>');
		background-size: contain;
		background-repeat: no-repeat;
		opacity: 0;
		transition: opacity 0.2s ease-in-out;
	}

	.qr-code-container:hover::after {
		opacity: 1;
	}
</style>