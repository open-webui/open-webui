<script lang="ts">
	import { onMount, tick, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { modelfiles, settings, chatId, WEBUI_NAME } from '$lib/stores';
	import { convertMessagesToHistory } from '$lib/utils';

	import { getChatByShareId } from '$lib/apis/chats';

	import Messages from '$lib/components/chat/Messages.svelte';
	import Navbar from '$lib/components/layout/Navbar.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	let autoScroll = true;
	let processing = '';
	let messagesContainerElement: HTMLDivElement;

	// let chatId = $page.params.id;
	let showModelSelector = false;
	let selectedModels = [''];

	let selectedModelfiles = {};
	$: selectedModelfiles = selectedModels.reduce((a, tagName, i, arr) => {
		const modelfile =
			$modelfiles.filter((modelfile) => modelfile.tagName === tagName)?.at(0) ?? undefined;

		return {
			...a,
			...(modelfile && { [tagName]: modelfile })
		};
	}, {});

	let chat = null;

	let title = '';
	let files = [];

	let messages = [];
	let history = {
		messages: {},
		currentId: null
	};

	$: if (history.currentId !== null) {
		let _messages = [];

		let currentMessage = history.messages[history.currentId];
		while (currentMessage !== null) {
			_messages.unshift({ ...currentMessage });
			currentMessage =
				currentMessage.parentId !== null ? history.messages[currentMessage.parentId] : null;
		}
		messages = _messages;
	} else {
		messages = [];
	}

	$: if ($page.params.id) {
		(async () => {
			if (await loadSharedChat()) {
				await tick();
				loaded = true;

				window.setTimeout(() => scrollToBottom(), 0);
				const chatInput = document.getElementById('chat-textarea');
				chatInput?.focus();
			} else {
				await goto('/');
			}
		})();
	}

	//////////////////////////
	// Web functions
	//////////////////////////

	const loadSharedChat = async () => {
		await chatId.set($page.params.id);
		chat = await getChatByShareId(localStorage.token, $chatId).catch(async (error) => {
			await goto('/');
			return null;
		});

		if (chat) {
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

				let _settings = JSON.parse(localStorage.getItem('settings') ?? '{}');
				await settings.set({
					..._settings,
					system: chatContent.system ?? _settings.system,
					options: chatContent.options ?? _settings.options
				});
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

	const scrollToBottom = () => {
		if (messagesContainerElement) {
			messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
		}
	};

	onMount(async () => {
		if (!($settings.saveChatHistory ?? true)) {
			await goto('/');
		}
	});
</script>

<svelte:head>
	<title>
		{title
			? `${title.length > 30 ? `${title.slice(0, 30)}...` : title} | ${$WEBUI_NAME}`
			: `${$WEBUI_NAME}`}
	</title>
</svelte:head>

{#if loaded}
	<div class="min-h-screen max-h-screen w-full flex flex-col">
		<Navbar
			{title}
			bind:selectedModels
			bind:showModelSelector
			shareEnabled={false}
			initNewChat={async () => {
				goto('/');
			}}
		/>
		<div class="flex flex-col flex-auto">
			<div
				class=" pb-2.5 flex flex-col justify-between w-full flex-auto overflow-auto h-0"
				id="messages-container"
				bind:this={messagesContainerElement}
				on:scroll={(e) => {
					autoScroll =
						messagesContainerElement.scrollHeight - messagesContainerElement.scrollTop <=
						messagesContainerElement.clientHeight + 5;
				}}
			>
				<div class=" h-full w-full flex flex-col py-4">
					<Messages
						chatId={$chatId}
						readOnly={true}
						{selectedModels}
						{selectedModelfiles}
						{processing}
						bind:history
						bind:messages
						bind:autoScroll
						bottomPadding={files.length > 0}
						sendPrompt={() => {}}
						continueGeneration={() => {}}
						regenerateResponse={() => {}}
					/>
				</div>
			</div>
		</div>
	</div>
{/if}
