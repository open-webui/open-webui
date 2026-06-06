<script lang="ts">
import { toast } from 'svelte-sonner';
import DOMPurify from 'dompurify';
import { marked } from 'marked';
import { getContext, tick, onDestroy, onMount } from 'svelte';
const i18n = getContext('i18n');

import { chatId, models, socket } from '$lib/stores';

import { chatCompletion } from '$lib/apis/openai';
import ChatBubble from '$lib/components/icons/ChatBubble.svelte';
import LightBulb from '$lib/components/icons/LightBulb.svelte';
import XMark from '$lib/components/icons/XMark.svelte';
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
let sidebarOpen = false;

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

const responseContainerId = () => `response-container-${id}`;
const floatingInputId = () => `floating-message-input-${id}`;

const autoScroll = async () => {
	const responseContainer = document.getElementById(responseContainerId());
	if (responseContainer) {
		if (
			responseContainer.scrollHeight - responseContainer.clientHeight <=
			responseContainer.scrollTop + 50
		) {
			responseContainer.scrollTop = responseContainer.scrollHeight;
		}
	}
};

const openSidebar = async () => {
	sidebarOpen = true;
	window.dispatchEvent(
		new CustomEvent('openwebui:floatingSidebarOpen', {
			detail: { id }
		})
	);
};

const resetForNewAction = () => {
	if (controller) {
		controller.abort();
	}
	responseContent = null;
	responseDone = false;
	content = '';
	floatingInput = false;
	floatingInputValue = '';
};

export const isSidebarOpen = () => sidebarOpen;

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
	const varToolPattern = /\{\{(.*?)\|tool:id="([^"]+)"\}\}/g;
	prompt = prompt.replace(varToolPattern, (match, variableId, toolId) => {
		toolIds.push(toolId);
		return variableId;
	});

	// legacy {{TOOL:toolId}} pattern
	let toolIdPattern = /\{\{TOOL:([^\}]+)\}\}/g;
	let match;
	while ((match = toolIdPattern.exec(prompt)) !== null) {
		toolIds.push(match[1]);
	}
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
		...(toolIds.length > 0 ? { tool_ids: toolIds } : {}),
		stream: true
	});

	if (res && res.ok) {
		const reader = res.body.getReader();
		const decoder = new TextDecoder();

		const processStream = async () => {
			while (true) {
				const { done, value } = await reader.read();
				if (done) break;
				const chunk = decoder.decode(value, { stream: true });
				const lines = chunk.split('\n').filter((line) => line.trim() !== '');
				for (const line of lines) {
					if (line.startsWith('data: ')) {
						if (line.startsWith('data: [DONE]')) {
							responseDone = true;
							await tick();
							autoScroll();
							continue;
						} else {
							try {
								const data = JSON.parse(line.slice(6));
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
	sidebarOpen = false;
	selectedAction = null;
	selectedText = '';
	responseContent = null;
	responseDone = false;
	floatingInput = false;
	floatingInputValue = '';
};

onMount(() => {
	const handler = (e) => {
		if (e?.detail?.id && e.detail.id !== id) {
			closeHandler();
		}
	};
	window.addEventListener('openwebui:floatingSidebarOpen', handler);
	return () => window.removeEventListener('openwebui:floatingSidebarOpen', handler);
});

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
	<div
		class="flex flex-row shrink-0 p-0.5 bg-white dark:bg-gray-850 dark:text-gray-100 text-medium rounded-xl shadow-xl border border-gray-100 dark:border-gray-800"
	>
		{#each actions as action}
			<button
				class="px-1.5 py-[1px] hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl flex items-center gap-1 min-w-fit transition"
				on:click={async () => {
					resetForNewAction();
					const selection = window.getSelection();
					selectedText = selection ? selection.toString() : '';
					selectedAction = action;
					await openSidebar();
					const floating = document.getElementById(`floating-buttons-${id}`);
					if (floating) floating.style.display = 'none';
					if (action.prompt.includes('{{INPUT_CONTENT}}')) {
						floatingInput = true;
						floatingInputValue = '';
						await tick();
						setTimeout(() => {
							const input = document.getElementById(floatingInputId());
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
</div>

{#if sidebarOpen}
	<aside
		id={`floating-sidebar-${id}`}
		class="fixed top-0 right-0 h-screen w-full sm:w-96 bg-white dark:bg-gray-900 border-l border-gray-100 dark:border-gray-800 z-9999 flex flex-col"
		aria-label={$i18n.t('Quick Actions')}
	>
		<div class="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800">
			<div class="text-sm font-medium dark:text-gray-100">
				{selectedAction?.label ?? $i18n.t('Quick Actions')}
			</div>
			<div class="flex items-center gap-1.5">
				<button
					class="p-1 rounded-md hover:bg-black/5 dark:hover:bg-white/5 transition"
					aria-label={$i18n.t('Close')}
					on:click={() => closeHandler()}
				>
					<XMark className="size-5" />
				</button>
			</div>
		</div>

		<div class="flex-1 overflow-y-auto">
			{#if responseContent === null && floatingInput}
				<div class="p-4">
					<div class="py-2 flex dark:text-gray-100 bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-full">
						<input
							type="text"
							id={floatingInputId()}
							class="ml-5 bg-transparent outline-hidden w-full flex-1 text-sm"
							placeholder={$i18n.t('Ask a question')}
							bind:value={floatingInputValue}
							on:keydown={(e) => {
								if (e.key === 'Enter') {
									actionHandler(selectedAction?.id);
								}
							}}
						/>
						<div class="ml-1 mr-1">
							<button
								class="{floatingInputValue !== ''
									? 'bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 '
									: 'text-white bg-gray-200 dark:text-gray-900 dark:bg-gray-700 disabled'} transition rounded-full p-1.5 m-0.5 self-center"
								aria-label={$i18n.t('Send')}
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
				</div>
			{:else if responseContent !== null}
				<div class="p-4 space-y-3">
					<div class="text-sm font-medium dark:text-gray-100">
						<Markdown id={`${id}-sidebar-prompt`} {content} />
					</div>
					<div
						class="min-h-24 markdown-prose-xs"
						id={responseContainerId()}
					>
						{#if !responseContent || responseContent?.trim() === ''}
							<Skeleton size="sm" />
						{:else}
							<Markdown id={`${id}-sidebar-response`} content={responseContent} />
						{/if}
						<div class="flex items-center justify-between pt-3 text-sm font-medium">
							<button
								class="px-3.5 py-1.5 text-sm font-medium bg-gray-50 hover:bg-gray-100 text-gray-800 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-100 transition rounded-full"
								on:click={() => closeHandler()}
							>
								{$i18n.t('Close')}
							</button>
							{#if responseDone}
								<button
									class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
									on:click={addHandler}
								>
									{$i18n.t('Add')}
								</button>
							{/if}
						</div>
					</div>
				</div>
			{:else}
				<div class="p-4 text-sm text-gray-600 dark:text-gray-300">
					{$i18n.t('Select text and choose an action.')}
				</div>
			{/if}
		</div>
		{#if responseContent === null}
			<div class="px-4 py-3 border-t border-gray-100 dark:border-gray-800">
				<button
					class="w-full px-3.5 py-2 text-sm font-medium bg-gray-50 hover:bg-gray-100 text-gray-800 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-100 transition rounded-full"
					on:click={() => closeHandler()}
				>
					{$i18n.t('Close')}
				</button>
			</div>
		{/if}
	</aside>
{/if}
