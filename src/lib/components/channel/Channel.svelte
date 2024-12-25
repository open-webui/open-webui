<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onDestroy, onMount, tick } from 'svelte';

	import { chatId, showSidebar, socket } from '$lib/stores';
	import { getChannelById, getChannelMessages, sendMessage } from '$lib/apis/channels';

	import Messages from './Messages.svelte';
	import MessageInput from './MessageInput.svelte';
	import { goto } from '$app/navigation';
	import Navbar from './Navbar.svelte';

	export let id = '';

	let scrollEnd = true;
	let messagesContainerElement = null;

	let top = false;

	let channel = null;
	let messages = null;

	$: if (id) {
		initHandler();
	}

	const scrollToBottom = () => {
		messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
	};

	const initHandler = async () => {
		top = false;
		messages = null;
		channel = null;

		channel = await getChannelById(localStorage.token, id).catch((error) => {
			return null;
		});

		if (channel) {
			messages = await getChannelMessages(localStorage.token, id, 0);

			if (messages) {
				messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;

				if (messages.length < 50) {
					top = true;
				}
			}
		} else {
			goto('/');
		}
	};

	const channelEventHandler = async (event) => {
		console.log(event);

		if (event.channel_id === id) {
			const type = event?.data?.type ?? null;
			const data = event?.data?.data ?? null;

			if (type === 'message') {
				console.log('message', data);
				messages = [data, ...messages];
				await tick();
				if (scrollEnd) {
					messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
				}
			} else if (type === 'message:update') {
				console.log('message:update', data);
				const idx = messages.findIndex((message) => message.id === data.id);

				if (idx !== -1) {
					messages[idx] = data;
				}
			} else if (type === 'message:delete') {
				console.log('message:delete', data);
				messages = messages.filter((message) => message.id !== data.id);
			}
		}
	};

	const submitHandler = async ({ content, data }) => {
		if (!content) {
			return;
		}

		const res = await sendMessage(localStorage.token, id, { content: content, data: data }).catch(
			(error) => {
				toast.error(error);
				return null;
			}
		);

		if (res) {
			messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
		}
	};

	onMount(() => {
		if ($chatId) {
			chatId.set('');
		}

		$socket?.on('channel-events', channelEventHandler);
	});

	onDestroy(() => {
		// $socket?.off('channel-events', channelEventHandler);
	});
</script>

<div
	class="h-screen max-h-[100dvh] {$showSidebar
		? 'md:max-w-[calc(100%-260px)]'
		: ''} w-full max-w-full flex flex-col"
	id="channel-container"
>
	<Navbar {channel} />

	<div class="flex-1 overflow-y-auto">
		{#if channel}
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
						{messages}
						{top}
						onLoad={async () => {
							const newMessages = await getChannelMessages(localStorage.token, id, messages.length);

							messages = [...messages, ...newMessages];

							if (newMessages.length < 50) {
								top = true;
								return;
							}
						}}
					/>
				{/key}
			</div>
		{/if}
	</div>

	<div class=" pb-[1rem]">
		<MessageInput onSubmit={submitHandler} {scrollToBottom} {scrollEnd} />
	</div>
</div>
