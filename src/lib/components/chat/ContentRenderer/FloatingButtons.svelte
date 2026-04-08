<script lang="ts">
	import { toast } from 'svelte-sonner';

	import DOMPurify from 'dompurify';
	import { marked } from 'marked';

	import { getContext, tick, onDestroy } from 'svelte';
	const i18n = getContext('i18n');

	import { chatCompletion } from '$lib/apis/openai';

	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';
	import LightBulb from '$lib/components/icons/LightBulb.svelte';
	import Clipboard from '$lib/components/icons/Clipboard.svelte';
	import Markdown from '../Messages/Markdown.svelte';
	import Skeleton from '../Messages/Skeleton.svelte';
	import { chatId, models, socket, chatInputContext } from '$lib/stores';

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
			label: '질문하기',
			icon: ChatBubble,
			contextOnly: true
		},
		{
			id: 'summarize',
			label: '요약하기',
			icon: Clipboard,
			prompt: `다음 내용을 핵심만 간결하게 요약해줘:\n\n{{SELECTED_CONTENT}}`
		},
		{
			id: 'explain',
			label: '설명하기',
			icon: LightBulb,
			prompt: `다음 내용을 쉽게 설명해줘:\n\n{{SELECTED_CONTENT}}`
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
		<div
			class="flex flex-row items-center gap-1.5 p-1.5
				bg-white/90 dark:bg-gray-850/95
				backdrop-blur-md
				border border-gray-200/60 dark:border-gray-700/60
				rounded-2xl shadow-lg"
		>
			{#each actions as action}
				<button
					class="flex items-center gap-1.5 px-3 py-1.5
						text-sm font-medium
						rounded-xl
						transition-all duration-150
						{action.id === 'ask'
							? 'bg-blue-500 hover:bg-blue-600 text-white'
							: 'text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700/60'}"
					on:click={async () => {
						selectedText = window.getSelection().toString();
						selectedAction = action;

						if (action.contextOnly) {
							// 질문하기: 선택 텍스트를 컨텍스트로 저장하고 입력창 포커스
							chatInputContext.set(selectedText);
							const floatingDiv = document.getElementById(`floating-buttons-${id}`);
							if (floatingDiv) floatingDiv.style.display = 'none';
							document.getElementById('chat-input')?.focus();
							return;
						}

						actionHandler(action.id);
					}}
				>
					{#if action.icon}
						<svelte:component this={action.icon} className="size-3.5 shrink-0" />
					{/if}
					<span class="shrink-0">{action.label}</span>
				</button>
			{/each}
		</div>
	{:else}
		<div
			class="bg-white dark:bg-gray-850 dark:text-gray-100 rounded-3xl shadow-xl w-80 max-w-full border border-gray-100 dark:border-gray-800 flex flex-col"
			style="max-height: min(28rem, 80vh)"
		>
			<!-- Header: action label + selected text preview -->
			<div class="px-3.5 pt-3 pb-2 flex flex-col gap-1 border-b border-gray-100 dark:border-gray-700/50 flex-shrink-0">
				<div class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
					{selectedAction?.label ?? ''}
				</div>
				<p class="text-xs text-gray-600 dark:text-gray-400 line-clamp-2 break-words leading-relaxed">
					"{selectedText}"
				</p>
			</div>

			<!-- Response body -->
			<div class="overflow-y-auto flex-1 w-full markdown-prose-xs px-3.5 py-3" id="response-container">
				{#if !responseContent || responseContent?.trim() === ''}
					<Skeleton size="sm" />
				{:else}
					<Markdown id={`${id}-float-response`} content={responseContent} />
				{/if}
			</div>

			{#if responseDone}
				<div class="flex justify-end px-3.5 pb-3 pt-1 flex-shrink-0">
					<button
						class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
						on:click={addHandler}
					>
						{$i18n.t('Add')}
					</button>
				</div>
			{/if}
		</div>
	{/if}
</div>
