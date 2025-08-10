<script lang="ts">
	import { toast } from 'svelte-sonner';

	import DOMPurify from 'dompurify';
	import { marked } from 'marked';

	import { getContext, tick, onDestroy } from 'svelte';
	const i18n = getContext('i18n');

	import { chatCompletion } from '$lib/apis/openai';

	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';
	import LightBulb from '$lib/components/icons/LightBulb.svelte';
	import Markdown from '../Messages/Markdown.svelte';
	import Skeleton from '../Messages/Skeleton.svelte';

	export let id = '';
	export let messageId = '';

	export let model = null;
	export let messages = [];
	export let actions = [];
	export let onAdd = (e) => {};

	let floatingInput = false;
	let selectedAction = null;

	let selectedText = '';
	let floatingInputValue = '';

	let content = '';
	let responseContent = null;
	let responseDone = false;
	let controller = null;

	$: if (actions.length === 0) {
		actions = DEFAULT_ACTIONS;
	}

	const DEFAULT_ACTIONS = [
		{
			id: 'ask',
			label: $i18n.t('Ask'),
			icon: ChatBubble,
			input: true,
			prompt: `{{SELECTED_CONTENT}}\n\n\n{{INPUT_CONTENT}}`
		},
		{
			id: 'explain',
			label: $i18n.t('Explain'),
			icon: LightBulb,
			prompt: `{{SELECTED_CONTENT}}\n\n\n${$i18n.t('Explain')}`
		}
	];

	const autoScroll = async () => {
		const responseContainer = document.getElementById('response-container');
		if (responseContainer) {
			// Scroll to bottom only if the scroll is at the bottom give 50px buffer
			if (
				responseContainer.scrollHeight - responseContainer.clientHeight <=
				responseContainer.scrollTop + 50
			) {
				responseContainer.scrollTop = responseContainer.scrollHeight;
			}
		}
	};

	const actionHandler = async (actionId) => {
		if (!model) {
			toast.error('Model not selected');
			return;
		}

		let selectedContent = selectedText
			.split('\n')
			.map((line) => `> ${line}`)
			.join('\n');

		let selectedAction = actions.find((action) => action.id === actionId);
		if (!selectedAction) {
			toast.error('Action not found');
			return;
		}

		let prompt = selectedAction?.prompt ?? '';
		let toolIds = [];

		// Handle: {{variableId|tool:id="toolId"}} pattern
		// This regex captures variableId and toolId from {{variableId|tool:id="toolId"}}
		const varToolPattern = /\{\{(.*?)\|tool:id="([^"]+)"\}\}/g;
		prompt = prompt.replace(varToolPattern, (match, variableId, toolId) => {
			toolIds.push(toolId);
			return variableId; // Replace with just variableId
		});

		// legacy {{TOOL:toolId}} pattern (for backward compatibility)
		let toolIdPattern = /\{\{TOOL:([^\}]+)\}\}/g;
		let match;
		while ((match = toolIdPattern.exec(prompt)) !== null) {
			toolIds.push(match[1]);
		}

		// Remove all TOOL placeholders from the prompt
		prompt = prompt.replace(toolIdPattern, '');

		if (prompt.includes('{{INPUT_CONTENT}}') && floatingInput) {
			prompt = prompt.replace('{{INPUT_CONTENT}}', floatingInputValue);
			floatingInputValue = '';
		}

		prompt = prompt.replace('{{CONTENT}}', selectedText);
		prompt = prompt.replace('{{SELECTED_CONTENT}}', selectedContent);

		content = prompt;
		responseContent = '';

		let res;
		[res, controller] = await chatCompletion(localStorage.token, {
			model: model,
			messages: [
				...messages,
				{
					role: 'user',
					content: content
				}
			].map((message) => ({
				role: message.role,
				content: message.content
			})),
			...(toolIds.length > 0
				? {
						tool_ids: toolIds
						// params: {
						// 	function_calling: 'native'
						// }
					}
				: {}),

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
			try {
				await processStream();
			} catch (e) {
				if (e.name !== 'AbortError') {
					console.error(e);
				}
			}
		} else {
			toast.error('An error occurred while fetching the explanation');
		}
	};

	const addHandler = async () => {
		const messages = [
			{
				role: 'user',
				content: content
			},
			{
				role: 'assistant',
				content: responseContent
			}
		];

		onAdd({
			modelId: model,
			parentId: messageId,
			messages: messages
		});
	};

	export const closeHandler = () => {
		if (controller) {
			controller.abort();
		}

		selectedAction = null;
		selectedText = '';
		responseContent = null;
		responseDone = false;
		floatingInput = false;
		floatingInputValue = '';
	};

	onDestroy(() => {
		if (controller) {
			controller.abort();
		}
	});
</script>

<div
	id={`floating-buttons-${id}`}
	class="absolute rounded-lg mt-1 text-xs z-9999"
	style="display: none"
>
	{#if responseContent === null}
		{#if !floatingInput}
			<div
				class="flex flex-row gap-0.5 shrink-0 p-1 bg-white dark:bg-gray-850 dark:text-gray-100 text-medium rounded-lg shadow-xl"
			>
				{#each actions as action}
					<button
						class="px-1 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-sm flex items-center gap-1 min-w-fit"
						on:click={async () => {
							selectedText = window.getSelection().toString();
							selectedAction = action;

							if (action.prompt.includes('{{INPUT_CONTENT}}')) {
								floatingInput = true;
								floatingInputValue = '';

								await tick();
								setTimeout(() => {
									const input = document.getElementById('floating-message-input');
									if (input) {
										input.focus();
									}
								}, 0);
							} else {
								actionHandler(action.id);
							}
						}}
					>
						{#if action.icon}
							<svelte:component this={action.icon} className="size-3 shrink-0" />
						{/if}
						<div class="shrink-0">{action.label}</div>
					</button>
				{/each}
			</div>
		{:else}
			<div
				class="py-1 flex dark:text-gray-100 bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-850 w-72 rounded-full shadow-xl"
			>
				<input
					type="text"
					id="floating-message-input"
					class="ml-5 bg-transparent outline-hidden w-full flex-1 text-sm"
					placeholder={$i18n.t('Ask a question')}
					bind:value={floatingInputValue}
					on:keydown={(e) => {
						if (e.key === 'Enter') {
							actionHandler(selectedAction?.id);
						}
					}}
				/>

				<div class="ml-1 mr-2">
					<button
						class="{floatingInputValue !== ''
							? 'bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 '
							: 'text-white bg-gray-200 dark:text-gray-900 dark:bg-gray-700 disabled'} transition rounded-full p-1.5 m-0.5 self-center"
						on:click={() => {
							actionHandler(selectedAction?.id);
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
					<Markdown id={`${id}-float-prompt`} {content} />
				</div>
			</div>

			<div
				class="bg-white dark:bg-gray-850 dark:text-gray-100 text-medium rounded-xl px-3.5 py-3 w-full"
			>
				<div class=" max-h-80 overflow-y-auto w-full markdown-prose-xs" id="response-container">
					{#if !responseContent || responseContent?.trim() === ''}
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
