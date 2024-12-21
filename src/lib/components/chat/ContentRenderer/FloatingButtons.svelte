<script lang="ts">
	import { toast } from 'svelte-sonner';

	import DOMPurify from 'dompurify';
	import { marked } from 'marked';

	import { getContext, tick } from 'svelte';
	const i18n = getContext('i18n');

	import { chatCompletion } from '$lib/apis/openai';

	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';
	import LightBlub from '$lib/components/icons/LightBlub.svelte';
	import Markdown from '../Messages/Markdown.svelte';
	import Skeleton from '../Messages/Skeleton.svelte';

	export let id = '';
	export let model = null;
	export let messages = [];
	export let onAdd = () => {};

	let floatingInput = false;

	let selectedText = '';
	let floatingInputValue = '';

	let prompt = '';
	let responseContent = null;
	let responseDone = false;

	const autoScroll = async () => {
		// Scroll to bottom only if the scroll is at the bottom give 50px buffer
		const responseContainer = document.getElementById('response-container');
		if (
			responseContainer.scrollHeight - responseContainer.clientHeight <=
			responseContainer.scrollTop + 50
		) {
			responseContainer.scrollTop = responseContainer.scrollHeight;
		}
	};

	const askHandler = async () => {
		if (!model) {
			toast.error('Model not selected');
			return;
		}
		prompt = `${floatingInputValue}\n\`\`\`\n${selectedText}\n\`\`\``;
		floatingInputValue = '';

		responseContent = '';
		const [res, controller] = await chatCompletion(localStorage.token, {
			model: model,
			messages: [
				...messages,
				{
					role: 'user',
					content: prompt
				}
			].map((message) => ({
				role: message.role,
				content: message.content
			})),
			stream: true // Enable streaming
		});

		if (res && res.ok) {
			const reader = res.body.getReader();
			const decoder = new TextDecoder();

			const processStream = async () => {
				while (true) {
					// Read data chunks from the response stream
					const { done, value } = await reader.read();
					if (done) {
						break;
					}

					// Decode the received chunk
					const chunk = decoder.decode(value, { stream: true });

					// Process lines within the chunk
					const lines = chunk.split('\n').filter((line) => line.trim() !== '');

					for (const line of lines) {
						if (line.startsWith('data: ')) {
							if (line.startsWith('data: [DONE]')) {
								responseDone = true;

								await tick();
								autoScroll();
								continue;
							} else {
								// Parse the JSON chunk
								try {
									const data = JSON.parse(line.slice(6));

									// Append the `content` field from the "choices" object
									if (data.choices && data.choices[0]?.delta?.content) {
										responseContent += data.choices[0].delta.content;

										autoScroll();
									}
								} catch (e) {
									console.error(e);
								}
							}
						}
					}
				}
			};

			// Process the stream in the background
			await processStream();
		} else {
			toast.error('An error occurred while fetching the explanation');
		}
	};

	const explainHandler = async () => {
		if (!model) {
			toast.error('Model not selected');
			return;
		}
		prompt = `Explain this section to me in more detail\n\n\`\`\`\n${selectedText}\n\`\`\``;

		responseContent = '';
		const [res, controller] = await chatCompletion(localStorage.token, {
			model: model,
			messages: [
				...messages,
				{
					role: 'user',
					content: prompt
				}
			].map((message) => ({
				role: message.role,
				content: message.content
			})),
			stream: true // Enable streaming
		});

		if (res && res.ok) {
			const reader = res.body.getReader();
			const decoder = new TextDecoder();

			const processStream = async () => {
				while (true) {
					// Read data chunks from the response stream
					const { done, value } = await reader.read();
					if (done) {
						break;
					}

					// Decode the received chunk
					const chunk = decoder.decode(value, { stream: true });

					// Process lines within the chunk
					const lines = chunk.split('\n').filter((line) => line.trim() !== '');

					for (const line of lines) {
						if (line.startsWith('data: ')) {
							if (line.startsWith('data: [DONE]')) {
								responseDone = true;

								await tick();
								autoScroll();
								continue;
							} else {
								// Parse the JSON chunk
								try {
									const data = JSON.parse(line.slice(6));

									// Append the `content` field from the "choices" object
									if (data.choices && data.choices[0]?.delta?.content) {
										responseContent += data.choices[0].delta.content;

										autoScroll();
									}
								} catch (e) {
									console.error(e);
								}
							}
						}
					}
				}
			};

			// Process the stream in the background
			await processStream();
		} else {
			toast.error('An error occurred while fetching the explanation');
		}
	};

	const addHandler = async () => {
		const messages = [
			{
				role: 'user',
				content: prompt
			},
			{
				role: 'assistant',
				content: responseContent
			}
		];

		onAdd({
			modelId: model,
			parentId: id,
			messages: messages
		});
	};

	export const closeHandler = () => {
		responseContent = null;
		responseDone = false;
		floatingInput = false;
		floatingInputValue = '';
	};
