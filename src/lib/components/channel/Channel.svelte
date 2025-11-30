<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { Pane, PaneGroup, PaneResizer } from 'paneforge';

	import { onDestroy, onMount, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { v4 as uuidv4 } from 'uuid';

	import {
		chatId,
		channels,
		channelId as _channelId,
		showSidebar,
		socket,
		user
	} from '$lib/stores';
	import { getChannelById, getChannelMessages, sendMessage } from '$lib/apis/channels';

	import Messages from './Messages.svelte';
	import MessageInput from './MessageInput.svelte';
	import Navbar from './Navbar.svelte';
	import Drawer from '../common/Drawer.svelte';
	import EllipsisVertical from '../icons/EllipsisVertical.svelte';
	import Thread from './Thread.svelte';
	import i18n from '$lib/i18n';
	import Spinner from '../common/Spinner.svelte';

	export let id = '';

	let currentId = null;

	let scrollEnd = true;
	let messagesContainerElement = null;
	let chatInputElement = null;

	let top = false;

	let channel = null;
	let messages = null;

	let replyToMessage = null;
	let threadId = null;

	let typingUsers = [];
	let typingUsersTimeout = {};

	$: if (id) {
		initHandler();
	}

	const scrollToBottom = () => {
		if (messagesContainerElement) {
			messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
		}
	};

	const updateLastReadAt = async (channelId) => {
		$socket?.emit('events:channel', {
			channel_id: channelId,
			message_id: null,
			data: {
				type: 'last_read_at'
			}
		});

		channels.set(
			$channels.map((channel) => {
				if (channel.id === channelId) {
					return {
						...channel,
						unread_count: 0
					};
				}
				return channel;
			})
		);
	};

	const initHandler = async () => {
		if (currentId) {
			updateLastReadAt(currentId);
		}

		currentId = id;
		updateLastReadAt(id);
		_channelId.set(id);

		top = false;
		messages = null;
		channel = null;
		threadId = null;

		typingUsers = [];
		typingUsersTimeout = {};

		channel = await getChannelById(localStorage.token, id).catch((error) => {
			return null;
		});

		if (channel) {
			messages = await getChannelMessages(localStorage.token, id, 0);

			if (messages) {
				scrollToBottom();

				if (messages.length < 50) {
					top = true;
				}
			}
		} else {
			goto('/');
		}
	};

	const channelEventHandler = async (event) => {
		if (event.channel_id === id) {
			const type = event?.data?.type ?? null;
			const data = event?.data?.data ?? null;

			if (type === 'message') {
				if ((data?.parent_id ?? null) === null) {
					const tempId = data?.temp_id ?? null;
					messages = [{ ...data, temp_id: null }, ...messages.filter((m) => m?.temp_id !== tempId)];

					if (typingUsers.find((user) => user.id === event.user.id)) {
						typingUsers = typingUsers.filter((user) => user.id !== event.user.id);
					}

					await tick();
					if (scrollEnd) {
						scrollToBottom();
					}
				}
			} else if (type === 'message:update') {
				const idx = messages.findIndex((message) => message.id === data.id);

				if (idx !== -1) {
					messages[idx] = data;
				}
			} else if (type === 'message:delete') {
				messages = messages.filter((message) => message.id !== data.id);
			} else if (type === 'message:reply') {
				const idx = messages.findIndex((message) => message.id === data.id);

				if (idx !== -1) {
					messages[idx] = data;
				}
			} else if (type.includes('message:reaction')) {
				const idx = messages.findIndex((message) => message.id === data.id);
				if (idx !== -1) {
					messages[idx] = data;
				}
			} else if (type === 'typing' && event.message_id === null) {
				if (event.user.id === $user?.id) {
					return;
				}

				typingUsers = data.typing
					? [
							...typingUsers,
							...(typingUsers.find((user) => user.id === event.user.id)
								? []
								: [
										{
											id: event.user.id,
											name: event.user.name
										}
									])
						]
					: typingUsers.filter((user) => user.id !== event.user.id);

				if (typingUsersTimeout[event.user.id]) {
					clearTimeout(typingUsersTimeout[event.user.id]);
				}

				typingUsersTimeout[event.user.id] = setTimeout(() => {
					typingUsers = typingUsers.filter((user) => user.id !== event.user.id);
				}, 5000);
			}
		}
	};

	const submitHandler = async ({ content, data }) => {
		if (!content && (data?.files ?? []).length === 0) {
			return;
		}

		const tempId = uuidv4();

		const message = {
			temp_id: tempId,
			content: content,
			data: data,
			reply_to_id: replyToMessage?.id ?? null
		};

		const ts = Date.now() * 1000000; // nanoseconds
		messages = [
			{
				...message,
				id: tempId,
				user_id: $user?.id,
				user: $user,
				reply_to_message: replyToMessage ?? null,
				created_at: ts,
				updated_at: ts
			},
			...messages
		];

		const res = await sendMessage(localStorage.token, id, message).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
		}

		replyToMessage = null;
	};

	const onChange = async () => {
		$socket?.emit('events:channel', {
			channel_id: id,
			message_id: null,
			data: {
				type: 'typing',
				data: {
					typing: true
				}
			}
		});

		updateLastReadAt(id);
	};

	let mediaQuery;
	let largeScreen = false;

	onMount(() => {
		if ($chatId) {
			chatId.set('');
		}

		$socket?.on('events:channel', channelEventHandler);

		mediaQuery = window.matchMedia('(min-width: 1024px)');

		const handleMediaQuery = async (e) => {
			if (e.matches) {
				largeScreen = true;
			} else {
				largeScreen = false;
			}
		};

		mediaQuery.addEventListener('change', handleMediaQuery);
		handleMediaQuery(mediaQuery);
	});

	onDestroy(() => {
		// last read at
		updateLastReadAt(id);
		_channelId.set(null);
		$socket?.off('events:channel', channelEventHandler);
	});
