<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { getContext, tick, onDestroy } from 'svelte';
	const i18n = getContext('i18n');

	import { chatCompletion } from '$lib/apis/openai';

	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';
	import LightBulb from '$lib/components/icons/LightBulb.svelte';
	import Markdown from '../Messages/Markdown.svelte';
	import Skeleton from '../Messages/Skeleton.svelte';
	import { chatId, models, socket, quotedText } from '$lib/stores';

	export let id = '';
	export let messageId = '';

	export let model = null;
	export let messages = [];
	export let actions = [];
	export let onAdd = (e) => {};
	export let onClose = () => {};

	let selectedText = '';

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
			toast.error($i18n.t('Model not selected'));
			return;
		}

		let selectedContent = selectedText
			.split('\n')
			.map((line) => `> ${line}`)
			.join('\n');

		let selectedAction = actions.find((action) => action.id === actionId);
		if (!selectedAction) {
			toast.error($i18n.t('Action not found'));
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

		prompt = prompt.replace('{{INPUT_CONTENT}}', '');
		prompt = prompt.replace('{{CONTENT}}', selectedText);
		prompt = prompt.replace('{{SELECTED_CONTENT}}', selectedContent);

		content = prompt;
		responseContent = '';

		let res;
		[res, controller] = await chatCompletion(localStorage.token, {
			model: model,
			model_item: $models.find((m) => m.id === model),
			session_id: $socket?.id,
			chat_id: $chatId,
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
			toast.error($i18n.t('An error occurred while fetching the explanation'));
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

		selectedText = '';
		responseContent = null;
		responseDone = false;
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
		<div
			class="flex flex-row shrink-0 p-0.5 bg-white dark:bg-gray-850 dark:text-gray-100 text-medium rounded-xl shadow-xl border border-gray-100 dark:border-gray-800"
		>
			{#each actions as action}
				<button
					aria-label={action.label}
					class="px-1.5 py-[1px] hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl flex items-center gap-1 min-w-fit transition"
					on:click={() => {
						selectedText = window.getSelection().toString();

						if (action.input) {
							quotedText.set(selectedText);
							onClose();
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
			class="bg-white dark:bg-gray-850 dark:text-gray-100 rounded-3xl shadow-xl w-80 max-w-full border border-gray-100 dark:border-gray-800"
		>
			<div
				class="bg-white dark:bg-gray-850 dark:text-gray-100 text-medium rounded-3xl px-3.5 pt-3 w-full"
			>
				<div class="font-medium">
					<Markdown id={`${id}-float-prompt`} {content} />
				</div>
			</div>

			<div class="bg-white dark:bg-gray-850 dark:text-gray-100 text-medium rounded-4xl w-full">
				<div
					class=" max-h-80 overflow-y-auto w-full markdown-prose-xs px-3.5 py-3"
					id="response-container"
				>
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
