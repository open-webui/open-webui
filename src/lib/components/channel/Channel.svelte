<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { onDestroy, onMount, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { v4 as uuidv4 } from 'uuid';
	import type { Socket } from 'socket.io-client';

	import {
		config,
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
	import { canUseEncryption, connected, enter, request } from '$lib/encryption/client';
	import Drawer from '../common/Drawer.svelte';
	import ResizableSidePanel from '../common/ResizableSidePanel.svelte';
	import EllipsisVertical from '../icons/EllipsisVertical.svelte';
	import Thread from './Thread.svelte';
	import i18n from '$lib/i18n';
	import Spinner from '../common/Spinner.svelte';

	export let id = '';

	let mounted = false;
	let invitationSession: string | null = null;
	let stopInvitation = () => {};
	$: watchInvitation(
		$socket,
		channel?.id === id ? id : null,
		mounted && canUseEncryption($user, $config?.features)
	);

	function watchInvitation(
		connection: Socket | null,
		channelId: string | null,
		enabled: boolean | undefined
	) {
		stopInvitation();
		stopInvitation = () => {};
		invitationSession = null;
		if (!enabled || !connection || !channelId) return;
		let alive = true;
		let revision = 0;
		const receive = (event: { channel: string; session: string | null }) => {
			if (event.channel === channelId) {
				revision++;
				invitationSession = event.session;
			}
		};
		const clear = () => {
			revision++;
			invitationSession = null;
		};
		const query = () => {
			if (!connected(connection)) return;
			const issued = revision;
			void request(connection, 'status', { channel: channelId })
				.then((result) => {
					if (alive && revision === issued)
						invitationSession = result.available ? result.session : null;
				})
				.catch(() => {});
		};
		connection.on('encryption:available', receive);
		connection.on('disconnect', clear);
		connection.on('connect', query);
		query();
		stopInvitation = () => {
			alive = false;
			connection.off('encryption:available', receive);
			connection.off('disconnect', clear);
			connection.off('connect', query);
		};
	}

	let currentId = null;

	let scrollEnd = true;
	let messagesContainerElement = null;
	let chatInputElement = null;

	let top = false;

	let channel: any = null;
	let messages = null;

	let replyToMessage = null;
	let threadId: any = null;

	let typingUsers = [];
	let typingUsersTimeout = {};

	$: if (id) {
		initHandler();
	}

	$: if (channel && $page.url.searchParams.get('thread')) {
		threadId = $page.url.searchParams.get('thread');
		if (!$page.url.searchParams.has('message')) {
			window.history.replaceState(history.state, '', `/channels/${id}`);
		}
	}

	const scrollToBottom = () => {
		if (messagesContainerElement) {
			// The channel uses flex-col-reverse, whose bottom is scrollTop = 0.
			messagesContainerElement.scrollTop = 0;
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

	const pinHandler = (
		messageId: string,
		pinned: boolean,
		pinnedBy: string | null = pinned ? ($user?.id ?? null) : null,
		pinnedAt: number | null = pinned ? Date.now() * 1000000 : null
	) => {
		if (messages) {
			messages = messages.map((message) => {
				if (message.id === messageId) {
					return {
						...message,
						is_pinned: pinned,
						pinned_by: pinnedBy,
						pinned_at: pinnedAt
					};
				}
				return message;
			});
		}
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
		replyToMessage = null;

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
					const idx = (messages ?? []).findIndex(
						(message) =>
							message.id === data.id || (data.temp_id && message.temp_id === data.temp_id)
					);
					if (idx === -1) {
						messages = [{ ...data, temp_id: null }, ...(messages ?? [])];
					} else {
						// Confirm the existing row without changing its position or render key.
						const previous = messages[idx];
						messages[idx] = {
							...previous,
							...data,
							temp_id: null,
							client_id: previous.client_id ?? previous.id
						};
					}

					if (typingUsers.find((user) => user.id === event.user.id)) {
						typingUsers = typingUsers.filter((user) => user.id !== event.user.id);
					}

					await tick();
					if (idx === -1 && scrollEnd) {
						scrollToBottom();
					}
				}
			} else if (type === 'message:update') {
				const idx = messages.findIndex((message) => message.id === data.id);

				if (idx !== -1) {
					messages[idx] = { ...messages[idx], ...data };
				}
			} else if (type === 'message:delete') {
				messages = messages
					.filter((message) => message.id !== data.id)
					.map((message) =>
						message?.reply_to_message?.id === data.id
							? { ...message, reply_to_message: null }
							: message
					);

				if (replyToMessage?.id === data.id) {
					replyToMessage = null;
				}

				if (threadId === data.id) {
					threadId = null;
				}
			} else if (type === 'message:reply') {
				const idx = messages.findIndex((message) => message.id === data.id);

				if (idx !== -1) {
					messages[idx] = { ...messages[idx], ...data };
				}
			} else if (type.includes('message:reaction')) {
				const idx = messages.findIndex((message) => message.id === data.id);
				if (idx !== -1) {
					messages[idx] = { ...messages[idx], ...data };
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

	const submitHandler = async ({
		content,
		data,
		channel_id,
		reply_to_message
	}: {
		content: string;
		data: any;
		channel_id: string;
		reply_to_message: any;
	}) => {
		if (!content && (data?.files ?? []).length === 0) {
			return;
		}

		const tempId = uuidv4();

		const message = {
			temp_id: tempId,
			content: content,
			data: data,
			reply_to_id: reply_to_message?.id ?? null
		};

		const ts = Date.now() * 1000000; // nanoseconds
		messages = [
			{
				...message,
				id: tempId,
				client_id: tempId,
				user_id: $user?.id,
				user: $user,
				reply_to_message: reply_to_message ?? null,
				created_at: ts,
				updated_at: ts
			},
			...messages
		];

		await tick();
		if (id === channel_id) scrollToBottom();

		await sendMessage(localStorage.token, channel_id, message).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
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
	let threadPanelWidth = 420;

	const handleMediaQuery = (e) => {
		largeScreen = e.matches;
	};

	onMount(() => {
		mounted = true;
		if ($chatId) {
			chatId.set('');
		}

		$socket?.on('events:channel', channelEventHandler);

		mediaQuery = window.matchMedia('(min-width: 1024px)');

		mediaQuery.addEventListener('change', handleMediaQuery);
		handleMediaQuery(mediaQuery);
	});

	onDestroy(() => {
		stopInvitation();
		// last read at
		updateLastReadAt(id);
		_channelId.set(null);
		$socket?.off('events:channel', channelEventHandler);
		mediaQuery?.removeEventListener('change', handleMediaQuery);
	});
</script>

<svelte:head>
	<!-- LICENSE covers this Open WebUI browser-title identifier.
	Do not alter, remove, obscure, or replace it except as LICENSE permits:
	https://docs.openwebui.com/license. -->
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
				}, '')} / Open WebUI</title
		>
	{:else}
		<title>#{channel?.name ?? 'Channel'} / Open WebUI</title>
	{/if}
</svelte:head>

<div
	class="h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''} w-full max-w-full flex flex-col"
	id="channel-container"
>
	<div class="w-full h-full flex">
		<div class="h-full flex flex-col min-w-0 flex-1 relative">
			<Navbar
				{channel}
				onPin={pinHandler}
				onUpdate={async () => {
					channel = await getChannelById(localStorage.token, id).catch((error) => {
						return null;
					});
				}}
			>
				<svelte:fragment slot="subtitle">
					{#if invitationSession}
						<div
							class="flex flex-wrap items-center gap-x-1.5 text-[0.6875rem] font-normal text-gray-500 dark:text-gray-400"
						>
							<span>{$i18n.t('Encrypted chat in progress')}</span>
							<span aria-hidden="true">·</span>
							<button
								type="button"
								aria-label={$i18n.t('Join encrypted chat')}
								class="text-[0.6875rem] font-normal text-gray-700 underline-offset-2 hover:underline dark:text-gray-200"
								on:click={() => {
									if (!invitationSession || !canUseEncryption($user, $config?.features)) return;
									enter(id, { action: 'join', session: invitationSession });
									void goto(`/channels/${encodeURIComponent(id)}/encrypted`);
								}}
							>
								{$i18n.t('Join')}
							</button>
						</div>
					{/if}
				</svelte:fragment>
			</Navbar>

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
								bind:messages
								{replyToMessage}
								onReply={async (message) => {
									replyToMessage = message;
									await tick();
									chatInputElement?.focus();
								}}
								onThread={(id) => {
									threadId = id;
								}}
								onPin={pinHandler}
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

				<div class=" pb-3 px-3">
					<MessageInput
						id="root"
						{messages}
						bind:chatInputElement
						bind:replyToMessage
						{typingUsers}
						{channel}
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
		</div>

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
							onPin={pinHandler}
							onClose={() => {
								threadId = null;
							}}
						/>
					</div>
				</Drawer>
			{/if}
		{:else if threadId !== null}
			<ResizableSidePanel
				open={true}
				bind:width={threadPanelWidth}
				minWidth={320}
				maxWidth={640}
				className="h-full"
			>
				<div class="h-full w-full border-l border-gray-100/60 dark:border-gray-800/40">
					<Thread
						{threadId}
						{channel}
						onPin={pinHandler}
						onClose={() => {
							threadId = null;
						}}
					/>
				</div>
			</ResizableSidePanel>
		{/if}
	</div>
</div>