</script>

<div
	id={`floating-buttons-${id}`}
	class="absolute rounded-lg mt-1 text-xs z-[9999]"
	style="display: none"
>
	{#if responseContent === null}
		{#if !floatingInput}
			<div
				class="flex flex-row gap-0.5 shrink-0 p-1 bg-white dark:bg-gray-850 dark:text-gray-100 text-medium rounded-lg shadow-xl"
			>
				<button
					class="px-1 hover:bg-gray-50 dark:hover:bg-gray-800 rounded flex items-center gap-1 min-w-fit"
					on:click={async () => {
						selectedText = window.getSelection().toString();
						floatingInput = true;

						await tick();
						setTimeout(() => {
							const input = document.getElementById('floating-message-input');
							if (input) {
								input.focus();
							}
						}, 0);
					}}
				>
					<ChatBubble className="size-3 shrink-0" />

					<div class="shrink-0">Ask</div>
				</button>
				<button
					class="px-1 hover:bg-gray-50 dark:hover:bg-gray-800 rounded flex items-center gap-1 min-w-fit"
					on:click={() => {
						selectedText = window.getSelection().toString();
						explainHandler();
					}}
				>
					<LightBlub className="size-3 shrink-0" />

					<div class="shrink-0">Explain</div>
				</button>
			</div>
		{:else}
			<div
				class="py-1 flex dark:text-gray-100 bg-gray-50 dark:bg-gray-800 border dark:border-gray-800 w-72 rounded-full shadow-xl"
			>
				<input
					type="text"
					id="floating-message-input"
					class="ml-5 bg-transparent outline-none w-full flex-1 text-sm"
					placeholder={$i18n.t('Ask a question')}
					bind:value={floatingInputValue}
					on:keydown={(e) => {
						if (e.key === 'Enter') {
							askHandler();
						}
					}}
				/>

				<div class="ml-1 mr-2">
					<button
						class="{floatingInputValue !== ''
							? 'bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 '
							: 'text-white bg-gray-200 dark:text-gray-900 dark:bg-gray-700 disabled'} transition rounded-full p-1.5 m-0.5 self-center"
						on:click={() => {
							askHandler();
						}}
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
				</div>
			</div>
		{/if}
	{:else}
		<div class="bg-white dark:bg-gray-850 dark:text-gray-100 rounded-xl shadow-xl w-80 max-w-full">
			<div
				class="bg-gray-50/50 dark:bg-gray-800 dark:text-gray-100 text-medium rounded-xl px-3.5 py-3 w-full"
			>
				<div class="font-medium">
					<Markdown id={`${id}-float-prompt`} content={prompt} />
				</div>
			</div>

			<div
				class="bg-white dark:bg-gray-850 dark:text-gray-100 text-medium rounded-xl px-3.5 py-3 w-full"
			>
				<div class=" max-h-80 overflow-y-auto w-full markdown-prose-xs" id="response-container">
					{#if responseContent.trim() === ''}
						<Skeleton size="sm" />
					{:else}
						<Markdown id={`${id}-float-response`} content={responseContent} />
					{/if}

					{#if responseDone}
						<div class="flex justify-end pt-3 text-sm font-medium">
							<button
								class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
								on:click={addHandler}
							>
								{$i18n.t('Add')}
							</button>
						</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>
