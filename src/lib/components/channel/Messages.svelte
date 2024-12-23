<script lang="ts">
	import { v4 as uuidv4 } from 'uuid';
	import { chats, config, settings, user as _user, mobile, currentChatPage } from '$lib/stores';
	import { tick, getContext, onMount, createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import { toast } from 'svelte-sonner';

	import Message from './Messages/Message.svelte';
	import Loader from '../common/Loader.svelte';
	import Spinner from '../common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let messages = [];
	export let top = false;

	export let onLoad: Function = () => {};

	let messagesLoading = false;

	const loadMoreMessages = async () => {
		// scroll slightly down to disable continuous loading
		const element = document.getElementById('messages-container');
		element.scrollTop = element.scrollTop + 100;

		messagesLoading = true;

		await onLoad();

		await tick();
		messagesLoading = false;
	};
</script>

{#if messages}
	{@const messageList = messages.slice().reverse()}
	<div>
		{#if !top}
			<Loader
				on:visible={(e) => {
					console.log('visible');
					if (!messagesLoading) {
						loadMoreMessages();
					}
				}}
			>
				<div class="w-full flex justify-center py-1 text-xs animate-pulse items-center gap-2">
					<Spinner className=" size-4" />
					<div class=" ">Loading...</div>
				</div>
			</Loader>
		{/if}

		{#each messageList as message, messageIdx (message.id)}
			<Message
				{message}
				showUserProfile={messageIdx === 0 ||
					messageList.at(messageIdx + 1)?.user_id !== message.user_id}
			/>
		{/each}

		<div class="pb-6" />
	</div>
{/if}
