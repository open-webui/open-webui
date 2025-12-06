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

	import { settings, user } from '$lib/stores';

	import Message from './Messages/Message.svelte';
	import Loader from '../common/Loader.svelte';
	import Spinner from '../common/Spinner.svelte';
	import {
		addReaction,
		deleteMessage,
		pinMessage,
		removeReaction,
		updateMessage
	} from '$lib/apis/channels';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');

	export let id = null;
	export let channel = null;
	export let messages = [];
	export let replyToMessage = null;
	export let top = false;
	export let thread = false;

	export let onLoad: Function = () => {};
	export let onReply: Function = () => {};
	export let onThread: Function = () => {};

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
					console.info('visible');
					if (!messagesLoading) {
						loadMoreMessages();
					}
				}}
			>
				<div class="w-full flex justify-center py-1 text-xs animate-pulse items-center gap-2">
					<Spinner className=" size-4" />
					<div class=" ">{$i18n.t('Loading...')}</div>
				</div>
			</Loader>
		{:else if !thread}
			<div class="px-5 max-w-full mx-auto">
				{#if channel}
					<div class="flex flex-col gap-1.5 pb-5 pt-10">
						{#if channel?.type === 'dm'}
							<div class="flex ml-[1px] mr-0.5">
								{#each channel.users.filter((u) => u.id !== $user?.id).slice(0, 2) as u, index}
									<img
										src={`${WEBUI_API_BASE_URL}/users/${u.id}/profile/image`}
										alt={u.name}
										class=" size-7.5 rounded-full border-2 border-white dark:border-gray-900 {index ===
										1
											? '-ml-2.5'
											: ''}"
									/>
								{/each}
							</div>
						{/if}

						<div class="text-2xl font-medium capitalize">
							{#if channel?.name}
								{channel.name}
							{:else}
								{channel?.users
									?.filter((u) => u.id !== $user?.id)
									.map((u) => u.name)
									.join(', ')}
							{/if}
						</div>

						<div class=" text-gray-500">
							{$i18n.t(
								'This channel was created on {{createdAt}}. This is the very beginning of the {{channelName}} channel.',
								{
									createdAt: dayjs(channel.created_at / 1000000).format('MMMM D, YYYY'),
									channelName: channel.name
								}
							)}
						</div>
					</div>
				{:else}
					<div class="flex justify-center text-xs items-center gap-2 py-5">
						<div class=" ">{$i18n.t('Start of the channel')}</div>
					</div>
				{/if}

				{#if messageList.length > 0}
					<hr class=" border-gray-50 dark:border-gray-700/20 py-2.5 w-full" />
				{/if}
			</div>
		{/if}

		{#each messageList as message, messageIdx (id ? `${id}-${message.id}` : message.id)}
			<Message
				{message}
				{channel}
				{thread}
				replyToMessage={replyToMessage?.id === message.id}
				disabled={!channel?.write_access || message?.temp_id}
				pending={!!message?.temp_id}
				showUserProfile={messageIdx === 0 ||
					messageList.at(messageIdx - 1)?.user_id !== message.user_id ||
					messageList.at(messageIdx - 1)?.meta?.model_id !== message?.meta?.model_id ||
					message?.reply_to_message !== null}
				onDelete={() => {
					messages = messages.filter((m) => m.id !== message.id);

					const res = deleteMessage(localStorage.token, message.channel_id, message.id).catch(
						(error) => {
							toast.error(`${error}`);
							return null;
						}
					);
				}}
				onEdit={(content) => {
					messages = messages.map((m) => {
						if (m.id === message.id) {
							m.content = content;
						}
						return m;
					});

					const res = updateMessage(localStorage.token, message.channel_id, message.id, {
						content: content
					}).catch((error) => {
						toast.error(`${error}`);
						return null;
					});
				}}
				onReply={(message) => {
					onReply(message);
				}}
				onPin={async (message) => {
					messages = messages.map((m) => {
						if (m.id === message.id) {
							m.is_pinned = !m.is_pinned;
							m.pinned_by = !m.is_pinned ? null : $user?.id;
							m.pinned_at = !m.is_pinned ? null : Date.now() * 1000000;
						}
						return m;
					});

					const updatedMessage = await pinMessage(
						localStorage.token,
						message.channel_id,
						message.id,
						message.is_pinned
					).catch((error) => {
						toast.error(`${error}`);
						return null;
					});
				}}
				onThread={(id) => {
					onThread(id);
				}}
				onReaction={(name) => {
					if (
						(message?.reactions ?? [])
							.find((reaction) => reaction.name === name)
							?.users?.some((u) => u.id === $user?.id) ??
						false
					) {
						messages = messages.map((m) => {
							if (m.id === message.id) {
								const reaction = m.reactions.find((reaction) => reaction.name === name);

								if (reaction) {
									reaction.users = reaction.users.filter((u) => u.id !== $user?.id);
									reaction.count = reaction.users.length;

									if (reaction.count === 0) {
										m.reactions = m.reactions.filter((r) => r.name !== name);
									}
								}
							}
							return m;
						});

						const res = removeReaction(
							localStorage.token,
							message.channel_id,
							message.id,
							name
						).catch((error) => {
							toast.error(`${error}`);
							return null;
						});
					} else {
						messages = messages.map((m) => {
							if (m.id === message.id) {
								if (m.reactions) {
									const reaction = m.reactions.find((reaction) => reaction.name === name);

									if (reaction) {
										reaction.users.push({ id: $user?.id, name: $user?.name });
										reaction.count = reaction.users.length;
									} else {
										m.reactions.push({
											name: name,
											users: [{ id: $user?.id, name: $user?.name }],
											count: 1
										});
									}
								}
							}
							return m;
						});

						const res = addReaction(localStorage.token, message.channel_id, message.id, name).catch(
							(error) => {
								toast.error(`${error}`);
								return null;
							}
						);
					}
				}}
			/>
		{/each}

		<div class="pb-6" />
	</div>
{/if}
