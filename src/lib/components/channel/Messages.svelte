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

	export let channelId;

	let messages = null;

	let messagesCount = 50;
	let messagesLoading = false;

	const loadMoreMessages = async () => {
		// scroll slightly down to disable continuous loading
		const element = document.getElementById('messages-container');
		element.scrollTop = element.scrollTop + 100;

		messagesLoading = true;
		messagesCount += 50;

		await tick();

		messagesLoading = false;
	};
</script>

<div class="h-full flex pt-8">
	<div class="w-full pt-2">
		{#key channelId}
			<div class="w-full">
				{#if messages.at(0)?.parentId !== null}
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

				{#each messages as message, messageIdx (message.id)}
					<Message {channelId} id={message.id} content={message.content} />
				{/each}
			</div>
			<div class="pb-12" />
		{/key}
	</div>
</div>
