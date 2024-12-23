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

	const initHandler = async () => {
		top = false;
		page = 1;
		messages = null;

		messages = await getChannelMessages(localStorage.token, id, page);

		if (messages.length < 50) {
			top = true;
		}
	};

	const channelEventHandler = async (data) => {
		console.log(data);
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
		class=" pb-2.5 flex flex-col justify-between w-full flex-auto overflow-auto h-0 max-w-full z-10 scrollbar-hidden"
		id="messages-container"
		bind:this={messagesContainerElement}
		on:scroll={(e) => {
			scrollEnd =
				messagesContainerElement.scrollHeight - messagesContainerElement.scrollTop <=
				messagesContainerElement.clientHeight + 5;
		}}
	>
		{#key id}
			<Messages
				{messages}
				onLoad={async () => {
					page += 1;

					const newMessages = await getChannelMessages(localStorage.token, id, page);

					if (newMessages.length === 0) {
						top = true;
						return;
					}

					messages = [...newMessages, ...messages];
				}}
			/>
		{/key}
	</div>

	<div class=" pb-[1rem]">
		<MessageInput onSubmit={submitHandler} />
	</div>
</div>
