<script lang="ts">
	import { goto } from '$app/navigation';

	import { socket } from '$lib/stores';

	import { getChannelThreadMessages } from '$lib/apis/channels';

	import XMark from '$lib/components/icons/XMark.svelte';
	import MessageInput from './MessageInput.svelte';
	import Messages from './Messages.svelte';
	import { onMount } from 'svelte';

	export let threadId = null;
	export let channel = null;

	export let onClose = () => {};

	let messages = null;
	let top = false;

	let typingUsers = [];
	let typingUsersTimeout = {};

	$: if (threadId) {
		initHandler();
	}

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
		} else {
			goto('/');
		}
	};

	const submitHandler = async (message) => {
		// if (message) {
		// 	await sendMessage(localStorage.token, channel.id, message, threadId);
		// }
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
</script>

{#if channel}
	<div class="flex flex-col w-full h-full bg-gray-50 dark:bg-gray-850">
		<div class="flex items-center justify-between mb-2 px-3.5 py-3">
			<div class=" font-medium text-lg">Thread</div>

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

		<MessageInput {typingUsers} {onChange} onSubmit={submitHandler} />
	</div>
{/if}
