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

	let messages = null;
	let top = false;

	let typingUsers = [];
	let typingUsersTimeout = {};

	let messagesContainerElement = null;

	$: if (threadId) {
		initHandler();
	}

	const scrollToBottom = () => {
		messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
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
						messages = [data, ...messages];

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
				if (messages) {
					messages = messages.filter((message) => message.id !== data.id);
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

	const submitHandler = async ({ content, data }) => {
		if (!content && (data?.files ?? []).length === 0) {
			return;
		}

		const res = await sendMessage(localStorage.token, channel.id, {
			parent_id: threadId,
			content: content,
			data: data
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
	};

	const onChange = async () => {
		$socket?.emit('channel-events', {
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
		$socket?.on('channel-events', channelEventHandler);
	});

	onDestroy(() => {
		$socket?.off('channel-events', channelEventHandler);
	});
</script>

{#if channel}
	<div class="flex flex-col w-full h-full bg-gray-50 dark:bg-gray-850">
		<div class="sticky top-0 flex items-center justify-between px-3.5 py-3">
			<div class=" font-medium text-lg">{$i18n.t('Thread')}</div>

			<div>
				<button
					class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 p-2"
					on:click={() => {
						onClose();
					}}
				>
					<XMark />
				</button>
			</div>
		</div>

		<div class=" max-h-full w-full overflow-y-auto" bind:this={messagesContainerElement}>
			{#if messages !== null}
				<Messages
					id={threadId}
					{channel}
					{messages}
					{top}
					thread={true}
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

			<div class=" pb-[1rem] px-2.5 w-full">
				<MessageInput
					id={threadId}
					disabled={!channel?.write_access}
					placeholder={!channel?.write_access
						? $i18n.t('You do not have permission to send messages in this thread.')
						: $i18n.t('Reply to thread...')}
					typingUsersClassName="from-gray-50 dark:from-gray-850"
					{typingUsers}
					userSuggestions={true}
					channelSuggestions={true}
					{onChange}
					onSubmit={submitHandler}
				/>
			</div>
		</div>
	</div>
{/if}
