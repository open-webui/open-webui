<script lang="ts">
	import { goto } from '$app/navigation';

	import { socket, user } from '$lib/stores';

	import { getChannelThreadMessages, sendMessage } from '$lib/apis/channels';

	import XMark from '$lib/components/icons/XMark.svelte';
	import MessageInput from './MessageInput.svelte';
	import Messages from './Messages.svelte';
	import { onDestroy, onMount, tick, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Spinner from '../common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let threadId = null;
	export let channel = null;

	export let onClose = () => {};
	export let onPin = () => {};

	let messages = null;
	let top = false;

	let messagesContainerElement = null;
	let chatInputElement = null;

	let replyToMessage = null;

	let typingUsers = [];
	let typingUsersTimeout = {};

	$: if (threadId) {
		initHandler();
	}

	const scrollToBottom = () => {
		if (messagesContainerElement) {
			messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
		}
	};

	const initHandler = async () => {
		messages = null;
		top = false;

		typingUsers = [];
		typingUsersTimeout = {};

		if (channel) {
			messages = await getChannelThreadMessages(localStorage.token, channel.id, threadId);

			if (messages.length < 50) {
				top = true;
			}

			await tick();
			scrollToBottom();
		} else {
			goto('/');
		}
	};

	const channelEventHandler = async (event) => {
		console.debug(event);
		if (event.channel_id === channel.id) {
			const type = event?.data?.type ?? null;
			const data = event?.data?.data ?? null;

			if (type === 'message') {
				if ((data?.parent_id ?? null) === threadId) {
					if (messages) {
						messages = [{ ...data, temp_id: null }, ...messages];

						if (typingUsers.find((user) => user.id === event.user.id)) {
							typingUsers = typingUsers.filter((user) => user.id !== event.user.id);
						}
					}
				}
			} else if (type === 'message:update') {
				if (messages) {
					const idx = messages.findIndex((message) => message.id === data.id);

					if (idx !== -1) {
						messages[idx] = data;
					}
				}
			} else if (type === 'message:delete') {
				if (data.id === threadId) {
					onClose();
				}

				if (messages) {
					messages = messages
						.filter((message) => message.id !== data.id)
						.map((message) =>
							message?.reply_to_message?.id === data.id
								? { ...message, reply_to_message: null }
								: message
						);
				}

				if (replyToMessage?.id === data.id) {
					replyToMessage = null;
				}
			} else if (type.includes('message:reaction')) {
				if (messages) {
					const idx = messages.findIndex((message) => message.id === data.id);
					if (idx !== -1) {
						messages[idx] = data;
					}
				}
			} else if (type === 'typing' && event.message_id === threadId) {
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
		parent_id,
		reply_to_message
	}: {
		content: string;
		data: any;
		channel_id: string;
		parent_id: string | null;
		reply_to_message: any;
	}) => {
		if (!content && (data?.files ?? []).length === 0) {
			return;
		}

		const res = await sendMessage(localStorage.token, channel_id, {
			parent_id: parent_id ?? undefined,
			reply_to_id: reply_to_message?.id ?? null,
			content: content,
			data: data
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
	};

	const onChange = async () => {
		$socket?.emit('events:channel', {
			channel_id: channel.id,
			message_id: threadId,
			data: {
				type: 'typing',
				data: {
					typing: true
				}
			}
		});
	};

	onMount(() => {
		$socket?.on('events:channel', channelEventHandler);
	});

	onDestroy(() => {
		$socket?.off('events:channel', channelEventHandler);
	});
</script>

{#if channel}
	<div class="flex flex-col w-full h-full bg-white dark:bg-gray-900">
		<div
			class="sticky top-0 flex min-h-10 items-center justify-between border-b border-gray-100/60 px-4 py-1.5 dark:border-gray-800/40"
		>
			<div class=" font-medium text-sm">{$i18n.t('Thread')}</div>

			<div>
				<button
					type="button"
					aria-label={$i18n.t('Close')}
					class="flex size-7 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-50/60 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800/60 dark:hover:text-gray-300"
					on:click={() => {
						onClose();
					}}
				>
					<XMark className="size-4" />
				</button>
			</div>
		</div>

		<div
			class="flex-1 min-h-0 w-full overflow-y-auto will-change-transform"
			bind:this={messagesContainerElement}
		>
			<div class="pt-3">
				{#if messages !== null}
					<Messages
						id={threadId}
						{channel}
						{top}
						{messages}
						{replyToMessage}
						thread={true}
						{onPin}
						onReply={async (message) => {
							replyToMessage = message;

							await tick();
							chatInputElement?.focus();
						}}
						onLoad={async () => {
							const newMessages = await getChannelThreadMessages(
								localStorage.token,
								channel.id,
								threadId,
								messages.length
							);

							messages = [...messages, ...newMessages];

							if (newMessages.length < 50) {
								top = true;
								return;
							}
						}}
					/>
				{:else}
					<div class="w-full flex justify-center pt-5 pb-10">
						<Spinner />
					</div>
				{/if}
			</div>
		</div>

		<div class=" pb-3 px-3 w-full">
			<MessageInput
				bind:replyToMessage
				bind:chatInputElement
				id={threadId}
				{channel}
				disabled={!channel?.write_access}
				placeholder={!channel?.write_access
					? $i18n.t('You do not have permission to send messages in this thread.')
					: $i18n.t('Reply to thread...')}
				typingUsersClassName="from-white dark:from-gray-900"
				{typingUsers}
				userSuggestions={true}
				channelSuggestions={true}
				{onChange}
				onSubmit={submitHandler}
			/>
		</div>
	</div>
{/if}
