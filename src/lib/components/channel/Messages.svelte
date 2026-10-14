<script lang="ts">
	import { toast } from 'svelte-sonner';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import isToday from 'dayjs/plugin/isToday';
	import isYesterday from 'dayjs/plugin/isYesterday';

	dayjs.extend(relativeTime);
	dayjs.extend(isToday);
	dayjs.extend(isYesterday);
	import { tick, getContext, onMount } from 'svelte';

	import { settings, socket, user } from '$lib/stores';

	import Message from './Messages/Message.svelte';
	import AppChannelReply from './AppChannelReply.svelte';
	import Loader from '../common/Loader.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Grid from '$lib/components/icons/Grid.svelte';
	import {
		addReaction,
		deleteMessage,
		pinMessage,
		removeReaction,
		updateMessage
	} from '$lib/apis/channels';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');

	export let id = null;
	export let channel = null;
	export let messages = [];
	export let replyToMessage = null;
	export let top = false;
	export let thread = false;

	export let onLoad: Function = () => {};
	export let onReply: Function = () => {};
	export let onThread: Function = () => {};
	export let onPin: Function = () => {};

	let messagesLoading = false;
	let appReplies: Record<string, any> = {};
	let replyLocation = '';
	$: if (replyLocation !== `${channel?.id}:${id}`) {
		replyLocation = `${channel?.id}:${id}`;
		appReplies = {};
	}

	const receiveAppChannelReply = (event) => {
		if (event.reply?.type === 'ack') return;
		if (event.channel_id !== channel?.id || (event.parent_id ?? null) !== (thread ? id : null))
			return;
		const key = `${event.message_id}:${event.app_id}`;
		appReplies = { ...appReplies, [key]: event };
	};

	onMount(() => {
		const appSocket = $socket;
		appSocket?.on('events:app', receiveAppChannelReply);
		return () => appSocket?.off('events:app', receiveAppChannelReply);
	});

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
			<div class="px-4 max-w-full mx-auto">
				{#if channel}
					<div class="flex flex-col gap-1.5 pb-4 pt-8">
						{#if channel?.type === 'dm'}
							<div class="flex ml-[0.0625rem] mr-0.5">
								{#each channel.users.filter((u) => u.id !== $user?.id).slice(0, 2) as u, index}
									<img
										src={`${WEBUI_API_BASE_URL}/users/${u.id}/profile/image`}
										alt={u.name}
										class=" size-7 rounded-full object-cover border-2 border-white dark:border-gray-900 {index ===
										1
											? '-ml-2.5'
											: ''}"
									/>
								{/each}
							</div>
						{/if}

						<div class="text-lg font-medium leading-6">
							{#if channel?.name}
								{channel.name}
							{:else}
								{channel?.users
									?.filter((u) => u.id !== $user?.id)
									.map((u) => u.name)
									.join(', ')}
							{/if}
						</div>

						<div class="text-xs leading-5 text-gray-500 dark:text-gray-400">
							{$i18n.t(
								'This channel was created on {{createdAt}}. This is the very beginning of the {{channelName}} channel.',
								{
									createdAt: dayjs(channel.created_at / 1000000)
										.locale($i18n.language)
										.format('MMMM D, YYYY'),
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
					<hr class=" border-gray-100/60 dark:border-gray-800/40 mb-2 w-full" />
				{/if}
			</div>
		{/if}

		{#each messageList as message, messageIdx (id ? `${id}-${message.id}` : message.id)}
			<Message
				on:reply={(event) =>
					receiveAppChannelReply({ ...event.detail, parent_id: thread ? id : null })}
				{message}
				{channel}
				{thread}
				{id}
				replyToMessage={replyToMessage?.id === message.id}
				disabled={!channel?.write_access || message?.temp_id}
				pending={!!message?.temp_id}
				showUserProfile={messageIdx === 0 ||
					Object.values(appReplies).some(
						(event) => event.message_id === messageList.at(messageIdx - 1)?.id
					) ||
					messageList.at(messageIdx - 1)?.user_id !== message.user_id ||
					messageList.at(messageIdx - 1)?.user?.id !== message.user?.id ||
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
					const pinned = !message.is_pinned;
					const pinnedBy = pinned ? ($user?.id ?? null) : null;
					const pinnedAt = pinned ? Date.now() * 1000000 : null;

					messages = messages.map((m) => {
						if (m.id === message.id) {
							m.is_pinned = pinned;
							m.pinned_by = pinnedBy;
							m.pinned_at = pinnedAt;
						}
						return m;
					});

					onPin(message.id, pinned, pinnedBy, pinnedAt);

					await pinMessage(localStorage.token, message.channel_id, message.id, pinned).catch(
						(error) => {
							toast.error(`${error}`);
							return null;
						}
					);
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
			{#each Object.entries(appReplies).filter(([, event]) => event.message_id === message.id) as [key, event] (key)}
				<div
					class="flex gap-3 px-4 pt-3 pb-2"
					data-app-reply={event.app_id}
					dir={$settings.chatDirection}
				>
					<span
						class="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-800"
						role="img"
						aria-label={$i18n.t('App')}><Grid className="size-4" /></span
					>
					<div class="min-w-0 flex-1">
						<div class="mb-0.5 flex items-baseline gap-1.5 leading-5">
							<span class="truncate text-[0.8125rem] font-medium text-gray-900 dark:text-gray-100"
								>{event.app_name ?? $i18n.t('App')}</span
							>
							<span class="text-[0.65rem] text-gray-500">{$i18n.t('App')}</span>
						</div>
						<div class="[&_.markdown-prose]:text-sm! [&_.markdown-prose]:leading-[1.375rem]!">
							{#key event.reply}
								<AppChannelReply appId={event.app_id} channelId={channel.id} reply={event.reply} />
							{/key}
						</div>
						<div class="mt-1.5 flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
							<span>{$i18n.t('Only visible to you')}</span>
							<span aria-hidden="true">·</span>
							<button
								type="button"
								class="focus-ring rounded hover:text-gray-800 hover:underline dark:hover:text-gray-200"
								on:click={() => {
									delete appReplies[key];
									appReplies = { ...appReplies };
								}}>{$i18n.t('Dismiss')}</button
							>
						</div>
					</div>
				</div>
			{/each}
		{/each}

		<div class="pb-4"></div>
	</div>
{/if}
