<script lang="ts">
	import { onMount, tick, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import dayjs from 'dayjs';

	import { settings, chatId, WEBUI_NAME, models } from '$lib/stores';
	import { convertMessagesToHistory, createMessagesList } from '$lib/utils';

	import { getChatByShareId, cloneChatByShareId } from '$lib/apis/chats';

	import Messages from '$lib/components/chat/Messages.svelte';
	import Navbar from '$lib/components/layout/Navbar.svelte';
	import { getUserById } from '$lib/apis/users';
	import { error } from '@sveltejs/kit';
	import { getModels } from '$lib/apis';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	let loaded = false;

	let autoScroll = true;
	let processing = '';
	let messagesContainerElement: HTMLDivElement;

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

	$: if ($page.params.id) {
		(async () => {
			if (await loadSharedChat()) {
				await tick();
				loaded = true;
			} else {
				await goto('/');
			}
		})();
	}

	//////////////////////////
	// Web functions
	//////////////////////////

	const loadSharedChat = async () => {
		await models.set(await getModels(localStorage.token));
		await chatId.set($page.params.id);
		chat = await getChatByShareId(localStorage.token, $chatId).catch(async (error) => {
			await goto('/');
			return null;
		});

		if (chat) {
			user = await getUserById(localStorage.token, chat.user_id).catch((error) => {
				console.error(error);
				return null;
			});

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

				if (messages.length > 0) {
					history.messages[messages.at(-1).id].done = true;
				}
				await tick();

				return true;
			} else {
				return null;
			}
		}
	};

	const cloneSharedChat = async () => {
		if (!chat) return;
		
		const res = await cloneChatByShareId(localStorage.token, chat.id).catch((error) => {
			toast.error(error);
			return null;
		});

		if (res) {
			goto(`/c/${res.id}`);
		}
	};
</script>

<svelte:head>
	<title>
		{title
			? `${title.length > 30 ? `${title.slice(0, 30)}...` : title} | ${$WEBUI_NAME}`
			: `${$WEBUI_NAME}`}
	</title>
</svelte:head>

{#if loaded}
	<div
		class="min-h-screen max-h-screen w-full flex flex-col text-gray-700 dark:text-gray-100 bg-white dark:bg-gray-900"
	>
		<div class="flex flex-col flex-auto justify-center py-8">
			<div class="px-3 w-full max-w-5xl mx-auto">
				<div>
					<div class=" text-3xl font-semibold line-clamp-1">
						{title}
					</div>

					<div class="flex justify-between items-center mt-1">
						<div class="text-gray-400">
							{dayjs(chat.chat.timestamp).format($i18n.t('MMMM DD, YYYY'))}
						</div>
						<button
							class="px-4 py-2 text-sm font-medium bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl transition"
							on:click={cloneSharedChat}
						>
							{$i18n.t('Clone in OpenWebUI')}
						</button>
					</div>
				</div>

				<hr class="border-gray-50 dark:border-gray-850 mt-6 mb-2" />
			</div>

			<div class=" flex flex-col w-full flex-auto overflow-auto h-0" id="messages-container">
				<div class=" h-full w-full flex flex-col py-4">
					<div class="py-2">
						<Messages
							{user}
							chatId={$chatId}
							readOnly={true}
							{selectedModels}
							{processing}
							bind:history
							bind:messages
							bind:autoScroll
							bottomPadding={files.length > 0}
							sendPrompt={() => {}}
							continueResponse={() => {}}
							regenerateResponse={() => {}}
						/>
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}
