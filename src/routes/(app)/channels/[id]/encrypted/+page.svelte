<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';
	import { beforeNavigate, goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { get } from 'svelte/store';
	import { socket, user, config, showSidebar, channels, settings, mobile } from '$lib/stores';
	import { canUseEncryption, consumeEntry, Conversation, type State } from '$lib/encryption/client';

	import Navbar from '$lib/components/channel/Navbar.svelte';
	import Message from '$lib/components/channel/Messages/Message.svelte';
	import RichTextInput from '$lib/components/common/RichTextInput.svelte';
	import type { Editor } from '@tiptap/core';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import Skeleton from '$lib/components/chat/Messages/Skeleton.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ProfileImage from '$lib/components/chat/Messages/ProfileImage.svelte';
	import UserAlt from '$lib/components/icons/UserAlt.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	const i18n: any = getContext('i18n');
	$: channel = $page.params.id ?? '';
	let mounted = false;
	let stopSession = () => {};
	// SvelteKit reuses the page when navigating between channel IDs.
	$: if (mounted) startSession(channel);
	let showParticipants = false;
	$: channelInfo = $channels.find((item) => item.id === channel) ?? {
		id: channel,
		name: $i18n.t('Conversation'),
		type: 'group',
		is_private: true
	};
	let conversation: Conversation | undefined;
	let state: State = { status: 'ended', messages: [], members: [], typing: [], self: '', host: '' };
	$: typingMembers = state.members.filter((member) =>
		state.typing.includes(member.identity.participation)
	);
	let draft = '';
	let inputEditor: Editor | null = null;
	let verified = new Set<string>();
	let list: HTMLDivElement;
	$: oversized = new TextEncoder().encode(draft).length > 16384;
	const close = () => {
		inputEditor?.destroy();
		inputEditor = null;
		draft = '';
		showParticipants = false;
		verified = new Set();
		conversation?.close();
	};
	const leave = () => {
		close();
		void goto(`/channels/${encodeURIComponent(channel)}`);
	};
	beforeNavigate(close);
	onMount(() => {
		mounted = true;
		return () => stopSession();
	});
	function startSession(channel: string) {
		stopSession();
		state = { status: 'ended', messages: [], members: [], typing: [], self: '', host: '' };
		const intent = consumeEntry(channel);
		const connection = get(socket);
		const account = get(user);
		if (!intent || !connection || !account || !canUseEncryption(account, get(config)?.features))
			return;
		try {
			conversation = new Conversation(connection, channel, account.id, intent);
		} catch {
			close();
			return;
		}
		const unsubscribe = conversation.state.subscribe((next) => {
			const messagesChanged = state.messages !== next.messages;
			state = next;
			if (next.status === 'ended') {
				showParticipants = false;
				draft = '';
				verified = new Set();
			}
			if (messagesChanged)
				void tick().then(() => {
					if (list) list.scrollTop = list.scrollHeight;
				});
		});
		const logout = user.subscribe((current) => {
			if (current?.id !== account.id || !canUseEncryption(current, get(config)?.features)) close();
		});
		const settingsChanged = config.subscribe((current) => {
			if (!canUseEncryption(get(user), current?.features)) close();
		});
		stopSession = () => {
			close();
			unsubscribe();
			logout();
			settingsChanged();
			conversation = undefined;
		};
	}
	function send() {
		if (oversized || !draft.trim() || state.status !== 'active') return;
		const text = draft;
		inputEditor?.commands.clearContent();
		draft = '';
		void conversation?.sendText(text);
	}
</script>

<svelte:head><title>{$i18n.t('Encrypted chat')} · Open WebUI</title></svelte:head>
<div
	class="h-screen max-h-[100dvh] w-full min-w-0 flex flex-col {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''}"
>
	<Navbar channel={channelInfo} readOnly>
		<span slot="status" class="ml-2 shrink-0 text-[0.6875rem] text-gray-500 dark:text-gray-400"
			>{$i18n.t('Encrypted')}</span
		>
		<svelte:fragment slot="actions">
			{#if state.status !== 'ended'}
				<Tooltip content={$i18n.t('Participants')}>
					<button
						type="button"
						aria-label={$i18n.t('{{COUNT}} participants', { COUNT: state.members.length })}
						class="flex h-7 items-center gap-1 px-1.5 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-50/60 dark:hover:bg-gray-800/60 transition-colors"
						on:click={() => (showParticipants = true)}
					>
						<UserAlt className="size-4" strokeWidth="1.5" />
						<span class="text-xs tabular-nums">{state.members.length}</span>
					</button>
				</Tooltip>
			{/if}
			<button
				type="button"
				class="h-7 rounded-lg px-2 text-xs text-gray-500 hover:bg-gray-50/60 dark:text-gray-400 dark:hover:bg-gray-800/60"
				on:click={leave}>{$i18n.t('Leave')}</button
			>
		</svelte:fragment>
	</Navbar>
	{#if state.status === 'ended'}
		<div
			class="flex flex-1 flex-col items-center justify-center gap-2 px-4 text-center"
			role="status"
		>
			<h2 class="text-xs font-normal text-gray-500 dark:text-gray-400">
				{$i18n.t('Encrypted chat ended')}
			</h2>
			<button
				type="button"
				class="h-7 rounded-lg bg-gray-100 px-2.5 text-xs font-normal text-gray-800 transition hover:bg-gray-100/70 dark:bg-gray-850 dark:text-white dark:hover:bg-gray-850/60"
				on:click={leave}>{$i18n.t('Return to conversation')}</button
			>
		</div>
	{:else}
		<div
			bind:this={list}
			class="flex-1 min-h-0 overflow-y-auto pt-14 pb-2.5"
			role="log"
			aria-label={$i18n.t('Encrypted messages')}
			aria-live="polite"
		>
			<div class="min-h-full flex flex-col justify-end">
				{#if state.messages.length === 0}
					<div class="px-4 py-6 text-sm text-gray-500 dark:text-gray-400">
						<p>
							{state.status === 'joining'
								? $i18n.t('Joining encrypted chat…')
								: $i18n.t('Messages are end-to-end encrypted and aren’t saved.')}
						</p>
						<p class="mt-1 text-xs">{$i18n.t('Leaving or reloading clears this device’s chat.')}</p>
					</div>
				{/if}
				{#each state.messages as message, messageIdx (message.id)}
					{#if message.type === 'joined'}
						<p class="px-4 py-1 text-[0.6875rem] font-normal text-gray-500 dark:text-gray-400">
							{$i18n.t('{{NAME}} joined', { NAME: message.user.name })}
						</p>
					{:else}
						<Message
							channel={channelInfo}
							disabled
							showUserProfile={messageIdx === 0 ||
								state.messages[messageIdx - 1].type === 'joined' ||
								state.messages[messageIdx - 1].sender !== message.sender}
							message={{
								id: message.id,
								content: message.text,
								user: message.user,
								created_at: message.created_at,
								updated_at: message.created_at
							}}
						>
							<div slot="content" class="markdown-prose">
								<Markdown
									id={message.id}
									content={message.text}
									allowHtml={false}
									allowEmbeds={false}
									allowRemoteContent={false}
									editCodeBlock={false}
								/>
							</div>
							<svelte:fragment slot="status">
								{#if message.sender === state.self}
									{#if message.expected.length > 0 && message.received.length === message.expected.length}
										<span
											class="hover-reveal shrink-0 translate-y-px text-[0.6875rem] leading-4 font-normal text-gray-500 dark:text-gray-400"
										>
											{$i18n.t('Delivered')}
										</span>
									{:else if !message.relayed}
										<span
											class="shrink-0 translate-y-px text-[0.6875rem] leading-4 font-normal text-gray-500 dark:text-gray-400"
										>
											{$i18n.t('Sending…')}
										</span>
									{/if}
								{/if}
							</svelte:fragment>
						</Message>
					{/if}
				{/each}
			</div>
		</div>
		<form
			class="shrink-0 pb-3 px-3"
			on:submit|preventDefault={send}
			on:focusout={() => conversation?.sendTyping(false)}
		>
			{#if typingMembers.length > 0}
				<div
					class="flex items-center gap-1.5 px-1 pb-2 text-xs text-gray-500 dark:text-gray-400"
					role="status"
				>
					<Skeleton size="xs" />
					<div>
						<span class="font-normal text-black dark:text-white"
							>{typingMembers.map((member) => member.name).join(', ')}</span
						>
						{typingMembers.length === 1 ? $i18n.t('is typing...') : $i18n.t('are typing...')}
					</div>
				</div>
			{/if}
			<div
				id="message-input-container"
				class="flex-1 flex flex-col relative w-full shadow-sm rounded-2xl border border-gray-100/60 dark:border-gray-800/50 hover:border-gray-100 focus-within:border-gray-100 hover:dark:border-gray-800 focus-within:dark:border-gray-800 transition bg-white dark:bg-gray-400/5 dark:text-gray-100"
				dir={$settings?.chatDirection === 'RTL'
					? 'rtl'
					: $settings?.chatDirection === 'LTR'
						? 'ltr'
						: 'auto'}
			>
				<div class="px-2" spellcheck="false">
					<div
						class="scrollbar-hidden rtl:text-right ltr:text-left bg-transparent dark:text-gray-100 outline-hidden w-full pt-2 pb-0.5 px-1 resize-none h-fit max-h-96 overflow-auto"
					>
						<RichTextInput
							id="chat-input"
							className="input-prose min-h-fit h-full text-sm!"
							bind:editor={inputEditor}
							json={true}
							messageInput={true}
							editable={state.status === 'active'}
							placeholder={$i18n.t('Type here...')}
							richText={$settings?.richTextInput ?? true}
							showFormattingToolbar={$settings?.showFormattingToolbar ?? false}
							shiftEnter={!($settings?.ctrlEnterToSend ?? false) && !$mobile}
							floatingMenuPlacement="top-start"
							onChange={({ md }) => {
								draft = state.status === 'active' ? md : '';
								void conversation?.sendTyping(Boolean(draft.trim()));
							}}
							on:keydown={({ detail: { event } }) => {
								if (event.isComposing || event.defaultPrevented || event.key !== 'Enter') return;
								const control = event.ctrlKey || event.metaKey;
								if (
									($settings?.ctrlEnterToSend ?? false)
										? control
										: !event.shiftKey && (!$mobile || control)
								) {
									event.preventDefault();
									send();
								}
							}}
						/>
					</div>
				</div>
				<div class="flex items-center justify-end gap-2 px-2 pb-2 pt-1">
					{#if oversized}<span class="mr-auto text-xs text-gray-500" role="status"
							>{$i18n.t('Message exceeds the 16 KiB limit.')}</span
						>{/if}
					<Tooltip content={$i18n.t('Send message')}>
						<button
							id="send-message-button"
							aria-label={$i18n.t('Send message')}
							class="{!(state.status !== 'active' || oversized || !draft.trim())
								? 'bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 '
								: 'text-white bg-gray-200 dark:text-gray-900 dark:bg-gray-700 disabled'} transition rounded-full size-7 flex items-center justify-center self-center"
							type="submit"
							disabled={state.status !== 'active' || oversized || !draft.trim()}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								class="size-4"
							>
								<path
									fill-rule="evenodd"
									d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z"
									clip-rule="evenodd"
								/>
							</svg>
						</button>
					</Tooltip>
				</div>
			</div>
		</form>
	{/if}
</div>

<Modal bind:show={showParticipants} size="sm" ariaLabel={$i18n.t('Participants')}>
	<div class="flex items-center justify-between px-4 pt-3 mb-1 dark:text-gray-100">
		<h2 class="text-base font-normal">{$i18n.t('Participants')}</h2>
		<button
			type="button"
			aria-label={$i18n.t('Close')}
			class="self-center rounded-lg p-1 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
			on:click={() => (showParticipants = false)}><XMark className="size-4" /></button
		>
	</div>
	<div class="max-h-[50dvh] overflow-y-auto px-3 pb-4 dark:text-gray-200">
		{#each state.members as member (member.identity.participation)}
			<details class="group text-xs">
				<summary
					class="flex cursor-pointer list-none items-center gap-2 px-2 py-1.5 font-normal text-gray-900 dark:text-white [&::-webkit-details-marker]:hidden"
				>
					<ProfileImage
						src={`${WEBUI_API_BASE_URL}/users/${member.identity.user}/profile/image`}
						className="size-6 shrink-0 rounded-2xl"
					/>
					<span class="min-w-0 flex-1 truncate text-xs font-normal" title={member.name}
						>{member.name}</span
					>
					<span class="shrink-0 text-xs font-normal text-gray-500 dark:text-gray-400"
						>{verified.has(member.fingerprint) ? $i18n.t('Verified') : $i18n.t('Verify')}</span
					>
					<ChevronRight
						className="size-3 shrink-0 text-gray-400 transition-transform group-open:rotate-90"
					/>
				</summary>
				<div class="mx-2 mb-2 rounded-lg bg-gray-50/60 p-2.5 dark:bg-gray-850/60">
					<p class="text-[0.6875rem] leading-4 text-gray-500 dark:text-gray-400">
						{$i18n.t(
							'Compare this code with this participant through another trusted channel. It changes when they rejoin.'
						)}
					</p>
					<code
						class="my-2 block break-all text-[0.6875rem] leading-4 text-gray-700 dark:text-gray-300"
						>{member.fingerprint.match(/.{1,4}/g)?.join(' ')}</code
					>
					{#if member.identity.participation !== state.self}
						<button
							type="button"
							class="h-7 rounded-lg bg-gray-100 px-2.5 text-xs font-normal text-gray-800 transition hover:bg-gray-100/70 dark:bg-gray-850 dark:text-white dark:hover:bg-gray-850/60"
							on:click={() => (verified = new Set([...verified, member.fingerprint]))}
							>{$i18n.t('Codes match')}</button
						>
					{/if}
				</div>
			</details>
		{/each}
		<div class="flex justify-end px-2 pt-2">
			<button
				type="button"
				class="h-7 rounded-lg bg-gray-100 px-2.5 text-xs font-normal text-gray-800 transition hover:bg-gray-100/70 disabled:opacity-60 dark:bg-gray-850 dark:text-white dark:hover:bg-gray-850/60"
				disabled={state.status !== 'active'}
				on:click={() => conversation?.updateKeys()}>{$i18n.t('Refresh encryption keys')}</button
			>
		</div>
	</div>
</Modal>
