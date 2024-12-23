<script lang="ts">
	import { getChannelMessages, sendMessage } from '$lib/apis/channels';
	import { toast } from 'svelte-sonner';
	import MessageInput from './MessageInput.svelte';
	import Messages from './Messages.svelte';
	import { socket } from '$lib/stores';
	import { onDestroy, onMount, tick } from 'svelte';

	export let id = '';

	let scrollEnd = true;
	let messagesContainerElement = null;

	let top = false;
	let page = 1;

	let messages = null;

	$: if (id) {
		initHandler();
	}

	const scrollToBottom = () => {
		messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
	};

	const initHandler = async () => {
		top = false;
		page = 1;
		messages = null;

		messages = await getChannelMessages(localStorage.token, id, page);

		if (messages) {
			messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;

			if (messages.length < 50) {
				top = true;
			}
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
			}
		}
	};

	const submitHandler = async ({ content }) => {
		if (!content) {
			return;
		}

		const res = await sendMessage(localStorage.token, id, { content: content }).catch((error) => {
			toast.error(error);
			return null;
		});

		if (res) {
			messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
		}
	};

	onMount(() => {
		$socket?.on('channel-events', channelEventHandler);
	});

	onDestroy(() => {
		$socket?.off('channel-events', channelEventHandler);
	});
</script>

<div class="h-full md:max-w-[calc(100%-260px)] w-full max-w-full flex flex-col">
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
				{messages}
				{top}
				onLoad={async () => {
					page += 1;

					const newMessages = await getChannelMessages(localStorage.token, id, page);

					if (newMessages.length === 0) {
						top = true;
						return;
					}

					messages = [...messages, ...newMessages];
				}}
			/>
		{/key}
	</div>

	<div class=" pb-[1rem]">
		<MessageInput onSubmit={submitHandler} {scrollToBottom} {scrollEnd} />
	</div>
</div>
