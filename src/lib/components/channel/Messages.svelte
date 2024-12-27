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

	import { settings } from '$lib/stores';

	import Message from './Messages/Message.svelte';
	import Loader from '../common/Loader.svelte';
	import Spinner from '../common/Spinner.svelte';
	import { deleteMessage, updateMessage } from '$lib/apis/channels';

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
			<div
				class="px-5
			
			{($settings?.widescreenMode ?? null) ? 'max-w-full' : 'max-w-5xl'} mx-auto"
			>
				{#if channel}
					<div class="flex flex-col gap-1.5 py-5">
						<div class="text-2xl font-medium capitalize">{channel.name}</div>

						<div class=" text-gray-500">
							This channel was created on {dayjs(channel.created_at / 1000000).format(
								'MMMM D, YYYY'
							)}. This is the very beginning of the {channel.name}
							channel.
						</div>
					</div>
				{:else}
					<div class="flex justify-center text-xs items-center gap-2 py-5">
						<div class=" ">Start of the channel</div>
					</div>
				{/if}

				{#if messageList.length > 0}
					<hr class=" border-gray-50 dark:border-gray-700/20 py-2.5 w-full" />
				{/if}
			</div>
		{/if}

		{#each messageList as message, messageIdx (message.id)}
			<Message
				{message}
				showUserProfile={messageIdx === 0 ||
					messageList.at(messageIdx - 1)?.user_id !== message.user_id}
				onDelete={() => {
					const res = deleteMessage(localStorage.token, message.channel_id, message.id).catch(
						(error) => {
							toast.error(error);
							return null;
						}
					);
				}}
				onEdit={(content) => {
					const res = updateMessage(localStorage.token, message.channel_id, message.id, {
						content: content
					}).catch((error) => {
						toast.error(error);
						return null;
					});
				}}
			/>
		{/each}

		<div class="pb-6" />
	</div>
{/if}