</script>

<svelte:head>
	{#if channel?.type === 'dm'}
		<title
			>{channel?.name.trim() ||
				channel?.users.reduce((a, e, i, arr) => {
					if (e.id === $user?.id) {
						return a;
					}

					if (a) {
						return `${a}, ${e.name}`;
					} else {
						return e.name;
					}
				}, '')} • Open WebUI</title
		>
	{:else}
		<title>#{channel?.name ?? 'Channel'} • Open WebUI</title>
	{/if}
</svelte:head>

<div
	class="h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-260px)]'
		: ''} w-full max-w-full flex flex-col"
	id="channel-container"
>
	<PaneGroup direction="horizontal" class="w-full h-full">
		<Pane defaultSize={50} minSize={50} class="h-full flex flex-col w-full relative">
			<Navbar
				{channel}
				onPin={(messageId, pinned) => {
					messages = messages.map((message) => {
						if (message.id === messageId) {
							return {
								...message,
								is_pinned: pinned
							};
						}
						return message;
					});
				}}
				onUpdate={async () => {
					channel = await getChannelById(localStorage.token, id).catch((error) => {
						return null;
					});
				}}
			/>

			{#if channel && messages !== null}
				<div class="flex-1 overflow-y-auto">
					<div
						class=" pb-2.5 max-w-full z-10 scrollbar-hidden w-full h-full pt-6 flex-1 flex flex-col-reverse overflow-auto"
						id="messages-container"
						bind:this={messagesContainerElement}
						on:scroll={(e) => {
							scrollEnd = Math.abs(messagesContainerElement.scrollTop) <= 50;
						}}
					>
						{#key id}
							<Messages
								{channel}
								{top}
								{messages}
								{replyToMessage}
								onReply={async (message) => {
									replyToMessage = message;
									await tick();
									chatInputElement?.focus();
								}}
								onThread={(id) => {
									threadId = id;
								}}
								onLoad={async () => {
									const newMessages = await getChannelMessages(
										localStorage.token,
										id,
										messages.length
									);

									messages = [...messages, ...newMessages];

									if (newMessages.length < 50) {
										top = true;
										return;
									}
								}}
							/>
						{/key}
					</div>
				</div>

				<div class=" pb-[1rem] px-2.5">
					<MessageInput
						id="root"
						bind:chatInputElement
						bind:replyToMessage
						{typingUsers}
						userSuggestions={true}
						channelSuggestions={true}
						disabled={!channel?.write_access}
						placeholder={!channel?.write_access
							? $i18n.t('You do not have permission to send messages in this channel.')
							: $i18n.t('Type here...')}
						{onChange}
						onSubmit={submitHandler}
						{scrollToBottom}
						{scrollEnd}
					/>
				</div>
			{:else}
				<div class=" flex items-center justify-center h-full w-full">
					<div class="m-auto">
						<Spinner className="size-5" />
					</div>
				</div>
			{/if}
		</Pane>

		{#if !largeScreen}
			{#if threadId !== null}
				<Drawer
					show={threadId !== null}
					onClose={() => {
						threadId = null;
					}}
				>
					<div class=" {threadId !== null ? ' h-screen  w-full' : 'px-6 py-4'} h-full">
						<Thread
							{threadId}
							{channel}
							onClose={() => {
								threadId = null;
							}}
						/>
					</div>
				</Drawer>
			{/if}
		{:else if threadId !== null}
			<PaneResizer
				class="relative flex items-center justify-center group border-l border-gray-50 dark:border-gray-850/30 hover:border-gray-200 dark:hover:border-gray-800  transition z-20"
				id="controls-resizer"
			>
				<div
					class=" absolute -left-1.5 -right-1.5 -top-0 -bottom-0 z-20 cursor-col-resize bg-transparent"
				/>
			</PaneResizer>

			<Pane defaultSize={50} minSize={30} class="h-full w-full">
				<div class="h-full w-full shadow-xl">
					<Thread
						{threadId}
						{channel}
						onClose={() => {
							threadId = null;
						}}
					/>
				</div>
			</Pane>
		{/if}
	</PaneGroup>
</div>
