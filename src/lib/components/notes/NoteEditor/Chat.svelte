<script lang="ts">
	export let show = false;
	export let selectedModelId = '';

	import { marked } from 'marked';
	// Configure marked with extensions
	marked.use({
		breaks: true,
		gfm: true,
		renderer: {
			list(body, ordered, start) {
				const isTaskList = body.includes('data-checked=');

				if (isTaskList) {
					return `<ul data-type="taskList">${body}</ul>`;
				}

				const type = ordered ? 'ol' : 'ul';
				const startatt = ordered && start !== 1 ? ` start="${start}"` : '';
				return `<${type}${startatt}>${body}</${type}>`;
			},

			listitem(text, task, checked) {
				if (task) {
					const checkedAttr = checked ? 'true' : 'false';
					return `<li data-type="taskItem" data-checked="${checkedAttr}">${text}</li>`;
				}
				return `<li>${text}</li>`;
			}
		}
	});

	import { toast } from 'svelte-sonner';

	import { goto } from '$app/navigation';
	import { onMount, tick, getContext } from 'svelte';

	import { WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, models, settings } from '$lib/stores';

	import { chatCompletion } from '$lib/apis/openai';

	import { splitStream } from '$lib/utils';

	import Messages from '$lib/components/notes/NoteEditor/Chat/Messages.svelte';
	import MessageInput from '$lib/components/channel/MessageInput.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import PencilSquare from '$lib/components/icons/PencilSquare.svelte';

	const i18n = getContext('i18n');

	export let editor = null;

	export let editing = false;
	export let streaming = false;
	export let stopResponseFlag = false;

	export let note = null;
	export let selectedContent = null;

	export let files = [];
	export let messages = [];

	export let onInsert = (content) => {};
	export let onStop = () => {};
	export let onEdited = () => {};

	export let insertNoteHandler = () => {};
	export let scrollToBottomHandler = () => {};

	let loaded = false;

	let loading = false;

	let messagesContainerElement: HTMLDivElement;

	let system = '';
	let editEnabled = false;
	let chatInputElement = null;

	const DEFAULT_DOCUMENT_EDITOR_PROMPT = `You are an expert document editor.

## Task
Based on the user's instruction, update and enhance the existing notes or selection by incorporating relevant and accurate information from the provided context in the content's primary language. Ensure all edits strictly follow the user’s intent.

## Input Structure
- Existing notes: Enclosed within <notes></notes> XML tags.
- Additional context: Enclosed within <context></context> XML tags.
- Current note selection: Enclosed within <selection></selection> XML tags.
- Editing instruction: Provided in the user message.

## Output Instructions
- If a selection is provided, edit **only** the content within <selection></selection>. Leave unselected parts unchanged.
- If no selection is provided, edit the entire notes.
- Deliver a single, rewritten version of the notes in markdown format.
- Integrate information from the context only if it directly supports the user's instruction.
- Use clear, organized markdown elements: headings, lists, task lists ([ ]) where tasks or checklists are strongly implied, bold and italic text as appropriate.
- Focus on improving clarity, completeness, and usefulness of the notes.
- Return only the final, fully-edited markdown notes—do not include explanations, reasoning, or XML tags.
`;

	let scrolledToBottom = true;

	const scrollToBottom = () => {
		if (messagesContainerElement) {
			if (scrolledToBottom) {
				messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
			}
		}
	};

	const onScroll = () => {
		if (messagesContainerElement) {
			scrolledToBottom =
				messagesContainerElement.scrollHeight - messagesContainerElement.scrollTop <=
				messagesContainerElement.clientHeight + 10;
		}
	};

	const chatCompletionHandler = async () => {
		if (selectedModelId === '') {
			toast.error($i18n.t('Please select a model.'));
			return;
		}

		const model = $models.find((model) => model.id === selectedModelId);
		if (!model) {
			selectedModelId = '';
			return;
		}

		let responseMessage;
		if (messages.at(-1)?.role === 'assistant') {
			responseMessage = messages.at(-1);
		} else {
			responseMessage = {
				role: 'assistant',
				content: '',
				done: false
			};
			messages.push(responseMessage);
			messages = messages;
		}

		await tick();
		scrollToBottom();

		stopResponseFlag = false;
		let enhancedContent = {
			json: null,
			html: '',
			md: ''
		};

		system = '';

		if (editEnabled) {
			system = `${DEFAULT_DOCUMENT_EDITOR_PROMPT}\n\n`;
		} else {
			system = `You are a helpful assistant. Please answer the user's questions based on the context provided.\n\n`;
		}

		system +=
			`<notes>${note?.data?.content?.md ?? ''}</notes>` +
			(files && files.length > 0
				? `\n<context>${files.map((file) => `${file.name}: ${file?.file?.data?.content ?? 'Could not extract content'}\n`).join('')}</context>`
				: '') +
			(selectedContent ? `\n<selection>${selectedContent?.text}</selection>` : '');

		const chatMessages = JSON.parse(
			JSON.stringify([
				{
					role: 'system',
					content: `${system}`
				},
				...messages
			])
		);

		const [res, controller] = await chatCompletion(
			localStorage.token,
			{
				model: model.id,
				stream: true,
				messages: chatMessages.map((m) => ({
					role: m.role,
					content: m.content
				}))
				// ...(files && files.length > 0 ? { files } : {}) // TODO: Decide whether to use native file handling or not
			},
			`${WEBUI_BASE_URL}/api`
		);

		await tick();
		scrollToBottom();

		let messageContent = '';

		if (res && res.ok) {
			const reader = res.body
				.pipeThrough(new TextDecoderStream())
				.pipeThrough(splitStream('\n'))
				.getReader();

			while (true) {
				const { value, done } = await reader.read();
				if (done || stopResponseFlag) {
					if (stopResponseFlag) {
						controller.abort('User: Stop Response');
					}

					if (editEnabled) {
						editing = false;
						streaming = false;
						onEdited();
					}

					break;
				}

				try {
					let lines = value.split('\n');

					for (const line of lines) {
						if (line !== '') {
							console.log(line);
							if (line === 'data: [DONE]') {
								if (editEnabled) {
									responseMessage.content = `<status title="${$i18n.t('Edited')}" done="true" />`;

									if (selectedContent && selectedContent?.text && editor) {
										editor.commands.insertContentAt(
											{
												from: selectedContent.from,
												to: selectedContent.to
											},
											enhancedContent.html || enhancedContent.md || ''
										);

										selectedContent = null;
									}
								}

								responseMessage.done = true;
								messages = messages;
							} else {
								let data = JSON.parse(line.replace(/^data: /, ''));
								console.log(data);

								let deltaContent = data.choices[0]?.delta?.content ?? '';
								if (responseMessage.content == '' && deltaContent == '\n') {
									continue;
								} else {
									if (editEnabled) {
										editing = true;
										streaming = true;

										enhancedContent.md += deltaContent;
										enhancedContent.html = marked.parse(enhancedContent.md);

										if (!selectedContent || !selectedContent?.text) {
											note.data.content.md = enhancedContent.md;
											note.data.content.html = enhancedContent.html;
											note.data.content.json = null;
										}

										scrollToBottomHandler();

										responseMessage.content = `<status title="${$i18n.t('Editing')}" done="false" />`;
										messages = messages;
									} else {
										messageContent += deltaContent;

										responseMessage.content = messageContent;
										messages = messages;
									}

									await tick();
								}
							}
						}
					}
				} catch (error) {
					console.log(error);
				}

				scrollToBottom();
			}
		}
	};

	const submitHandler = async (e) => {
		const { content, data } = e;
		if (selectedModelId && content) {
			messages.push({
				role: 'user',
				content: content
			});
			messages = messages;

			await tick();
			scrollToBottom();

			loading = true;
			await chatCompletionHandler();
			messages = messages.map((message) => {
				message.done = true;
				return message;
			});

			loading = false;
			stopResponseFlag = false;
		}
	};

	onMount(async () => {
		editEnabled = localStorage.getItem('noteEditEnabled') === 'true';

		loaded = true;

		await tick();
		scrollToBottom();
	});
