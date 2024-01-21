<script lang="ts">
	import toast from 'svelte-french-toast';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { getChatById } from '$lib/apis/chats';
	import { chatId, modelfiles } from '$lib/stores';
	import ShareChatModal from '../chat/ShareChatModal.svelte';
	import TagInput from '../common/Tags/TagInput.svelte';
	import Tags from '../common/Tags.svelte';

	export let initNewChat: Function;
	export let title: string = 'Ollama Web UI';
	export let shareEnabled: boolean = false;

	export let tags = [];
	export let addTag: Function;
	export let deleteTag: Function;

	let showShareChatModal = false;

	let tagName = '';
	let showTagInput = false;

	const shareChat = async () => {
		const chat = (await getChatById(localStorage.token, $chatId)).chat;
		console.log('share', chat);

		toast.success('Redirecting you to OllamaHub');
		const url = 'https://ollamahub.com';
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
<nav
	id="nav"
	class=" fixed py-2.5 top-0 flex flex-row justify-center bg-white/95 dark:bg-gray-900/90 dark:text-gray-200 backdrop-blur-xl w-screen z-30"
>
	<div class=" flex max-w-3xl w-full mx-auto px-3">
		<div class="flex items-center w-full max-w-full">
			<div class="pl-2 self-center flex items-center justify-between space-x-2 w-full">
				{#if shareEnabled}
					<Tags {tags} {deleteTag} {addTag} />
					<div class="flex flex-row space-x-0.5 line-clamp-1">
						Tags:&nbsp;
						{#each tags as tag}
							<div
								class="px-2 py-0.5 space-x-1 flex h-fit items-center rounded-full transition border dark:border-gray-600 dark:text-white"
							>
								<div class=" text-[0.65rem] font-medium self-center line-clamp-1">
									{tag.name}
								</div>
								<button
									class=" m-auto self-center cursor-pointer"
									on:click={() => {
										deleteTag(tag.name);
									}}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 16 16"
										fill="currentColor"
										class="w-3 h-3"
									>
										<path
											d="M5.28 4.22a.75.75 0 0 0-1.06 1.06L6.94 8l-2.72 2.72a.75.75 0 1 0 1.06 1.06L8 9.06l2.72 2.72a.75.75 0 1 0 1.06-1.06L9.06 8l2.72-2.72a.75.75 0 0 0-1.06-1.06L8 6.94 5.28 4.22Z"
										/>
									</svg>
								</button>
							</div>
						{/each}

						<div class="flex space-x-1 pl-1.5">
							{#if showTagInput}
								<div class="flex items-center">
									<input
										bind:value={tagName}
										class=" cursor-pointer self-center text-xs h-fit bg-transparent outline-none line-clamp-1 w-[4rem]"
										placeholder="Add a tag"
									/>

									<button
										on:click={() => {
											addTagHandler();
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 16 16"
											fill="currentColor"
											class="w-3 h-3"
										>
											<path
												fill-rule="evenodd"
												d="M12.416 3.376a.75.75 0 0 1 .208 1.04l-5 7.5a.75.75 0 0 1-1.154.114l-3-3a.75.75 0 0 1 1.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 0 1 1.04-.207Z"
												clip-rule="evenodd"
											/>
										</svg>
									</button>
								</div>

								<!-- TODO: Tag Suggestions -->
							{/if}

							<button
								class=" cursor-pointer self-center p-0.5 space-x-1 flex h-fit items-center dark:hover:bg-gray-700 rounded-full transition border dark:border-gray-600 border-dashed"
								on:click={() => {
									showTagInput = !showTagInput;
								}}
							>
								<div class=" m-auto self-center">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 16 16"
										fill="currentColor"
										class="w-3 h-3 {showTagInput ? 'rotate-45' : ''} transition-all transform"
									>
										<path
											d="M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5a.75.75 0 0 0 0 1.5h3.5v3.5a.75.75 0 0 0 1.5 0v-3.5h3.5a.75.75 0 0 0 0-1.5h-3.5v-3.5Z"
										/>
									</svg>
								</div>
							</button>
						</div>
					</div>

					<button
						class=" cursor-pointer p-1.5 flex dark:hover:bg-gray-700 rounded-lg transition border dark:border-gray-600"
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
				{/if}
			</div>
		</div>
	</div>
</nav>
