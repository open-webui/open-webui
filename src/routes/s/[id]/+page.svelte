<script lang="ts">
	import { onMount, tick, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import dayjs from 'dayjs';
	import localizedFormat from 'dayjs/plugin/localizedFormat';

	import { settings, chatId, WEBUI_NAME, models, config, user as sessionUser } from '$lib/stores';
	import { convertMessagesToHistory, createMessagesList } from '$lib/utils';

	import { getChatByShareId, cloneSharedChatById, forkChatById } from '$lib/apis/chats';

	import Messages from '$lib/components/chat/Messages.svelte';

	import { getUserInfoById, getUserSettings } from '$lib/apis/users';
	import { getModels } from '$lib/apis';
	import { toast } from 'svelte-sonner';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	dayjs.extend(localizedFormat);

	let loaded = false;
	let forking = false;

	let autoScroll = true;
	let processing = '';
	let messagesComponent;

	// let chatId = $page.params.id;
	let showModelSelector = false;
	let selectedModels = [''];

	let chat = null;
	let user = null;

	let title = '';
	let files = [];

	let messages = [];
	let history = {
		messages: {},
		currentId: null
	};

	$: messages = createMessagesList(history, history.currentId);
	$: canClone =
		$sessionUser &&
		($sessionUser.role === 'admin' || ($sessionUser.permissions?.chat?.import ?? true));

	$: if ($page.params.id) {
		(async () => {
			if (await loadSharedChat()) {
				loaded = true;
				await tick();
				messagesComponent?.scrollToBottom();
			} else if (localStorage.token) {
				await goto('/');
			} else {
				await goto(`/auth?redirect=${encodeURIComponent($page.url.pathname)}`);
			}
		})();
	}

	//////////////////////////
	// Web functions
	//////////////////////////

	const loadSharedChat = async () => {
		const token = localStorage.token ?? '';
		const shareId = $page.params.id;
		if (!shareId) return null;

		const userSettings = token
			? await getUserSettings(token).catch((error) => {
					console.error(error);
					return null;
				})
			: null;

		if (userSettings) {
			settings.set(userSettings.ui);
		} else {
			let localStorageSettings = {} as Parameters<(typeof settings)['set']>[0];

			try {
				localStorageSettings = JSON.parse(localStorage.getItem('settings') ?? '{}');
			} catch (e: unknown) {
				console.error('Failed to parse settings from localStorage', e);
			}

			settings.set(localStorageSettings);
		}

		await models.set(
			token
				? await getModels(
						token,
						$config?.features?.enable_direct_connections
							? ($settings?.directConnections ?? null)
							: null
					).catch((error) => {
						console.error(error);
						return [];
					})
				: []
		);
		await chatId.set(shareId);
		chat = await getChatByShareId(token, shareId).catch(() => null);

		if (chat?.chat?.share_mode === 'continue' && chat.id !== shareId) {
			await goto(`/c/${chat.id}`, { replaceState: true });
			return true;
		}

		if (chat) {
			user = token
				? await getUserInfoById(token, chat.user_id).catch((error) => {
						console.error(error);
						return null;
					})
				: null;

			const chatContent = chat.chat;

			if (chatContent) {
				console.log(chatContent);

				selectedModels =
					(chatContent?.models ?? undefined) !== undefined
						? chatContent.models
						: [chatContent.models ?? ''];
				history =
					(chatContent?.history ?? undefined) !== undefined
						? chatContent.history
						: convertMessagesToHistory(chatContent.messages);
				title = chatContent.title;

				autoScroll = true;
				await tick();

				if (messages.length > 0 && messages.at(-1)?.id && messages.at(-1)?.id in history.messages) {
					history.messages[messages.at(-1)?.id].done = true;
				}
				await tick();

				return true;
			} else {
				return null;
			}
		}
	};

	const forkSharedChat = async (messageId: string | null = null) => {
		const shareId = $page.params.id;
		if (!canClone || !shareId || forking) return;
		forking = true;
		const toastId = toast.loading($i18n.t('Forking chat...'));
		try {
			const result = await forkChatById(
				localStorage.token,
				shareId,
				messageId ?? history.currentId
			);
			if (result?.id) {
				await goto(`/c/${result.id}`);
				toast.success($i18n.t('Chat forked'), { id: toastId });
			} else {
				toast.error($i18n.t('Failed to fork chat'), { id: toastId });
			}
		} catch (error) {
			toast.error(`${error}`, { id: toastId });
		} finally {
			forking = false;
		}
	};

	const cloneSharedChat = async () => {
		if (!canClone) {
			toast.error($i18n.t('Access prohibited'));
			return;
		}

		if (!chat) return;

		const res = await cloneSharedChatById(localStorage.token, chat.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			goto(`/c/${res.id}`);
		}
	};
</script>

<svelte:head>
	<!-- LICENSE covers this Open WebUI browser-title identifier.
	Do not alter, remove, obscure, or replace it except as LICENSE permits:
	https://docs.openwebui.com/license. -->
	<title>
		{title
			? `${title.length > 30 ? `${title.slice(0, 30)}...` : title} / ${$WEBUI_NAME}`
			: `${$WEBUI_NAME}`}
	</title>
	<meta name="robots" content="noindex,nofollow" />
</svelte:head>

{#if loaded}
	<div
		class="h-screen max-h-[100dvh] w-full flex flex-col text-gray-700 dark:text-gray-100 bg-white dark:bg-gray-900"
	>
		<div class="flex flex-col flex-auto justify-center relative">
			<div
				class="@container flex flex-col w-full flex-auto overflow-auto h-0"
				id="messages-container"
			>
				<header
					class="sticky top-0 z-30 mx-auto w-full max-w-[58rem] shrink-0 bg-white px-2 dark:bg-gray-900"
				>
					<div
						class="pointer-events-none absolute inset-x-0 top-full h-10 z-[-1] bg-linear-to-b from-white to-transparent dark:from-gray-900"
					></div>
					<div class="flex items-center gap-3 px-3 py-2">
						<h1
							class="min-w-0 truncate text-[0.9375rem] font-normal text-gray-700 dark:text-gray-300"
							{title}
						>
							{title}
						</h1>
						<time
							class="ms-auto shrink-0 whitespace-nowrap text-xs text-gray-400 dark:text-gray-500"
							datetime={dayjs(chat.chat.timestamp || chat.created_at * 1000)
								.locale($i18n.language)
								.toISOString()}
						>
							{dayjs(chat.chat.timestamp || chat.created_at * 1000)
								.locale($i18n.language)
								.format('LLL')}
						</time>
					</div>
				</header>

				<div class=" h-full w-full flex flex-col py-2" role="main">
					<div class="w-full">
						<Messages
							bind:this={messagesComponent}
							className="h-full flex pb-8"
							{user}
							chatId={$chatId}
							readOnly={true}
							forkHandler={canClone ? forkSharedChat : null}
							{selectedModels}
							{processing}
							bind:history
							bind:messages
							bind:autoScroll
							bottomPadding={files.length > 0}
							sendMessage={() => {}}
							continueResponse={() => {}}
							regenerateResponse={() => {}}
						/>
					</div>
				</div>
			</div>

			{#if canClone}
				<div
					class="pointer-events-none absolute inset-x-0 bottom-0 z-10 flex justify-center gap-2 bg-linear-to-t from-white dark:from-gray-900 to-transparent pb-5 pt-10"
				>
					<button
						class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs font-normal text-white transition hover:bg-black disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white pointer-events-auto"
						on:click={cloneSharedChat}
					>
						{$i18n.t('Clone Chat')}
					</button>
				</div>
			{/if}
		</div>
	</div>
{/if}
