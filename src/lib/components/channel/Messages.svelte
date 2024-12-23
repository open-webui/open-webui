<script lang="ts">
	import { toast } from 'svelte-sonner';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import isToday from 'dayjs/plugin/isToday';
	import isYesterday from 'dayjs/plugin/isYesterday';

	dayjs.extend(relativeTime);
	dayjs.extend(isToday);
	dayjs.extend(isYesterday);
	import { tick, getContext, onMount, createEventDispatcher } from 'svelte';

	import Message from './Messages/Message.svelte';
	import Loader from '../common/Loader.svelte';
	import Spinner from '../common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let channel = null;
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
		{:else}
			<div class="px-5">
				{#if channel}
					<div class="flex flex-col py-1 gap-1.5">
						<div class="text-xl font-medium">{channel.name}</div>

						<div class="text-sm text-gray-500">
							This channel was created on {dayjs(channel.created_at / 1000000).format(
								'MMMM D, YYYY'
							)}. This is the very beginning of the {channel.name}
							channel.
						</div>
					</div>
				{:else}
					<div class="flex justify-center py-1 text-xs items-center gap-2">
						<div class=" ">Start of the channel</div>
					</div>
				{/if}
			</div>
		{/if}

		{#each messageList as message, messageIdx (message.id)}
			<Message
				{message}
				showUserProfile={messageIdx === 0 ||
					messageList.at(messageIdx - 1)?.user_id !== message.user_id}
			/>
		{/each}

		<div class="pb-6" />
	</div>
{/if}