</script>

<div class="flex items-center mb-1.5 pt-1.5">
	<div class="flex items-center mr-1">
		<button
			class="p-0.5 bg-transparent transition rounded-lg"
			on:click={() => {
				show = !show;
			}}
		>
			<XMark className="size-5" strokeWidth="2.5" />
		</button>
	</div>

	<div class=" font-medium text-base flex items-center gap-1">
		<div>
			{$i18n.t('Chat')}
		</div>

		<div>
			<Tooltip
				content={$i18n.t(
					'This feature is experimental and may be modified or discontinued without notice.'
				)}
				position="top"
				className="inline-block"
			>
				<span class="text-gray-500 text-sm">({$i18n.t('Experimental')})</span>
			</Tooltip>
		</div>
	</div>
</div>

<div class="flex flex-col items-center flex-1 @container">
	<div class=" flex flex-col justify-between w-full overflow-y-auto h-full">
		<div class="mx-auto w-full md:px-0 h-full relative">
			<div class=" flex flex-col h-full">
				<div
					class=" pb-2.5 flex flex-col justify-between w-full flex-auto overflow-auto h-0 scrollbar-hidden"
					id="messages-container"
					bind:this={messagesContainerElement}
					on:scroll={onScroll}
				>
					<div class=" h-full w-full flex flex-col">
						<div class="flex-1 p-1">
							<Messages bind:messages {onInsert} />
						</div>
					</div>
				</div>

				<div class=" pb-[1rem]">
					{#if selectedContent}
						<div class="text-xs rounded-xl px-2.5 py-3 w-full markdown-prose-xs">
							<blockquote>
								<div class=" line-clamp-3">
									{selectedContent?.text}
								</div>
							</blockquote>
						</div>
					{/if}

					<MessageInput
						bind:chatInputElement
						acceptFiles={false}
						inputLoading={loading}
						showFormattingToolbar={false}
						onSubmit={submitHandler}
						{onStop}
					>
						<div slot="menu" class="flex items-center justify-between gap-2 w-full pr-1">
							<div>
								<Tooltip content={$i18n.t('Edit')} placement="top">
									<button
										on:click|preventDefault={() => {
											editEnabled = !editEnabled;

											localStorage.setItem('noteEditEnabled', editEnabled ? 'true' : 'false');
										}}
										disabled={streaming || loading}
										type="button"
										class="px-2 @xl:px-2.5 py-2 flex gap-1.5 items-center text-sm rounded-full transition-colors duration-300 focus:outline-hidden max-w-full overflow-hidden hover:bg-gray-50 dark:hover:bg-gray-800 {editEnabled
											? ' text-sky-500 dark:text-sky-300 bg-sky-50 dark:bg-sky-200/5'
											: 'bg-transparent text-gray-600 dark:text-gray-300 '} disabled:opacity-50 disabled:pointer-events-none"
									>
										<PencilSquare className="size-4" strokeWidth="1.75" />
										<span
											class="block whitespace-nowrap overflow-hidden text-ellipsis leading-none pr-0.5"
											>{$i18n.t('Edit')}</span
										>
									</button>
								</Tooltip>
							</div>

							<Tooltip content={selectedModelId}>
								<select
									class=" bg-transparent rounded-lg py-1 px-2 -mx-0.5 text-sm outline-hidden w-full text-right pr-5"
									bind:value={selectedModelId}
								>
									{#each $models.filter((model) => !(model?.info?.meta?.hidden ?? false)) as model}
										<option value={model.id} class="bg-gray-50 dark:bg-gray-700"
											>{model.name}</option
										>
									{/each}
								</select>
							</Tooltip>
						</div>
					</MessageInput>
				</div>
			</div>
		</div>
	</div>
</div>
