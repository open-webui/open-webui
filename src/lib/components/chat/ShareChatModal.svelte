<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import {
		models,
		config,
		sharedChats as sharedChatsStore,
		sharedChatsUpdated
	} from '$lib/stores';

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
	import Calendar from '$lib/components/icons/Calendar.svelte';
	import dayjs from 'dayjs';
	import customParseFormat from 'dayjs/plugin/customParseFormat';
	dayjs.extend(customParseFormat);

	const formatTimeRemaining = (expires_at) => {
		const now = new Date();
		const expirationDate = new Date(expires_at * 1000);
		const secondsRemaining = (expirationDate.getTime() - now.getTime()) / 1000;

		if (secondsRemaining <= 0) {
			return 'Expired';
		}

		const days = Math.floor(secondsRemaining / (3600 * 24));
		if (days > 0) return `in ${days} day${days > 1 ? 's' : ''}`;

		const hours = Math.floor(secondsRemaining / 3600);
		if (hours > 0) return `in ${hours} hour${hours > 1 ? 's' : ''}`;

		const minutes = Math.floor(secondsRemaining / 60);
		if (minutes > 0) return `in ${minutes} minute${minutes > 1 ? 's' : ''}`;

		return `in ${Math.floor(secondsRemaining)} second${
			Math.floor(secondsRemaining) !== 1 ? 's' : ''
		}`;
	};

	export let chatId;
	export let closeOnDelete = false;

	let chat = null;
	let timeRemaining = '';
	let intervalId = null;
	let shareUrl = null;
	let qrCodeUrl = '';
	let share_id = '';
	let initial_share_id = '';
	let expirationOption = 'never';
	let customExpirationDate = '';
	let expireOnViewsCount = 1;
	let initialExpirationOption = 'never';
	let initialCustomExpirationDate = '';
	let initialExpireOnViewsCount = 1;
	let currentViews = 0;
	const i18n = getContext('i18n');

	const handleExpirationChange = () => {
		if (expirationOption === 'custom' && !customExpirationDate) {
			customExpirationDate = dayjs().add(1, 'hour').format('YYYY-MM-DDTHH:mm');
		}
	};

	let expirationDateParts = {
		year: '',
		month: '',
		day: '',
		hour: '',
		minute: '',
		ampm: ''
	};

	$: {
		if (customExpirationDate) {
			const date = dayjs(customExpirationDate, 'YYYY-MM-DDTHH:mm');
			if (date.isValid()) {
				expirationDateParts = {
					year: date.format('YYYY'),
					month: date.format('MM'),
					day: date.format('DD'),
					hour: date.format('hh'),
					minute: date.format('mm'),
					ampm: date.format('A')
				};
			}
		}
	}


	const handleDateScroll = (event, part) => {
		event.preventDefault();

		if (!customExpirationDate) {
			// For empty dates, set to current time before adjusting
			customExpirationDate = dayjs().format('YYYY-MM-DDTHH:mm');
		}

		const date = dayjs(customExpirationDate, 'YYYY-MM-DDTHH:mm');
		const direction = event.deltaY < 0 ? 1 : -1; // scroll up increases, scroll down decreases

		let newDate;

		if (part === 'month') {
			newDate = date.add(direction, 'month');
		} else if (part === 'day') {
			newDate = date.add(direction, 'day');
		} else if (part === 'year') {
			newDate = date.add(direction, 'year');
		} else if (part === 'hour') {
			newDate = date.add(direction, 'hour');
		} else if (part === 'minute') {
			newDate = date.add(direction, 'minute');
		} else if (part === 'ampm') {
			const currentHour = date.hour();
			if (currentHour < 12) {
				newDate = date.hour(currentHour + 12); // Switch to PM
			} else {
				newDate = date.hour(currentHour - 12); // Switch to AM
			}
		}

		if (newDate && newDate.isValid()) {
			customExpirationDate = newDate.format('YYYY-MM-DDTHH:mm');
		}
	};

	const openDatePicker = () => {
		const picker = document.getElementById('hidden-datetime-picker');
		if (picker) {
			try {
				picker.showPicker();
			} catch (error) {
				// Fallback for browsers that don't support showPicker()
				console.error('showPicker() is not supported by this browser, falling back to click().', error);
				picker.click();
			}
		}
	};

	$: if (shareUrl) {
		(async () => {
			qrCodeUrl = await QRCode.toDataURL(shareUrl);
		})();
	} else {
		qrCodeUrl = '';
	}

	const formatISODate = (timestamp) => {
		const date = new Date(timestamp * 1000);
		const year = date.getFullYear();
		const month = (date.getMonth() + 1).toString().padStart(2, '0');
		const day = date.getDate().toString().padStart(2, '0');
		const hours = date.getHours().toString().padStart(2, '0');
		const minutes = date.getMinutes().toString().padStart(2, '0');
		return `${year}-${month}-${day}T${hours}:${minutes}`;
	};

	const expirationSettingsChanged = () => {
		if (expirationOption !== initialExpirationOption) {
			return true;
		}
		if (expirationOption === 'custom' && customExpirationDate !== initialCustomExpirationDate) {
			return true;
		}
		if (
			expirationOption === 'expire-on-views' &&
			expireOnViewsCount !== initialExpireOnViewsCount
		) {
			return true;
		}
		return false;
	};

	const shareLocalChat = async () => {
		if (
			expirationOption === 'expire-on-views' &&
			initial_share_id &&
			Number(expireOnViewsCount) <= currentViews
		) {
			toast.error(
				$i18n.t('Max views must be greater than the current view count ({{currentViews}}).', {
					currentViews: currentViews
				})
			);
			return null;
		}

		const idChanged = initial_share_id !== '' && share_id !== initial_share_id;
		const expirationChanged = expirationSettingsChanged();

		if (initial_share_id && !idChanged && !expirationChanged) {
			toast.info($i18n.t('No changes detected'));
			return null;
		}

		try {
			let expires_at = null;
			let expire_on_views = null;

			if (expirationOption === 'expire-on-views') {
				const count = Number(expireOnViewsCount);
				if (!isNaN(count) && count > 0) {
					expire_on_views = count;
				} else {
					toast.error('Number of views must be a valid number greater than 0.');
					return null;
				}
			} else if (expirationOption !== 'never') {
				if (expirationOption === 'custom') {
					const selectedDate = new Date(customExpirationDate);
					const now = new Date();
					selectedDate.setSeconds(now.getSeconds());

					if (selectedDate < now) {
						toast.error($i18n.t('The selected date and time cannot be in the past.'));
						return null;
					}
					expires_at = selectedDate.getTime() / 1000;
				} else {
					const now = new Date();
					if (expirationOption === '1h') {
						now.setHours(now.getHours() + 1);
					} else if (expirationOption === '24h') {
						now.setHours(now.getHours() + 24);
					} else if (expirationOption === '7d') {
						now.setDate(now.getDate() + 7);
					}
					expires_at = Math.floor(now.getTime() / 1000);
				}
			}

			if (initial_share_id && (idChanged || expirationChanged)) {
				const res = await deleteSharedChatById(localStorage.token, chatId);
				if (res) {
					toast.success($i18n.t('Old share link deleted successfully'));
				} else {
					toast.error($i18n.t('Failed to delete old share link'));
					return null;
				}
			}

			const sharedChat = await shareChatById(
				localStorage.token,
				chatId,
				share_id,
				expires_at,
				expire_on_views
			);

			// Update all state directly and atomically from the single API response.
			shareUrl = `${window.location.origin}/s/${sharedChat.id}`;
			share_id = sharedChat.id;
			initial_share_id = sharedChat.id;

			initialExpirationOption = expirationOption;
			initialCustomExpirationDate = customExpirationDate;
			initialExpireOnViewsCount = expireOnViewsCount;

			// Update the main chat object to reflect the new share status.
			chat = {
				...chat,
				share_id: sharedChat.id,
				expires_at: sharedChat.expires_at,
				expire_on_views: sharedChat.expire_on_views
			};

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
					initial_share_id = share_id;

					const sharedChatFromStore = $sharedChatsStore.find((c) => c.id === _chat.id);
					if (sharedChatFromStore) {
						currentViews = sharedChatFromStore.views;
					} else {
						currentViews = 0;
					}

					// New logic to correctly set expiration form state
					if (_chat.expire_on_views) {
						expirationOption = 'expire-on-views';
						expireOnViewsCount = _chat.expire_on_views;
						customExpirationDate = '';
					} else if (_chat.expires_at) {
						expirationOption = 'custom';
						customExpirationDate = formatISODate(_chat.expires_at);
						expireOnViewsCount = 1;
					} else {
						expirationOption = 'never';
						customExpirationDate = '';
						expireOnViewsCount = 1;
					}

					// Snapshot the newly set initial state
					initialExpirationOption = expirationOption;
					initialCustomExpirationDate = customExpirationDate;
					initialExpireOnViewsCount = expireOnViewsCount;

					if (chat.share_id) {
						shareUrl = `${window.location.origin}/s/${chat.share_id}`;
					} else {
						shareUrl = null;
					}

					if (intervalId) clearInterval(intervalId);
					if (chat.expires_at) {
						timeRemaining = formatTimeRemaining(chat.expires_at);
						intervalId = setInterval(() => {
							timeRemaining = formatTimeRemaining(chat.expires_at);
							if (timeRemaining === 'Expired') {
								clearInterval(intervalId);
							}
						}, 1000);
					} else {
						timeRemaining = '';
					}
				}
			} else {
				chat = null;
				share_id = '';
				initial_share_id = '';
				shareUrl = null;

				initialExpirationOption = 'never';
				initialCustomExpirationDate = '';
				initialExpireOnViewsCount = 1;
				console.log(chat);
			}
		})();
	} else {
		chat = null;
		share_id = '';
		initial_share_id = '';
		qrCodeUrl = '';
		expirationOption = 'never';
		customExpirationDate = '';
		expireOnViewsCount = 1;
		initialExpirationOption = 'never';
		initialCustomExpirationDate = '';
		initialExpireOnViewsCount = 1;

		if (intervalId) clearInterval(intervalId);
		timeRemaining = '';
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
								'The link remains active as long as the original chat exists and the expiration, if set, has not been reached.'
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
							>{$i18n.t('View existing share link')}</a
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

				<div class="mt-4">
					<label for="expiration" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Link Expiration')}</label>
					<select
						id="expiration"
						bind:value={expirationOption}
						on:change={handleExpirationChange}
						class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
					>
						<option value="never">{$i18n.t('Never')}</option>
						<option value="1h">{$i18n.t('1 Hour')}</option>
						<option value="24h">{$i18n.t('24 Hours')}</option>
						<option value="7d">{$i18n.t('7 Days')}</option>
						<option value="expire-on-views">{$i18n.t('Expire after a number of views')}</option>
						<option value="custom">{$i18n.t('Custom')}</option>
					</select>
				</div>

				{#if expirationOption === 'custom'}
					<div class="mt-4 relative">
						<div
							class="flex items-center mt-1 w-full pl-3 pr-2 py-0.5 text-base border border-gray-300 focus-within:ring-2 focus-within:ring-indigo-500 focus-within:border-indigo-500 sm:text-sm rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white"
						>
							<div class="flex-1">
								{#if customExpirationDate}
									<span class="flex items-center">
										<span
											class="cursor-pointer px-1 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
											on:wheel|preventDefault={(e) => handleDateScroll(e, 'month')}
											>{expirationDateParts.month}</span
										>
										<span>/</span>
										<span
											class="cursor-pointer px-1 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
											on:wheel|preventDefault={(e) => handleDateScroll(e, 'day')}
											>{expirationDateParts.day}</span
										>
										<span>/</span>
										<span
											class="cursor-pointer px-1 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
											on:wheel|preventDefault={(e) => handleDateScroll(e, 'year')}
											>{expirationDateParts.year}</span
										>
										<span
											class="ml-2 cursor-pointer px-1 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
											on:wheel|preventDefault={(e) => handleDateScroll(e, 'hour')}
											>{expirationDateParts.hour}</span
										>
										<span>:</span>
										<span
											class="cursor-pointer px-1 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
											on:wheel|preventDefault={(e) => handleDateScroll(e, 'minute')}
											>{expirationDateParts.minute}</span
										>
										<span
											class="ml-1 cursor-pointer px-1 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
											on:wheel|preventDefault={(e) => handleDateScroll(e, 'ampm')}
											>{expirationDateParts.ampm}</span
										>
									</span>
								{:else}
									<span class="text-gray-400 select-none py-2">Select a date and time</span>
								{/if}
							</div>

							<button
								type="button"
								class="p-2 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600"
								on:click={openDatePicker}
								aria-label="Open date picker"
							>
								<Calendar class="size-5" />
							</button>
						</div>
						<input
							type="datetime-local"
							bind:value={customExpirationDate}
							id="hidden-datetime-picker"
							class="absolute bottom-0 left-0 w-px h-px opacity-0"
						/>
					</div>
				{/if}

				{#if expirationOption === 'expire-on-views'}
					<div class="mt-4">
						<input type="number" min="1" bind:value={expireOnViewsCount} class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white" placeholder="Enter number of views" />
					</div>
				{/if}

				{#if chat.share_id && chat.expires_at}
					<div class="mt-2 text-sm text-gray-500 dark:text-gray-400">
						{$i18n.t('Expires on')} {new Date(chat.expires_at * 1000).toLocaleString()}
						{#if timeRemaining}
							<span class="font-semibold ml-1">({timeRemaining})</span>
						{/if}
					</div>
				{/if}

				{#if chat.share_id && chat.expire_on_views}
					<div class="mt-2 text-sm text-gray-500 dark:text-gray-400">
						{$i18n.t('Expires after')} {chat.expire_on_views} {$i18n.t('views')}
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