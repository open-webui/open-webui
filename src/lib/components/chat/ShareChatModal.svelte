<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';
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
	import Tooltip from '../common/Tooltip.svelte';
	import Switch from '../common/Switch.svelte';
	import Link from '../icons/Link.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import ArrowPath from '$lib/components/icons/ArrowPath.svelte';
	import ArrowDownTray from '$lib/components/icons/ArrowDownTray.svelte';
	import ArrowUpTray from '$lib/components/icons/ArrowUpTray.svelte';
	import Calendar from '$lib/components/icons/Calendar.svelte';
	import Eye from '$lib/components/icons/Eye.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Clipboard from '$lib/components/icons/Clipboard.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import QuestionMarkCircle from '$lib/components/icons/QuestionMarkCircle.svelte';
	import dayjs from 'dayjs';
	import customParseFormat from 'dayjs/plugin/customParseFormat';
	dayjs.extend(customParseFormat);

	const formatTimeRemaining = (expires_at) => {
		const now = new Date();
		const expirationDate = new Date(expires_at * 1000);
		const secondsRemaining = (expirationDate.getTime() - now.getTime()) / 1000;

		if (secondsRemaining <= 0) {
			return $i18n.t('Expired');
		}

		const days = Math.floor(secondsRemaining / (3600 * 24));
		const years = Math.floor(days / 365);
		if (years > 0) {
			return years === 1
				? $i18n.t('in {{count}} year', { count: years })
				: $i18n.t('in {{count}} years', { count: years });
		}

		const weeks = Math.floor(days / 7);
		if (weeks > 0) {
			return weeks === 1
				? $i18n.t('in {{count}} week', { count: weeks })
				: $i18n.t('in {{count}} weeks', { count: weeks });
		}

		if (days > 0) {
			return days === 1
				? $i18n.t('in {{count}} day', { count: days })
				: $i18n.t('in {{count}} days', { count: days });
		}

		const hours = Math.floor(secondsRemaining / 3600);
		if (hours > 0) {
			return hours === 1
				? $i18n.t('in {{count}} hour', { count: hours })
				: $i18n.t('in {{count}} hours', { count: hours });
		}

		const minutes = Math.floor(secondsRemaining / 60);
		if (minutes > 0) {
			return minutes === 1
				? $i18n.t('in {{count}} minute', { count: minutes })
				: $i18n.t('in {{count}} minutes', { count: minutes });
		}

		const seconds = Math.floor(secondsRemaining);
		return seconds === 1
			? $i18n.t('in {{count}} second', { count: seconds })
			: $i18n.t('in {{count}} seconds', { count: seconds });
	};

	export let chatId;
	export let closeOnDelete = false;

	let chat = null;
	let timeRemaining = '';
	let intervalId = null;
	let previewQrCodeUrl = '';
	let downloadQrCodeUrl = '';
	let share_id = '';
	$: shareUrl = share_id ? `${window.location.origin}/s/${share_id}` : null;
	let initial_share_id = '';
	let expirationOption = 'never';
	let customExpirationDate = '';
	let minDateTime = '';
	let expireOnViewsCount = 1;
	let initialExpirationOption = 'never';
	let initialCustomExpirationDate = '';
	let initialExpireOnViewsCount = 1;
	let is_public = false;
	let initial_is_public = false;
	let currentViews = 0;
	const i18n = getContext('i18n');

	let isExpirationDropdownOpen = false;

	let expirationOptions = [];
	$: expirationOptions = [
		{ value: 'never', label: $i18n.t('Never') },
		{ value: '1h', label: $i18n.t('1 Hour') },
		{ value: '24h', label: $i18n.t('24 Hours') },
		{ value: '7d', label: $i18n.t('7 Days') },
		{ value: 'expire-on-views', label: $i18n.t('Expire after a number of views') },
		{ value: 'custom', label: $i18n.t('Custom') }
	];

	$: selectedExpirationIndex = expirationOptions.findIndex((o) => o.value === expirationOption);

	const handleExpirationScroll = (event) => {
		event.preventDefault();
		const direction = event.deltaY < 0 ? -1 : 1;
		let newIndex = selectedExpirationIndex + direction;

		if (newIndex < 0) {
			newIndex = expirationOptions.length - 1;
		} else if (newIndex >= expirationOptions.length) {
			newIndex = 0;
		}
		expirationOption = expirationOptions[newIndex].value;
	};

	function clickOutside(node) {
		const handleClick = (event) => {
			if (node && !node.contains(event.target) && !event.defaultPrevented) {
				isExpirationDropdownOpen = false;
			}
		};
		document.addEventListener('click', handleClick, true);
		return {
			destroy() {
				document.removeEventListener('click', handleClick, true);
			}
		};
	}

	const handleExpirationChange = () => {
		if (expirationOption === 'custom') {
			const date = dayjs(customExpirationDate, 'YYYY-MM-DDTHH:mm');
			if (!customExpirationDate || date.isBefore(dayjs())) {
				customExpirationDate = dayjs().add(1, 'hour').format('YYYY-MM-DDTHH:mm');
			}
		} else if (expirationOption === 'expire-on-views') {
			if (expireOnViewsCount <= currentViews) {
				expireOnViewsCount = currentViews + 1;
			}
		}
	};

	$: if (expirationOption) {
		handleExpirationChange();
	}

	const validateViewsCount = () => {
		if (Number(expireOnViewsCount) <= currentViews) {
			toast.warning(
				`Max views must be greater than the current view count (${currentViews}). Setting to ${
					currentViews + 1
				}.`
			);
			expireOnViewsCount = currentViews + 1;
		}
	};

	const handleViewsScroll = (event) => {
		const direction = event.deltaY < 0 ? 1 : -1;
		const newCount = Number(expireOnViewsCount) + direction;

		if (newCount > currentViews) {
			expireOnViewsCount = newCount;
		} else {
			expireOnViewsCount = currentViews + 1;
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

		if (newDate && newDate.isValid() && !newDate.isBefore(dayjs())) {
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

	const debounce = (func, timeout = 300) => {
		let timer;
		return (...args) => {
			clearTimeout(timer);
			timer = setTimeout(() => {
				func.apply(this, args);
			}, timeout);
		};
	};

	const generateQrCodesImmediate = async (url) => {
		if (url) {
			previewQrCodeUrl = await QRCode.toDataURL(url, { width: 192 });
			downloadQrCodeUrl = await QRCode.toDataURL(url, { width: 512 });
		} else {
			previewQrCodeUrl = '';
			downloadQrCodeUrl = '';
		}
	};

	const generateQrCodesDebounced = debounce(generateQrCodesImmediate, 500);

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
		if (is_public !== initial_is_public) {
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
				expire_on_views,
				is_public
			);

			// Update all state directly and atomically from the single API response.
			share_id = sharedChat.id;
			initial_share_id = sharedChat.id;

			initialExpirationOption = expirationOption;
			initialCustomExpirationDate = customExpirationDate;
			initialExpireOnViewsCount = expireOnViewsCount;
			initial_is_public = is_public;

			// Update the main chat object to reflect the new share status.
			chat = {
				...chat,
				share_id: sharedChat.id,
				expires_at: sharedChat.expires_at,
				expire_on_views: sharedChat.expire_on_views,
				is_public: sharedChat.is_public
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
		minDateTime = dayjs().format('YYYY-MM-DDTHH:mm');

		(async () => {
			if (chatId) {
				const _chat = await getChatById(localStorage.token, chatId);
				if (isDifferentChat(_chat)) {
					chat = _chat;
					share_id = chat.share_id ?? '';
					initial_share_id = share_id;

					generateQrCodesImmediate(share_id ? `${window.location.origin}/s/${share_id}` : null);

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

					is_public = _chat.is_public ?? false;
					initial_is_public = is_public;

					// Snapshot the newly set initial state
					initialExpirationOption = expirationOption;
					initialCustomExpirationDate = customExpirationDate;
					initialExpireOnViewsCount = expireOnViewsCount;

					if (intervalId) clearInterval(intervalId);
					if (chat.expires_at) {
						timeRemaining = formatTimeRemaining(chat.expires_at);
						intervalId = setInterval(() => {
							timeRemaining = formatTimeRemaining(chat.expires_at);
							if (timeRemaining === 'Expired') {
								if (expirationOption === 'custom') {
									customExpirationDate = dayjs().add(1, 'hour').format('YYYY-MM-DDTHH:mm');
								}
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
		previewQrCodeUrl = '';
		downloadQrCodeUrl = '';
		expirationOption = 'never';
		customExpirationDate = '';
		is_public = false;
		initial_is_public = false;
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
			<div class=" text-lg font-medium self-center flex items-center space-x-2">
				{$i18n.t('Share Chat')}
				<Tooltip placement="right" interactive={true}>
					<QuestionMarkCircle class="cursor-pointer text-gray-500 size-5" />
					<div class="p-2 text-sm" slot="tooltip">
						<div class="font-medium mb-2">{$i18n.t('How Sharing Works:')}</div>
						<ul class="list-disc list-inside space-y-1">
							<li>
								<strong>{$i18n.t('Creates a Snapshot:')}</strong>
								{$i18n.t(
									'Sharing creates a static, public snapshot of your conversation up to this point.'
								)}
							</li>
							<li>
								<strong>{$i18n.t('Future Messages Not Included:')}</strong>
								{$i18n.t(
									'Any new messages you send after creating the link will not be added to the shared chat.'
								)}
							</li>
							<li>
								<strong>{$i18n.t('Updating the Link:')}</strong>
								{$i18n.t(
									'You can update the link at any time to reflect the latest state of the conversation.'
								)}
							</li>
							<li>
								<strong>{$i18n.t('Link Persistence:')}</strong>
								{$i18n.t(
									'The link remains active as long as the original chat exists and the expiration, if set, has not been reached.'
								)}
							</li>
						</ul>
					</div>
				</Tooltip>
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		{#if chat && chat.chat}
			<div class="px-5 pt-2 text-sm text-gray-500 dark:text-gray-400 truncate">
				{chat.chat.title}
			</div>
		{/if}

		{#if chat}
			<div class="px-5 pt-4 pb-5 w-full flex flex-col">
				<div class="mt-4">
					<div class="flex items-center justify-between">
						<label for="is_public" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
							{$i18n.t('Public Access')}
						</label>
						<Switch bind:state={is_public} tooltip={true} />
					</div>
					<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
						{$i18n.t(
							'When enabled, anyone with the link can view the chat. When disabled, only logged-in users can view the chat.'
						)}
					</p>
				</div>

				<div class="mt-4 relative" use:clickOutside>
					<label for="expiration" class="block text-sm font-medium text-gray-700 dark:text-gray-300"
						>{$i18n.t('Link Expiration')}</label
					>
					<button
						type="button"
						class="mt-1 relative block w-full cursor-pointer text-left pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white"
						on:click={() => (isExpirationDropdownOpen = !isExpirationDropdownOpen)}
						on:wheel|preventDefault={handleExpirationScroll}
					>
						<span class="block truncate">{expirationOptions[selectedExpirationIndex]?.label ?? ''}</span>
						<span class="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
							<ChevronDown class="h-5 w-5 text-gray-400" />
						</span>
					</button>

					{#if isExpirationDropdownOpen}
						<ul
							class="absolute z-10 mt-1 w-full rounded-md bg-white shadow-lg border border-gray-200 dark:bg-gray-700 dark:border-gray-600"
						>
							{#each expirationOptions as option, i}
								<li
									class="relative cursor-pointer select-none py-2 pl-3 pr-9 text-gray-900 dark:text-white hover:bg-indigo-600 hover:text-white"
									on:click={() => {
										expirationOption = option.value;
										isExpirationDropdownOpen = false;
									}}
								>
									<span class="block truncate">{option.label}</span>
								</li>
							{/each}
						</ul>
					{/if}
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
							min={minDateTime}
						/>
					</div>
				{/if}


				{#if expirationOption === 'expire-on-views'}
					<div class="mt-4">
						<input
							type="number"
							min="1"
							bind:value={expireOnViewsCount}
							on:blur={validateViewsCount}
							on:wheel|preventDefault={handleViewsScroll}
							class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
							placeholder="Enter number of views"
						/>
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
								value={share_id}
								maxlength="144"
								on:input={(e) => {
									const sanitized = e.target.value.replace(/ /g, '-').replace(/[^a-zA-Z0-9-._~]/g, '');
									if (share_id !== sanitized) {
										share_id = sanitized;
										generateQrCodesDebounced(
											share_id ? `${window.location.origin}/s/${share_id}` : null
										);
									}
								}}
							/>
							<span class="pr-3 text-xs text-gray-500 dark:text-gray-400 shrink-0"
								>{share_id.length} / 144</span
							>
						</div>
					</div>

					<div class="flex items-center gap-2">
						{#if chat.share_id}
							<Tooltip content={$i18n.t('Generate New ID')}>
								<button
									class="flex items-center justify-center p-2 rounded-lg dark:text-white bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
									on:click={() => {
										share_id = uuidv4();
										generateQrCodesImmediate(
											share_id ? `${window.location.origin}/s/${share_id}` : null
										);
									}}
								>
									<ArrowPath class="size-5" />
								</button>
							</Tooltip>
							<Tooltip content={$i18n.t('Copy Link')}>
								<button
									class="flex items-center justify-center p-2 rounded-lg dark:text-white bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
									on:click={() => {
										copyToClipboard(shareUrl);
										toast.success($i18n.t('Copied shared chat URL to clipboard!'));
									}}
								>
									<Clipboard class="size-5" />
								</button>
							</Tooltip>
							<Tooltip content={$i18n.t('View Link')}>
								<a
									href={shareUrl}
									target="_blank"
									class="flex items-center justify-center p-2 rounded-lg dark:text-white bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
								>
									<Eye class="size-5" />
								</a>
							</Tooltip>
							<Tooltip content={$i18n.t('Delete Link')}>
								<button
									class="flex items-center justify-center p-2 rounded-lg text-red-600 dark:text-red-500 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
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
								>
									<GarbageBin class="size-5" />
								</button>
							</Tooltip>
						{:else}
							<Tooltip content={$i18n.t('Generate Random ID')}>
								<button
									class="flex items-center justify-center p-2 rounded-lg dark:text-white bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
									on:click={() => {
										share_id = uuidv4();
									}}
								>
									<ArrowPath class="size-5" />
								</button>
							</Tooltip>
						{/if}
					</div>
				</div>

				<div class="my-4 flex flex-col items-center justify-center">
					{#if previewQrCodeUrl}
						<a
							class="qr-code-container"
							href={downloadQrCodeUrl}
							download="qrcode.png"
							on:click={() => {
								toast.success($i18n.t('Downloading QR code...'));
							}}
						>
							<img class="w-48 h-48 rounded-md" src={previewQrCodeUrl} alt="QR Code" />
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
							{$i18n.t(chat.share_id ? 'Update Link Settings' : 'Create Link')}
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