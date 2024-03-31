<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { Separator } from 'bits-ui';
	import { getChatById } from '$lib/apis/chats';
	import { WEBUI_NAME, chatId, modelfiles, settings, showSettings } from '$lib/stores';

	import { slide } from 'svelte/transition';
	import ShareChatModal from '../chat/ShareChatModal.svelte';
	import TagInput from '../common/Tags/TagInput.svelte';
	import ModelSelector from '../chat/ModelSelector.svelte';
	import Tooltip from '../common/Tooltip.svelte';

	import EllipsisVertical from '../icons/EllipsisVertical.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';
	import ChevronUpDown from '../icons/ChevronUpDown.svelte';
	import Menu from './Navbar/Menu.svelte';
	import TagChatModal from '../chat/TagChatModal.svelte';

	const i18n = getContext('i18n');

	export let initNewChat: Function;
	export let title: string = $WEBUI_NAME;
	export let shareEnabled: boolean = false;

	export let selectedModels;

	export let tags = [];
	export let addTag: Function;
	export let deleteTag: Function;

	export let showModelSelector = false;

	let showShareChatModal = false;
	let showTagChatModal = false;

	const shareChat = async () => {
		const chat = (await getChatById(localStorage.token, $chatId)).chat;
		console.log('share', chat);

		toast.success($i18n.t('Redirecting you to OpenWebUI Community'));
		const url = 'https://openwebui.com';
		// const url = 'http://localhost:5173';

		const tab = await window.open(`${url}/chats/upload`, '_blank');
		window.addEventListener(
			'message',
			(event) => {
				if (event.origin !== url) return;
				if (event.data === 'loaded') {
					tab.postMessage(
						JSON.stringify({
							chat: chat,
							modelfiles: $modelfiles.filter((modelfile) => chat.models.includes(modelfile.tagName))
						}),
						'*'
					);
				}
			},
			false
		);
	};

	const downloadChat = async () => {
		const chat = (await getChatById(localStorage.token, $chatId)).chat;
		console.log('download', chat);

		const chatText = chat.messages.reduce((a, message, i, arr) => {
			return `${a}### ${message.role.toUpperCase()}\n${message.content}\n\n`;
		}, '');

		let blob = new Blob([chatText], {
			type: 'text/plain'
		});

		saveAs(blob, `chat-${chat.title}.txt`);
	};
</script>

<ShareChatModal bind:show={showShareChatModal} {downloadChat} {shareChat} />
<!-- <TagChatModal bind:show={showTagChatModal} {tags} {deleteTag} {addTag} /> -->
<nav id="nav" class=" sticky py-2.5 top-0 flex flex-row justify-center z-30">
	<div
		class=" flex {$settings?.fullScreenMode ?? null ? 'max-w-full' : 'max-w-3xl'} 
		 w-full mx-auto px-3"
	>
		<!-- {#if shareEnabled}
			<div class="flex items-center w-full max-w-full">
				<div class=" flex-1 self-center font-medium line-clamp-1">
					<div>
						{title != '' ? title : $WEBUI_NAME}
					</div>
				</div>
				<div class="pl-2 self-center flex items-center">
					<div class=" mr-1">
						<Tags {tags} {deleteTag} {addTag} />
					</div>

					<Tooltip content="Share">
						<button
							class="cursor-pointer p-1.5 flex dark:hover:bg-gray-700 rounded-full transition"
							on:click={async () => {
								showShareChatModal = !showShareChatModal;

								// console.log(showShareChatModal);
							}}
						>
							<div class=" m-auto self-center">
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 24 24"
									fill="currentColor"
									class="w-4 h-4"
								>
									<path
										fill-rule="evenodd"
										d="M15.75 4.5a3 3 0 1 1 .825 2.066l-8.421 4.679a3.002 3.002 0 0 1 0 1.51l8.421 4.679a3 3 0 1 1-.729 1.31l-8.421-4.678a3 3 0 1 1 0-4.132l8.421-4.679a3 3 0 0 1-.096-.755Z"
										clip-rule="evenodd"
									/>
								</svg>
							</div>
						</button>
					</Tooltip>
				</div>
			</div>
		{/if} -->

		<!-- <div class=" flex-1 self-center font-medium line-clamp-1">
			<div>
				{title != '' ? title : $WEBUI_NAME}
			</div>
		</div> -->

		<div class="flex items-center w-full max-w-full">
			<div class="w-full flex-1 overflow-hidden max-w-full">
				<ModelSelector bind:selectedModels />
			</div>

			<div class="self-start flex flex-none items-center">
				<div class="flex self-center w-[1px] h-5 mx-2 bg-stone-700" />

				{#if !shareEnabled}
					<Tooltip content="Settings">
						<button
							class="cursor-pointer p-1.5 flex dark:hover:bg-gray-700 rounded-full transition"
							id="open-settings-button"
							on:click={async () => {
								await showSettings.set(!$showSettings);
							}}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="w-5 h-5"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z"
								/>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
								/>
							</svg>
						</button>
					</Tooltip>
				{:else}
					<Menu
						{shareEnabled}
						shareHandler={() => {
							showShareChatModal = !showShareChatModal;
						}}
						{tags}
						{deleteTag}
						{addTag}
					>
						<button
							class="cursor-pointer p-1.5 flex dark:hover:bg-gray-700 rounded-full transition"
						>
							<div class=" m-auto self-center">
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke-width="1.5"
									stroke="currentColor"
									class="size-5"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="M6.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM12.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM18.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Z"
									/>
								</svg>
							</div>
						</button>
					</Menu>
				{/if}
				<Tooltip content="New Chat">
					<button
						id="new-chat-button"
						class=" cursor-pointer p-1.5 flex dark:hover:bg-gray-700 rounded-full transition"
						on:click={() => {
							initNewChat();
						}}
					>
						<div class=" m-auto self-center">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="w-5 h-5"
							>
								<path
									d="M5.433 13.917l1.262-3.155A4 4 0 017.58 9.42l6.92-6.918a2.121 2.121 0 013 3l-6.92 6.918c-.383.383-.84.685-1.343.886l-3.154 1.262a.5.5 0 01-.65-.65z"
								/>
								<path
									d="M3.5 5.75c0-.69.56-1.25 1.25-1.25H10A.75.75 0 0010 3H4.75A2.75 2.75 0 002 5.75v9.5A2.75 2.75 0 004.75 18h9.5A2.75 2.75 0 0017 15.25V10a.75.75 0 00-1.5 0v5.25c0 .69-.56 1.25-1.25 1.25h-9.5c-.69 0-1.25-.56-1.25-1.25v-9.5z"
								/>
							</svg>
						</div>
					</button>
				</Tooltip>
			</div>
		</div>
	</div>
</nav>
