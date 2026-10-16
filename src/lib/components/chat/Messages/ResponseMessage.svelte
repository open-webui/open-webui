<script lang="ts">
	import EditPencilIcon from '$lib/components/layout/Sidebar/icons/EditPencil.svelte';
	import CopyIcon from '$lib/components/layout/Sidebar/icons/Copy.svelte';
	import TrashIcon from '$lib/components/layout/Sidebar/icons/Trash.svelte';
	import ChevronRightIcon from '$lib/components/layout/Sidebar/icons/ChevronRight.svelte';
	import { resolveLocalizedFunction } from '$lib/utils/localizedContent';
	import { functions as localizedFunctions } from '$lib/stores';
	import { toast } from 'svelte-sonner';

	import { createEventDispatcher, onDestroy } from 'svelte';
	import { onMount, tick, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType, t } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');

	const dispatch = createEventDispatcher();

	import { createNewFeedback, getFeedbackById, updateFeedbackById } from '$lib/apis/evaluations';
	import { getChatById } from '$lib/apis/chats';
	import { generateTags } from '$lib/apis';

	import {
		audioQueue,
		config,
		models,
		settings,
		temporaryChatEnabled,
		TTSWorker,
		user
	} from '$lib/stores';
	import { synthesizeOpenAISpeech } from '$lib/apis/audio';
	import { imageGenerations } from '$lib/apis/images';
	import {
		copyToClipboard as _copyToClipboard,
		approximateToHumanReadable,
		getMessageContentParts,
		sanitizeResponseContent,
		createMessagesList,
		formatMessageTimestamp,
		formatMessageTimestampFull,
		removeDetails,
		removeAllDetails
	} from '$lib/utils';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { resolveLocalizedModelName } from '$lib/utils/localizedContent';
	import equal from 'fast-deep-equal';

	import Name from './Name.svelte';
	import ProfileImage from './ProfileImage.svelte';
	import Image from '$lib/components/common/Image.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import RateComment from './RateComment.svelte';
	import WebSearchResults from './ResponseMessage/WebSearchResults.svelte';
	import Sparkles from '$lib/components/layout/Sidebar/icons/Sparkles.svelte';

	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	import Error from './Error.svelte';
	import Citations from './Citations.svelte';
	import CodeExecutions from './CodeExecutions.svelte';
	import ContentRenderer from './ContentRenderer.svelte';
	import { KokoroWorker } from '$lib/workers/KokoroWorker';
	import FileItem from '$lib/components/common/FileItem.svelte';
	import FollowUps from './ResponseMessage/FollowUps.svelte';
	import { fade } from 'svelte/transition';
	import { flyAndScale } from '$lib/utils/transitions';
	import RegenerateMenu from './ResponseMessage/RegenerateMenu.svelte';
	import StatusHistory from './ResponseMessage/StatusHistory.svelte';
	import FullHeightIframe from '$lib/components/common/FullHeightIframe.svelte';
	import OutputEditView from './OutputEditView.svelte';
	import { getOutputText, replaceOutputMessageText, type OutputItem } from './structuredOutput';

	interface MessageType {
		user_id?: string;
		id: string;
		model: string;
		content: string;
		output?: OutputItem[];
		files?: { type: string; url: string }[];
		timestamp: number;
		role: string;
		statusHistory?: {
			done: boolean;
			action: string;
			description: string;
			urls?: string[];
			query?: string;
		}[];
		status?: {
			done: boolean;
			action: string;
			description: string;
			urls?: string[];
			query?: string;
		};
		done: boolean;
		error?: boolean | { content: string };
		sources?: string[];
		code_executions?: {
			uuid: string;
			name: string;
			code: string;
			language?: string;
			result?: {
				error?: string;
				output?: string;
				files?: { name: string; url: string }[];
			};
		}[];
		info?: {
			openai?: boolean;
			prompt_tokens?: number;
			completion_tokens?: number;
			total_tokens?: number;
			eval_count?: number;
			eval_duration?: number;
			prompt_eval_count?: number;
			prompt_eval_duration?: number;
			total_duration?: number;
			load_duration?: number;
			usage?: unknown;
		};
		annotation?: { type: string; rating: number };
	}

	export let chatId = '';
	export let history;
	export let messageId;
	export let selectedModels = [];

	let messageSource = history.messages[messageId];
	let message: MessageType = structuredClone(messageSource);
	$: if (history.messages) {
		const source = history.messages[messageId];
		if (source) {
			// Fast path for the fields that change most often while streaming.
			// Responses streams update output even when legacy content is unchanged.
			if (source !== messageSource) {
				messageSource = source;
				message = structuredClone(source);
			} else if (
				message.content !== source.content ||
				message.done !== source.done ||
				message.output?.length !== source.output?.length
			) {
				message = structuredClone(source);
			} else if (!equal(message, source)) {
				// Slow path: full comparison for infrequent changes (sources, annotations, status, etc.)
				message = structuredClone(source);
			}
		}
	}

	export let siblings;

	export let setInputText: Function = () => {};
	export let gotoMessage: Function = () => {};
	export let showPreviousMessage: Function;
	export let showNextMessage: Function;

	export let updateChat: Function;
	export let editMessage: Function;
	export let saveMessage: Function;
	export let rateMessage: Function;
	export let actionMessage: Function;
	export let deleteMessage: Function;

	export let submitMessage: Function;
	export let continueResponse: Function;
	export let regenerateResponse: Function;
	export let forkHandler: Function | null = null;

	export let addMessages: Function;
	export let onToolCallResolved: Function = () => {};

	export let isLastMessage = true;
	export let readOnly = false;
	export let shareMode: 'continue' | null = null;
	export let allowDelete = true;
	export let compactPreview = false;
	export let editCodeBlock = true;
	export let topPadding = false;
	export let onInsertToNote: ((content: string) => void) | null = null;

	let citationsElement: HTMLDivElement;

	let contentContainerElement: HTMLDivElement;
	let buttonsContainerElement: HTMLDivElement;
	let showDeleteConfirm = false;

	let model = null;
	$: localizedModelName = model ? resolveLocalizedModelName(model, $i18n.language) : message.model;
	$: model = $models.find((m) => m.id === message.model);

	$: statusEntries = message?.statusHistory ?? [...(message?.status ? [message?.status] : [])];
	$: hasVisibleStatus =
		(model?.info?.meta?.capabilities?.status_updates ?? true) &&
		statusEntries.length > 0 &&
		!(statusEntries.at(-1)?.hidden ?? false);
	$: visibleResponseContent =
		getOutputText(message.output) || removeAllDetails(message.content ?? '');
	$: hasResponseContent = Boolean((message.content ?? '').trim() || message.output?.length);

	let edit = false;
	let editedContent = '';
	let editedOutput: any[] | null = null;
	let editTextAreaElement: HTMLTextAreaElement;

	let messageIndexEdit = false;

	let speaking = false;
	let speakingIdx: number | undefined;

	let loadingSpeech = false;
	let speakAbort: AbortController | null = null;

	let showRateComment = false;

	const copyToClipboard = async (text) => {
		text = removeAllDetails(text);

		if (($config?.ui?.response_watermark ?? '').trim() !== '') {
			text = `${text}\n\n${$config?.ui?.response_watermark}`;
		}

		const res = await _copyToClipboard(text, null, $settings?.copyFormatted ?? false);
		if (res) {
			toast.success($i18n.t('Copying to clipboard was successful!'));
		}
	};

	const stopAudio = () => {
		speakAbort?.abort();
		speakAbort = null;

		try {
			speechSynthesis.cancel();
			$audioQueue?.stop();
		} catch {}

		speaking = false;
		speakingIdx = undefined;
		loadingSpeech = false;
	};

	// Resolve voice: model-specific > user settings > config default
	const getVoiceId = () =>
		model?.info?.meta?.tts?.voice ??
		($settings?.audio?.tts?.defaultVoice === $config.audio.tts.voice
			? ($settings?.audio?.tts?.voice ?? $config?.audio?.tts?.voice)
			: $config?.audio?.tts?.voice);

	const speak = async () => {
		const content = visibleResponseContent;
		if (!content.trim().length) {
			toast.info($i18n.t('No content to speak'));
			return;
		}

		stopAudio();
		speakAbort = new AbortController();
		const { signal } = speakAbort;

		speaking = true;

		if ($config.audio.tts.engine === '') {
			let voices = [];
			const getVoicesLoop = setInterval(() => {
				voices = speechSynthesis.getVoices();
				if (voices.length > 0) {
					clearInterval(getVoicesLoop);

					const voice = voices.find((v) => v.voiceURI === getVoiceId());
					const speech = new SpeechSynthesisUtterance(content);
					speech.rate = $settings.audio?.tts?.playbackRate ?? 1;

					speech.onend = () => {
						speaking = false;
						if ($settings.conversationMode) {
							document.getElementById('voice-input-button')?.click();
						}
					};

					if (voice) {
						speech.voice = voice;
					}

					speechSynthesis.speak(speech);
				}
			}, 100);
		} else {
			$audioQueue.setId(`${message.id}`);
			$audioQueue.setPlaybackRate($settings.audio?.tts?.playbackRate ?? 1);
			let synthesizing = true;
			$audioQueue.onStopped = ({ event }) => {
				if (event === 'empty-queue' && synthesizing) return;

				speaking = false;
				speakingIdx = undefined;

				if (event === 'error') {
					speakAbort?.abort();
					toast.error($i18n.t('Audio playback failed'));
				}
			};

			loadingSpeech = true;
			const messageContentParts: string[] = getMessageContentParts(
				content,
				$config?.audio?.tts?.split_on ?? 'punctuation'
			);

			if (!messageContentParts.length) {
				toast.info($i18n.t('No content to speak'));
				speaking = false;
				loadingSpeech = false;
				return;
			}

			const voiceId = getVoiceId();
			console.debug('Prepared message content for TTS', messageContentParts, 'voice:', voiceId);

			if ($settings.audio?.tts?.engine === 'browser-kokoro') {
				if (!$TTSWorker) {
					await TTSWorker.set(
						new KokoroWorker({
							dtype: $settings.audio?.tts?.engineConfig?.dtype ?? 'fp32'
						})
					);

					await $TTSWorker.init();
				}

				for (const [, sentence] of messageContentParts.entries()) {
					if (signal.aborted) return;

					const url = await $TTSWorker
						.generate({ text: sentence, voice: voiceId })
						.catch((error) => {
							console.error(error);
							toast.error(`${error}`);
							speaking = false;
							loadingSpeech = false;
						});

					if (signal.aborted) return;

					if (url && speaking) {
						$audioQueue.enqueue(url);
						loadingSpeech = false;
					}
				}
			} else {
				for (const [, sentence] of messageContentParts.entries()) {
					if (signal.aborted) return;

					const res = await synthesizeOpenAISpeech(localStorage.token, voiceId, sentence).catch(
						(error) => {
							console.error(error);
							toast.error(`${error}`);
							speaking = false;
							loadingSpeech = false;
						}
					);

					if (signal.aborted) return;

					if (res && speaking) {
						const blob = await res.blob();
						const url = URL.createObjectURL(blob);
						$audioQueue.enqueue(url);
						loadingSpeech = false;
					}
				}
			}

			synthesizing = false;
		}
	};

	let preprocessedDetailsCache = [];

	function preprocessForEditing(content: string): string {
		// Replace <details>...</details> with unique ID placeholder
		const detailsBlocks = [];
		let i = 0;

		content = content.replace(/<details[\s\S]*?<\/details>/gi, (match) => {
			detailsBlocks.push(match);
			return `<details id="__DETAIL_${i++}__"/>`;
		});

		// Store original blocks in the editedContent or globally (see merging later)
		preprocessedDetailsCache = detailsBlocks;

		return content;
	}

	function postprocessAfterEditing(content: string): string {
		const restoredContent = content.replace(
			/<details id="__DETAIL_(\d+)__"\/>/g,
			(_, index) => preprocessedDetailsCache[parseInt(index)] || ''
		);

		return restoredContent;
	}

	const editMessageHandler = async () => {
		edit = true;

		if (message.output?.length) {
			// Structured edit: use the block editor
			editedOutput = structuredClone(message.output);
		} else {
			// Legacy text edit: use the textarea
			editedContent = preprocessForEditing(message.content);
		}

		await tick();

		if (!editedOutput && editTextAreaElement) {
			const messagesContainer = document.getElementById('messages-container');
			const savedScrollTop = messagesContainer?.scrollTop ?? 0;

			editTextAreaElement.style.height = '';
			editTextAreaElement.style.height = `${editTextAreaElement.scrollHeight}px`;

			if (messagesContainer) messagesContainer.scrollTop = savedScrollTop;
			editTextAreaElement?.focus({ preventScroll: true });
		}
	};

	const editMessageConfirmHandler = async () => {
		if (editedOutput) {
			editMessage(message.id, { output: editedOutput }, false);
		} else {
			// Legacy text edit
			const messageContent = postprocessAfterEditing(editedContent ?? '');
			editMessage(message.id, { content: messageContent }, false);
		}

		edit = false;
		editedContent = '';
		editedOutput = null;

		await tick();
	};

	const saveAsCopyHandler = async () => {
		if (editedOutput) {
			editMessage(message.id, { output: editedOutput });
		} else {
			const messageContent = postprocessAfterEditing(editedContent ?? '');
			editMessage(message.id, { content: messageContent });
		}

		edit = false;
		editedContent = '';
		editedOutput = null;

		await tick();
	};

	const cancelEditMessage = async () => {
		edit = false;
		editedContent = '';
		editedOutput = null;
		await tick();
	};

	let feedbackLoading = false;

	const feedbackHandler = async (rating: number | null = null, details: object | null = null) => {
		feedbackLoading = true;
		console.log('Feedback', rating, details);

		const updatedMessage = {
			...message,
			annotation: {
				...(message?.annotation ?? {}),
				...(rating !== null ? { rating: rating } : {}),
				...(rating !== null && rating !== message?.annotation?.rating
					? { reason: null, details: null }
					: {}),
				...(details ? details : {})
			}
		};

		const chat = await getChatById(localStorage.token, chatId).catch((error) => {
			toast.error(`${error}`);
		});
		if (!chat) {
			return;
		}

		const messages = createMessagesList(history, message.id);

		let feedbackItem = {
			type: 'rating',
			data: {
				...(updatedMessage?.annotation ? updatedMessage.annotation : {}),
				model_id: message?.selectedModelId ?? message.model,
				...(history.messages[message.parentId].childrenIds.length > 1
					? {
							sibling_model_ids: history.messages[message.parentId].childrenIds
								.filter((id) => id !== message.id)
								.map((id) => history.messages[id]?.selectedModelId ?? history.messages[id].model)
						}
					: {})
			},
			meta: {
				arena: message ? message.arena : false,
				model_id: message.model,
				message_id: message.id,
				message_index: messages.length,
				chat_id: chatId
			},
			snapshot: {
				chat: chat
			}
		};

		const baseModels = [
			feedbackItem.data.model_id,
			...(feedbackItem.data.sibling_model_ids ?? [])
		].reduce((acc, modelId) => {
			const model = $models.find((m) => m.id === modelId);
			if (model) {
				acc[model.id] = model?.info?.base_model_id ?? null;
			} else {
				// Log or handle cases where corresponding model is not found
				console.warn(`Model with ID ${modelId} not found`);
			}
			return acc;
		}, {});
		feedbackItem.meta.base_models = baseModels;

		let feedback = null;
		if (message?.feedbackId) {
			feedback = await updateFeedbackById(
				localStorage.token,
				message.feedbackId,
				feedbackItem
			).catch((error) => {
				console.error(error);
				return null;
			});
		}

		if (!feedback) {
			feedback = await createNewFeedback(localStorage.token, feedbackItem).catch((error) => {
				toast.error(`${error}`);
			});

			if (feedback) {
				updatedMessage.feedbackId = feedback.id;
			}
		}

		console.log(updatedMessage);
		saveMessage(message.id, updatedMessage);

		await tick();

		if (!details) {
			showRateComment = true;

			if (!updatedMessage.annotation?.tags && (message?.content ?? '') !== '') {
				// attempt to generate tags
				const tags = await generateTags(localStorage.token, message.model, messages, chatId).catch(
					(error) => {
						console.error(error);
						return [];
					}
				);
				console.log(tags);

				if (tags) {
					const taggedMessage = {
						...message,
						annotation: { ...(message?.annotation ?? {}), tags: tags }
					};
					feedbackItem.data = { ...feedbackItem.data, ...taggedMessage.annotation };

					saveMessage(message.id, taggedMessage);
					await updateFeedbackById(
						localStorage.token,
						taggedMessage.feedbackId,
						feedbackItem
					).catch((error) => {
						toast.error(`${error}`);
					});
				}
			}
		}

		feedbackLoading = false;
	};

	const deleteMessageHandler = async () => {
		deleteMessage(message.id);
	};

	$: if (!edit) {
		(async () => {
			await tick();
		})();
	}

	const buttonsWheelHandler = (event: WheelEvent) => {
		if (buttonsContainerElement) {
			if (buttonsContainerElement.scrollWidth <= buttonsContainerElement.clientWidth) {
				// If the container is not scrollable, horizontal scroll
				return;
			} else {
				event.preventDefault();

				if (event.deltaY !== 0) {
					// Adjust horizontal scroll position based on vertical scroll
					buttonsContainerElement.scrollLeft += event.deltaY;
				}
			}
		}
	};

	const contentCopyHandler = (e) => {
		if (contentContainerElement) {
			e.preventDefault();
			// Get the selected HTML
			const selection = window.getSelection();
			const range = selection.getRangeAt(0);
			const tempDiv = document.createElement('div');

			// Remove background, color, and font styles
			tempDiv.appendChild(range.cloneContents());

			tempDiv.querySelectorAll('table').forEach((table) => {
				table.style.borderCollapse = 'collapse';
				table.style.width = 'auto';
				table.style.tableLayout = 'auto';
			});

			tempDiv.querySelectorAll('th').forEach((th) => {
				th.style.whiteSpace = 'nowrap';
				th.style.padding = '4px 8px';
			});

			// Put cleaned HTML + plain text into clipboard
			e.clipboardData.setData('text/html', tempDiv.innerHTML);
			e.clipboardData.setData('text/plain', selection.toString());
		}
	};

	onMount(async () => {
		// console.log('ResponseMessage mounted');

		await tick();
		if (buttonsContainerElement) {
			buttonsContainerElement.addEventListener('wheel', buttonsWheelHandler);
		}

		if (contentContainerElement) {
			contentContainerElement.addEventListener('copy', contentCopyHandler);
		}
	});

	onDestroy(() => {
		if (buttonsContainerElement) {
			buttonsContainerElement.removeEventListener('wheel', buttonsWheelHandler);
		}

		if (contentContainerElement) {
			contentContainerElement.removeEventListener('copy', contentCopyHandler);
		}
	});
</script>

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete message?')}
	on:confirm={() => {
		deleteMessageHandler();
	}}
/>

{#key message.id}
	<div
		class=" flex w-full message-{message.id}"
		id="message-{message.id}"
		dir={$settings.chatDirection}
		style="scroll-margin-top: 3rem;"
	>
		<div class={`shrink-0 ltr:mr-2 rtl:ml-2 hidden @lg:flex mt-0.5 `}>
			<ProfileImage
				src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${model?.id ?? message.model}&lang=${$i18n.language}`}
				className={'size-7 assistant-message-profile-image'}
			/>
		</div>

		<div class="flex-auto w-0 pl-1 relative">
			{#if !compactPreview}
				<Name>
					<Tooltip content={localizedModelName} placement="top-start">
						<span id="response-message-model-name" class="line-clamp-1 text-black dark:text-white">
							{localizedModelName}
						</span>
					</Tooltip>
				</Name>
			{/if}

			<div>
				<div class="chat-{message.role} w-full min-w-full">
					<div>
						{#if model?.info?.meta?.capabilities?.status_updates ?? true}
							<StatusHistory statusHistory={message?.statusHistory} />
						{/if}

						{#if message?.files && message.files?.filter( (f) => ['image', 'file'].includes(f.type) ).length > 0}
							<div
								class="my-1 w-full flex overflow-x-auto gap-2 flex-wrap"
								dir={$settings?.chatDirection ?? 'auto'}
							>
								{#each message.files.filter((f) => ['image', 'file'].includes(f.type)) as file}
									<div>
										{#if file.type === 'image' || (file?.content_type ?? '').startsWith('image/')}
											<Image src={file.url} alt={file.name || $i18n.t('Generated Image')} />
										{:else}
											<FileItem
												item={file}
												url={file.url}
												name={file.name}
												type={file.type}
												size={file?.size}
												small={true}
											/>
										{/if}
									</div>
								{/each}
							</div>
						{/if}

						{#if !readOnly && message?.embeds && message.embeds.length > 0}
							<div
								class="my-1 w-full flex overflow-x-auto gap-2 flex-wrap"
								id={`${message.id}-embeds-container`}
							>
								{#each message.embeds as embed, idx}
									<div class="my-2 w-full" id={`${message.id}-embeds-${idx}`}>
										<FullHeightIframe
											src={embed}
											allowScripts={true}
											allowForms={$settings?.iframeSandboxAllowForms ?? true}
											allowSameOrigin={$settings?.iframeSandboxAllowSameOrigin ?? false}
											allowPopups={true}
										/>
									</div>
								{/each}
							</div>
						{/if}

						{#if edit === true}
							<div
								class="w-full bg-gray-50 dark:bg-gray-800 rounded-3xl px-3 py-3 my-2 {($settings?.highContrastMode ??
								false)
									? 'focus-within:outline focus-within:outline-2 focus-within:-outline-offset-2 focus-within:outline-blue-500'
									: ''}"
							>
								{#if editedOutput}
									<!-- Structured output editor (visual + JSON toggle) -->
									<OutputEditView
										output={editedOutput}
										onChange={(updated) => {
											editedOutput = updated;
										}}
									/>
								{:else}
									<!-- Legacy textarea for messages without output -->
									<textarea
										id="message-edit-{message.id}"
										bind:this={editTextAreaElement}
										class=" bg-transparent outline-hidden focus-visible:outline-none! w-full resize-none text-[0.9375rem]"
										bind:value={editedContent}
										on:input={(e) => {
											const messagesContainer = document.getElementById('messages-container');
											const savedScrollTop = messagesContainer?.scrollTop ?? 0;
											const textarea = e.currentTarget;

											textarea.style.height = '';
											textarea.style.height = `${textarea.scrollHeight}px`;

											if (messagesContainer) messagesContainer.scrollTop = savedScrollTop;
										}}
										on:keydown={(e) => {
											if (e.key === 'Escape') {
												document.getElementById('close-edit-message-button')?.click();
											}

											const isCmdOrCtrlPressed = e.metaKey || e.ctrlKey;
											const isEnterPressed = e.key === 'Enter';

											if (isCmdOrCtrlPressed && isEnterPressed) {
												document.getElementById('confirm-edit-message-button')?.click();
											}
										}}
									></textarea>
								{/if}

								<div class=" mt-2 flex justify-between text-sm font-normal">
									<div>
										<button
											id="save-new-message-button"
											class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-gray-100 px-2.5 text-xs font-normal text-gray-800 transition hover:bg-gray-100/70 disabled:opacity-60 dark:bg-gray-850 dark:text-white dark:hover:bg-gray-850/60"
											on:click={() => {
												saveAsCopyHandler();
											}}
										>
											{$i18n.t('Save As Copy')}
										</button>
									</div>

									<div class="flex space-x-1.5">
										<button
											id="close-edit-message-button"
											class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg px-2.5 text-xs font-normal text-gray-600 transition hover:bg-gray-100 hover:text-gray-900 disabled:opacity-60 dark:text-gray-400 dark:hover:bg-gray-850 dark:hover:text-white"
											on:click={() => {
												cancelEditMessage();
											}}
										>
											{$i18n.t('Cancel')}
										</button>

										{#if !message.user_id || message.user_id === $user?.id}
											<button
												id="confirm-edit-message-button"
												class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs font-normal text-white transition hover:bg-black disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
												on:click={() => {
													editMessageConfirmHandler();
												}}
											>
												{$i18n.t('Save')}
											</button>
										{/if}
									</div>
								</div>
							</div>
						{/if}

						<div
							bind:this={contentContainerElement}
							class="w-full flex flex-col relative {edit ? 'hidden' : ''}"
							id="response-content-container"
						>
							{#if hasResponseContent && message.error !== true}
								<!-- always show message contents even if there's an error -->
								<!-- unless message.error === true which is legacy error handling, where the error message is stored in message.content -->
								<ContentRenderer
									id={`${chatId}-${message.id}`}
									{chatId}
									messageId={message.id}
									content={message.content}
									output={message.output}
									sources={message.sources}
									floatingButtons={message?.done &&
										!readOnly &&
										($settings?.showFloatingActionButtons ?? true)}
									save={(!readOnly && (!message.user_id || message.user_id === $user?.id)) ||
										(shareMode === 'continue' && message.user_id === $user?.id)}
									preview={!readOnly}
									{compactPreview}
									editCodeBlock={!readOnly && editCodeBlock}
									{topPadding}
									done={message?.done ?? false}
									allowEmbeds={!readOnly}
									{model}
									onTaskClick={async (e) => {
										console.log(e);
									}}
									{onToolCallResolved}
									onSourceClick={async (id) => {
										console.log(id);

										if (citationsElement) {
											citationsElement?.showSourceModal(id);
										}
									}}
									onSetInputText={(text) => {
										setInputText(text);
									}}
									onSave={({ raw, oldContent, newContent }) => {
										const sourceMessage = history.messages[message.id];
										if (sourceMessage.output?.length) {
											const updatedOutput = replaceOutputMessageText(
												sourceMessage.output,
												oldContent,
												newContent
											);
											if (updatedOutput !== sourceMessage.output) {
												sourceMessage.output = updatedOutput;
											} else {
												sourceMessage.content = sourceMessage.content.replace(raw, () =>
													raw.replace(oldContent, () => newContent)
												);
											}
										} else {
											sourceMessage.content = sourceMessage.content.replace(raw, () =>
												raw.replace(oldContent, () => newContent)
											);
										}

										updateChat();
									}}
								/>
							{/if}

							{#if !message.done && !message.error && (hasResponseContent || !hasVisibleStatus)}
								<div class="text-[0.9375rem] leading-relaxed">
									<span
										class="inline-block w-[0.125rem] h-3.5 bg-gray-400 dark:bg-gray-500 ml-0.5 animate-cursor-pulse align-text-bottom"
									></span>
								</div>
							{/if}

							{#if message?.error}
								<Error content={message?.error?.content ?? message.content} />
							{/if}

							{#if (message?.sources || message?.citations) && (model?.info?.meta?.capabilities?.citations ?? true)}
								<Citations
									bind:this={citationsElement}
									id={message?.id}
									{chatId}
									sources={message?.sources ?? message?.citations}
									{readOnly}
								/>
							{/if}

							{#if message.code_executions}
								<CodeExecutions codeExecutions={message.code_executions} />
							{/if}
						</div>
					</div>
				</div>

				{#if compactPreview && message.timestamp}
					<div class="mt-0.5 flex justify-start whitespace-nowrap text-gray-600 dark:text-gray-500">
						<Tooltip
							className="flex self-center"
							content={formatMessageTimestampFull(message.timestamp * 1000, $i18n.language)}
							placement="bottom"
						>
							<time
								datetime={new Date(message.timestamp * 1000).toISOString()}
								class="ml-1 shrink-0 whitespace-nowrap text-[0.6875rem] tabular-nums text-gray-400 dark:text-gray-600 select-none"
							>
								{formatMessageTimestamp(message.timestamp * 1000, $i18n.language)}
							</time>
						</Tooltip>
					</div>
				{:else if !edit}
					<div
						bind:this={buttonsContainerElement}
						class="flex items-center justify-start overflow-x-auto whitespace-nowrap buttons {($settings?.highContrastMode ??
						false)
							? 'text-gray-600 dark:text-gray-500'
							: 'text-gray-600/80 dark:text-gray-500/70'} mt-0.5 [&>*]:shrink-0"
					>
						{#if message.done || siblings.length > 1}
							{#if message.done && onInsertToNote && visibleResponseContent}
								<Tooltip content={$i18n.t('Insert into note')} placement="bottom">
									<button
										aria-label={$i18n.t('Insert into note')}
										class="{isLastMessage || ($settings?.highContrastMode ?? false)
											? 'visible'
											: 'hover-reveal'} inline-flex size-7 shrink-0 items-center justify-center p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-gray-400 hover:text-gray-600 transition"
										on:click={() => {
											onInsertToNote?.(visibleResponseContent);
										}}
									>
										<svg
											class="size-4"
											aria-hidden="true"
											viewBox="0 0 24 24"
											stroke-width="1.5"
											fill="none"
											xmlns="http://www.w3.org/2000/svg"
										>
											<path
												d="M19 19L6 6M6 6L6 18.48M6 6L18.48 6"
												stroke="currentColor"
												stroke-linecap="round"
												stroke-linejoin="round"
											/>
										</svg>
									</button>
								</Tooltip>
							{/if}

							{#if siblings.length > 1}
								<div class="flex self-center min-w-fit" dir="ltr">
									<button
										aria-label={$i18n.t('Previous message')}
										class="self-center inline-flex size-7 shrink-0 items-center justify-center p-1.5 hover:bg-black/5 dark:hover:bg-white/5 dark:hover:text-gray-400 hover:text-gray-600 rounded-md transition"
										on:click={() => {
											showPreviousMessage(message);
										}}
									>
										<ChevronRightIcon className="size-4 rotate-180" />
									</button>

									{#if messageIndexEdit}
										<div
											class="text-sm flex justify-center font-normal self-center dark:text-gray-500 min-w-fit"
										>
											<input
												id="message-index-input-{message.id}"
												type="number"
												value={siblings.indexOf(message.id) + 1}
												min="1"
												max={siblings.length}
												on:focus={(e) => {
													e.target.select();
												}}
												on:blur={(e) => {
													gotoMessage(message, e.target.value - 1);
													messageIndexEdit = false;
												}}
												on:keydown={(e) => {
													if (e.key === 'Enter') {
														gotoMessage(message, e.target.value - 1);
														messageIndexEdit = false;
													}
												}}
												class="bg-transparent font-normal self-center dark:text-gray-500 min-w-fit outline-hidden"
											/>/{siblings.length}
										</div>
									{:else}
										<!-- svelte-ignore a11y-no-static-element-interactions -->
										<div
											class="text-sm tracking-widest font-normal self-center dark:text-gray-500 min-w-fit"
											on:dblclick={async () => {
												messageIndexEdit = true;

												await tick();
												const input = document.getElementById(`message-index-input-${message.id}`);
												if (input) {
													input.focus();
													input.select();
												}
											}}
										>
											{siblings.indexOf(message.id) + 1}/{siblings.length}
										</div>
									{/if}

									<button
										class="self-center inline-flex size-7 shrink-0 items-center justify-center p-1.5 hover:bg-black/5 dark:hover:bg-white/5 dark:hover:text-gray-400 hover:text-gray-600 rounded-md transition"
										on:click={() => {
											showNextMessage(message);
										}}
										aria-label={$i18n.t('Next message')}
									>
										<ChevronRightIcon className="size-4" />
									</button>
								</div>
							{/if}

							{#if message.done}
								{#if !readOnly}
									{#if $user?.role === 'user' ? ($user?.permissions?.chat?.edit ?? true) : true}
										<Tooltip content={$i18n.t('Edit')} placement="bottom">
											<button
												aria-label={$i18n.t('Edit')}
												class="{isLastMessage || ($settings?.highContrastMode ?? false)
													? 'visible'
													: 'hover-reveal'} inline-flex size-7 shrink-0 items-center justify-center p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-gray-400 hover:text-gray-600 transition"
												on:click={() => {
													editMessageHandler();
												}}
											>
												<EditPencilIcon />
											</button>
										</Tooltip>
									{/if}
								{/if}

								<Tooltip content={$i18n.t('Copy')} placement="bottom">
									<button
										aria-label={$i18n.t('Copy')}
										class="{isLastMessage || ($settings?.highContrastMode ?? false)
											? 'visible'
											: 'hover-reveal'} inline-flex size-7 shrink-0 items-center justify-center p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-gray-400 hover:text-gray-600 transition copy-response-button"
										on:click={() => {
											copyToClipboard(visibleResponseContent);
										}}
									>
										<CopyIcon />
									</button>
								</Tooltip>

								{#if !readOnly && ($user?.role === 'admin' || ($user?.permissions?.chat?.tts ?? true))}
									<Tooltip content={$i18n.t('Read Aloud')} placement="bottom">
										<button
											aria-label={$i18n.t('Read Aloud')}
											id="speak-button-{message.id}"
											class="{isLastMessage || ($settings?.highContrastMode ?? false)
												? 'visible'
												: 'hover-reveal'} inline-flex size-7 shrink-0 items-center justify-center p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-gray-400 hover:text-gray-600 transition"
											on:click={() => {
												if (!loadingSpeech) {
													if (speaking) {
														stopAudio();
													} else {
														speak();
													}
												}
											}}
										>
											{#if loadingSpeech}
												<svg
													class="size-4 animate-spin"
													aria-hidden="true"
													stroke-width="1.5"
													viewBox="0 0 24 24"
													fill="none"
													xmlns="http://www.w3.org/2000/svg"
												>
													<path
														d="M21.8883 13.5C21.1645 18.3113 17.013 22 12 22C6.47715 22 2 17.5228 2 12C2 6.47715 6.47715 2 12 2C16.1006 2 19.6248 4.46819 21.1679 8"
														stroke="currentColor"
														stroke-linecap="round"
														stroke-linejoin="round"
													/>
													<path
														d="M17 8H21.4C21.7314 8 22 7.73137 22 7.4V3"
														stroke="currentColor"
														stroke-linecap="round"
														stroke-linejoin="round"
													/>
												</svg>
											{:else if speaking}
												<svg
													class="size-4"
													aria-hidden="true"
													viewBox="0 0 24 24"
													stroke-width="1.5"
													fill="none"
													xmlns="http://www.w3.org/2000/svg"
												>
													<path
														d="M18 14L20.0005 12M22 10L20.0005 12M20.0005 12L18 10M20.0005 12L22 14"
														stroke="currentColor"
														stroke-linecap="round"
														stroke-linejoin="round"
													/>
													<path
														d="M2 13.8571V10.1429C2 9.03829 2.89543 8.14286 4 8.14286H6.9C7.09569 8.14286 7.28708 8.08544 7.45046 7.97772L13.4495 4.02228C14.1144 3.5839 15 4.06075 15 4.85714V19.1429C15 19.9392 14.1144 20.4161 13.4495 19.9777L7.45046 16.0223C7.28708 15.9146 7.09569 15.8571 6.9 15.8571H4C2.89543 15.8571 2 14.9617 2 13.8571Z"
														stroke="currentColor"
													/>
												</svg>
											{:else}
												<svg
													class="size-4"
													aria-hidden="true"
													viewBox="0 0 24 24"
													stroke-width="1.5"
													fill="none"
													xmlns="http://www.w3.org/2000/svg"
												>
													<path
														d="M1 13.8571V10.1429C1 9.03829 1.89543 8.14286 3 8.14286H5.9C6.09569 8.14286 6.28708 8.08544 6.45046 7.97772L12.4495 4.02228C13.1144 3.5839 14 4.06075 14 4.85714V19.1429C14 19.9392 13.1144 20.4161 12.4495 19.9777L6.45046 16.0223C6.28708 15.9146 6.09569 15.8571 5.9 15.8571H3C1.89543 15.8571 1 14.9617 1 13.8571Z"
														stroke="currentColor"
													/>
													<path
														d="M17.5 7.5C17.5 7.5 19 9 19 11.5C19 14 17.5 15.5 17.5 15.5"
														stroke="currentColor"
														stroke-linecap="round"
														stroke-linejoin="round"
													/>
													<path
														d="M20.5 4.5C20.5 4.5 23 7 23 11.5C23 16 20.5 18.5 20.5 18.5"
														stroke="currentColor"
														stroke-linecap="round"
														stroke-linejoin="round"
													/>
												</svg>
											{/if}
										</button>
									</Tooltip>
								{/if}

								{#if message.usage}
									<Tooltip
										content={message.usage
											? `<pre>${sanitizeResponseContent(
													JSON.stringify(message.usage, null, 2)
														.replace(/"([^(")"]+)":/g, '$1:')
														.slice(1, -1)
														.split('\n')
														.map((line) => line.slice(2))
														.map((line) => (line.endsWith(',') ? line.slice(0, -1) : line))
														.join('\n')
												)}</pre>`
											: ''}
										placement="bottom"
									>
										<button
											aria-hidden="true"
											class=" {isLastMessage || ($settings?.highContrastMode ?? false)
												? 'visible'
												: 'hover-reveal'} inline-flex size-7 shrink-0 items-center justify-center p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-gray-400 hover:text-gray-600 transition whitespace-pre-wrap"
											on:click={() => {
												console.log(message);
											}}
											id="info-{message.id}"
										>
											<svg
												class="size-4"
												aria-hidden="true"
												stroke-width="1.5"
												viewBox="0 0 24 24"
												fill="none"
												xmlns="http://www.w3.org/2000/svg"
											>
												<path
													d="M12 11.5V16.5"
													stroke="currentColor"
													stroke-linecap="round"
													stroke-linejoin="round"
												/>
												<path
													d="M12 7.51L12.01 7.49889"
													stroke="currentColor"
													stroke-linecap="round"
													stroke-linejoin="round"
												/>
												<path
													d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z"
													stroke="currentColor"
													stroke-linecap="round"
													stroke-linejoin="round"
												/>
											</svg>
										</button>
									</Tooltip>
								{/if}

								{#if $user && message.done && forkHandler && ($user?.role === 'admin' || ($user?.permissions?.chat?.import ?? true))}
									<Tooltip content={$i18n.t('Fork chat')} placement="bottom">
										<button
											aria-label={$i18n.t('Fork chat')}
											class="{isLastMessage || ($settings?.highContrastMode ?? false)
												? 'visible'
												: 'hover-reveal'} inline-flex size-7 shrink-0 items-center justify-center p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-gray-400 hover:text-gray-600 transition"
											on:click={() => {
												forkHandler?.(message.id);
											}}
										>
											<svg
												class="size-4 -scale-x-100 -scale-y-100 -rotate-90"
												aria-hidden="true"
												viewBox="0 0 24 24"
												stroke-width="1.5"
												fill="none"
												xmlns="http://www.w3.org/2000/svg"
											>
												<path
													d="M17 7C18.1046 7 19 6.10457 19 5C19 3.89543 18.1046 3 17 3C15.8954 3 15 3.89543 15 5C15 6.10457 15.8954 7 17 7Z"
													stroke="currentColor"
													stroke-linecap="round"
													stroke-linejoin="round"
												/>
												<path
													d="M7 7C8.10457 7 9 6.10457 9 5C9 3.89543 8.10457 3 7 3C5.89543 3 5 3.89543 5 5C5 6.10457 5.89543 7 7 7Z"
													stroke="currentColor"
													stroke-linecap="round"
													stroke-linejoin="round"
												/>
												<path
													d="M7 21C8.10457 21 9 20.1046 9 19C9 17.8954 8.10457 17 7 17C5.89543 17 5 17.8954 5 19C5 20.1046 5.89543 21 7 21Z"
													stroke="currentColor"
													stroke-linecap="round"
													stroke-linejoin="round"
												/>
												<path
													d="M7 7V17"
													stroke="currentColor"
													stroke-linecap="round"
													stroke-linejoin="round"
												/>
												<path
													d="M17 7V8C17 10.5 15 11 15 11L9 13C9 13 7 13.5 7 16V17"
													stroke="currentColor"
													stroke-linecap="round"
													stroke-linejoin="round"
												/>
											</svg>
										</button>
									</Tooltip>
								{/if}

								{#if (!readOnly && (!message.user_id || message.user_id === $user?.id)) || (shareMode === 'continue' && message.user_id === $user?.id)}
									{#if !readOnly && !$temporaryChatEnabled && ($config?.features.enable_message_rating ?? true) && ($user?.role === 'admin' || ($user?.permissions?.chat?.rate_response ?? true))}
										<Tooltip content={$i18n.t('Good Response')} placement="bottom">
											<button
												aria-label={$i18n.t('Good Response')}
												class="{isLastMessage || ($settings?.highContrastMode ?? false)
													? 'visible'
													: 'hover-reveal'} inline-flex size-7 shrink-0 items-center justify-center p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg {(
													message?.annotation?.rating ?? ''
												).toString() === '1'
													? 'bg-gray-100 dark:bg-gray-800'
													: ''} dark:hover:text-gray-400 hover:text-gray-600 transition disabled:cursor-progress disabled:hover:bg-transparent"
												disabled={feedbackLoading}
												on:click={async (e) => {
													e.stopPropagation();
													await feedbackHandler(1);
													window.setTimeout(() => {
														document
															.getElementById(`message-feedback-${message.id}`)
															?.scrollIntoView();
													}, 0);
												}}
											>
												<svg
													class="size-4"
													aria-hidden="true"
													stroke-width="1.5"
													viewBox="0 0 24 24"
													fill="none"
													xmlns="http://www.w3.org/2000/svg"
												>
													<path
														d="M16.4724 20H4.1C3.76863 20 3.5 19.7314 3.5 19.4V9.6C3.5 9.26863 3.76863 9 4.1 9H6.86762C7.57015 9 8.22116 8.6314 8.5826 8.02899L11.293 3.51161C11.8779 2.53688 13.2554 2.44422 13.9655 3.33186C14.3002 3.75025 14.4081 4.30635 14.2541 4.81956L13.2317 8.22759C13.1162 8.61256 13.4045 9 13.8064 9H18.3815C19.7002 9 20.658 10.254 20.311 11.5262L18.4019 18.5262C18.1646 19.3964 17.3743 20 16.4724 20Z"
														stroke="currentColor"
														stroke-linecap="round"
													/>
													<path
														d="M7 20L7 9"
														stroke="currentColor"
														stroke-linecap="round"
														stroke-linejoin="round"
													/>
												</svg>
											</button>
										</Tooltip>

										<Tooltip content={$i18n.t('Bad Response')} placement="bottom">
											<button
												aria-label={$i18n.t('Bad Response')}
												class="{isLastMessage || ($settings?.highContrastMode ?? false)
													? 'visible'
													: 'hover-reveal'} inline-flex size-7 shrink-0 items-center justify-center p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg {(
													message?.annotation?.rating ?? ''
												).toString() === '-1'
													? 'bg-gray-100 dark:bg-gray-800'
													: ''} dark:hover:text-gray-400 hover:text-gray-600 transition disabled:cursor-progress disabled:hover:bg-transparent"
												disabled={feedbackLoading}
												on:click={async (e) => {
													e.stopPropagation();
													await feedbackHandler(-1);
													window.setTimeout(() => {
														document
															.getElementById(`message-feedback-${message.id}`)
															?.scrollIntoView();
													}, 0);
												}}
											>
												<svg
													class="size-4"
													aria-hidden="true"
													stroke-width="1.5"
													viewBox="0 0 24 24"
													fill="none"
													xmlns="http://www.w3.org/2000/svg"
												>
													<path
														d="M16.4724 3.5H4.1C3.76863 3.5 3.5 3.76863 3.5 4.1V13.9C3.5 14.2314 3.76863 14.5 4.1 14.5H6.86762C7.57015 14.5 8.22116 14.8686 8.5826 15.471L11.293 19.9884C11.8779 20.9631 13.2554 21.0558 13.9655 20.1681C14.3002 19.7497 14.4081 19.1937 14.2541 18.6804L13.2317 15.2724C13.1162 14.8874 13.4045 14.5 13.8064 14.5H18.3815C19.7002 14.5 20.658 13.246 20.311 11.9738L18.4019 4.97376C18.1646 4.10364 17.3743 3.5 16.4724 3.5Z"
														stroke="currentColor"
														stroke-linecap="round"
													/>
													<path
														d="M7 14.5L7 3.5"
														stroke="currentColor"
														stroke-linecap="round"
														stroke-linejoin="round"
													/>
												</svg>
											</button>
										</Tooltip>
									{/if}

									{#if isLastMessage && ($user?.role === 'admin' || ($user?.permissions?.chat?.continue_response ?? true))}
										<Tooltip content={$i18n.t('Continue Response')} placement="bottom">
											<button
												aria-label={$i18n.t('Continue Response')}
												type="button"
												id="continue-response-button"
												class="{isLastMessage || ($settings?.highContrastMode ?? false)
													? 'visible'
													: 'hover-reveal'} inline-flex size-7 shrink-0 items-center justify-center p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-gray-400 hover:text-gray-600 transition"
												on:click={() => {
													continueResponse(message);
												}}
											>
												<svg
													class="size-4"
													aria-hidden="true"
													stroke-width="1.5"
													viewBox="0 0 24 24"
													fill="none"
													xmlns="http://www.w3.org/2000/svg"
												>
													<path
														d="M6.90588 4.53682C6.50592 4.2998 6 4.58808 6 5.05299V18.947C6 19.4119 6.50592 19.7002 6.90588 19.4632L18.629 12.5162C19.0211 12.2838 19.0211 11.7162 18.629 11.4838L6.90588 4.53682Z"
														stroke="currentColor"
														stroke-linecap="round"
														stroke-linejoin="round"
													/>
												</svg>
											</button>
										</Tooltip>
									{/if}
								{/if}

								{#if (!readOnly && (!message.user_id || message.user_id === $user?.id)) || shareMode === 'continue'}
									{#if $user?.role === 'admin' || ($user?.permissions?.chat?.regenerate_response ?? true)}
										{#if $settings?.regenerateMenu ?? true}
											<button
												type="button"
												class="hidden regenerate-response-button"
												on:click={() => {
													showRateComment = false;
													regenerateResponse(message);

													(model?.actions ?? []).forEach((action) => {
														dispatch('action', {
															id: action.id,
															event: {
																id: 'regenerate-response',
																data: {
																	messageId: message.id
																}
															}
														});
													});
												}}
											/>

											<RegenerateMenu
												onRegenerate={(prompt = null) => {
													showRateComment = false;
													regenerateResponse(message, prompt);

													(model?.actions ?? []).forEach((action) => {
														dispatch('action', {
															id: action.id,
															event: {
																id: 'regenerate-response',
																data: {
																	messageId: message.id
																}
															}
														});
													});
												}}
											>
												<Tooltip content={$i18n.t('Regenerate')} placement="bottom">
													<button
														type="button"
														aria-label={$i18n.t('Regenerate')}
														class="{isLastMessage || ($settings?.highContrastMode ?? false)
															? 'visible'
															: 'hover-reveal'} inline-flex size-7 shrink-0 items-center justify-center p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-gray-400 hover:text-gray-600 transition"
													>
														<svg
															class="size-4"
															aria-hidden="true"
															stroke-width="1.5"
															viewBox="-2 -2 28 28"
															fill="none"
															xmlns="http://www.w3.org/2000/svg"
														>
															<path
																d="M21.1679 8C19.6247 4.46819 16.1006 2 11.9999 2C6.81459 2 2.55104 5.94668 2.04932 11"
																stroke="currentColor"
																stroke-linecap="round"
																stroke-linejoin="round"
															/>
															<path
																d="M17 8H21.4C21.7314 8 22 7.73137 22 7.4V3"
																stroke="currentColor"
																stroke-linecap="round"
																stroke-linejoin="round"
															/>
															<path
																d="M2.88146 16C4.42458 19.5318 7.94874 22 12.0494 22C17.2347 22 21.4983 18.0533 22 13"
																stroke="currentColor"
																stroke-linecap="round"
																stroke-linejoin="round"
															/>
															<path
																d="M7.04932 16H2.64932C2.31795 16 2.04932 16.2686 2.04932 16.6V21"
																stroke="currentColor"
																stroke-linecap="round"
																stroke-linejoin="round"
															/>
														</svg>
													</button>
												</Tooltip>
											</RegenerateMenu>
										{:else}
											<Tooltip content={$i18n.t('Regenerate')} placement="bottom">
												<button
													type="button"
													aria-label={$i18n.t('Regenerate')}
													class="{isLastMessage || ($settings?.highContrastMode ?? false)
														? 'visible'
														: 'hover-reveal'} inline-flex size-7 shrink-0 items-center justify-center p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-gray-400 hover:text-gray-600 transition regenerate-response-button"
													on:click={() => {
														showRateComment = false;
														regenerateResponse(message);

														(model?.actions ?? []).forEach((action) => {
															dispatch('action', {
																id: action.id,
																event: {
																	id: 'regenerate-response',
																	data: {
																		messageId: message.id
																	}
																}
															});
														});
													}}
												>
													<svg
														class="size-4"
														aria-hidden="true"
														stroke-width="1.5"
														viewBox="-2 -2 28 28"
														fill="none"
														xmlns="http://www.w3.org/2000/svg"
													>
														<path
															d="M21.1679 8C19.6247 4.46819 16.1006 2 11.9999 2C6.81459 2 2.55104 5.94668 2.04932 11"
															stroke="currentColor"
															stroke-linecap="round"
															stroke-linejoin="round"
														/>
														<path
															d="M17 8H21.4C21.7314 8 22 7.73137 22 7.4V3"
															stroke="currentColor"
															stroke-linecap="round"
															stroke-linejoin="round"
														/>
														<path
															d="M2.88146 16C4.42458 19.5318 7.94874 22 12.0494 22C17.2347 22 21.4983 18.0533 22 13"
															stroke="currentColor"
															stroke-linecap="round"
															stroke-linejoin="round"
														/>
														<path
															d="M7.04932 16H2.64932C2.31795 16 2.04932 16.2686 2.04932 16.6V21"
															stroke="currentColor"
															stroke-linecap="round"
															stroke-linejoin="round"
														/>
													</svg>
												</button>
											</Tooltip>
										{/if}
									{/if}
								{/if}

								{#if (!readOnly && (!message.user_id || message.user_id === $user?.id)) || (shareMode === 'continue' && message.user_id === $user?.id)}
									{#each (!readOnly && model?.actions) || [] as action}
										<Tooltip
											content={resolveLocalizedFunction(
												action,
												$localizedFunctions,
												$i18n.language
											)}
											placement="bottom"
										>
											<button
												type="button"
												aria-label={resolveLocalizedFunction(
													action,
													$localizedFunctions,
													$i18n.language
												)}
												class="{isLastMessage || ($settings?.highContrastMode ?? false)
													? 'visible'
													: 'hover-reveal'} inline-flex size-7 shrink-0 items-center justify-center p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-gray-400 hover:text-gray-600 transition"
												on:click={() => {
													actionMessage(action.id, message);
												}}
											>
												{#if action?.icon}
													<div class="size-4">
														<img
															src={action.icon}
															class="w-4 h-4 {action.icon.includes('data:image/svg')
																? 'dark:invert-[80%]'
																: ''}"
															style="fill: currentColor;"
															alt={resolveLocalizedFunction(
																action,
																$localizedFunctions,
																$i18n.language
															)}
															draggable="false"
														/>
													</div>
												{:else}
													<Sparkles />
												{/if}
											</button>
										</Tooltip>
									{/each}

									{#if $user?.role === 'admin' || ($user?.permissions?.chat?.delete_message ?? true)}
										{#if (!readOnly || ($user?.role === 'admin' && $config?.features?.enable_admin_chat_access)) && siblings.length > 1}
											<Tooltip content={$i18n.t('Delete')} placement="bottom">
												<button
													type="button"
													aria-label={$i18n.t('Delete')}
													id="delete-response-button"
													class="{isLastMessage || ($settings?.highContrastMode ?? false)
														? 'visible'
														: 'hover-reveal'} inline-flex size-7 shrink-0 items-center justify-center p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-gray-400 hover:text-gray-600 transition disabled:opacity-50 disabled:hover:bg-transparent"
													disabled={!allowDelete}
													on:click={(e) => {
														if (!allowDelete) {
															return;
														}
														if (e.shiftKey) {
															deleteMessageHandler();
														} else {
															showDeleteConfirm = true;
														}
													}}
												>
													<TrashIcon />
												</button>
											</Tooltip>
										{/if}
									{/if}

									{#if message.timestamp}
										<Tooltip
											className="flex self-center"
											content={formatMessageTimestampFull(message.timestamp * 1000, $i18n.language)}
											placement="bottom"
										>
											<time
												datetime={new Date(message.timestamp * 1000).toISOString()}
												class="hover-reveal ml-1 shrink-0 whitespace-nowrap text-[0.6875rem] tabular-nums text-gray-400 dark:text-gray-600 select-none"
											>
												{formatMessageTimestamp(message.timestamp * 1000, $i18n.language)}
											</time>
										</Tooltip>
									{/if}
								{/if}
							{/if}
						{/if}
					</div>

					{#if message.done && showRateComment}
						{#key message?.annotation?.rating}
							<RateComment
								bind:message
								bind:show={showRateComment}
								on:save={async (e) => {
									await feedbackHandler(null, {
										...e.detail
									});
								}}
							/>
						{/key}
					{/if}

					{#if (isLastMessage || ($settings?.keepFollowUpPrompts ?? false)) && message.done && !readOnly && (message?.followUps ?? []).length > 0}
						<div class="my-2.5" in:fade={{ duration: 100 }}>
							<FollowUps
								followUps={message?.followUps}
								onClick={(prompt) => {
									if ($settings?.insertFollowUpPrompt ?? false) {
										// Insert the follow-up prompt into the input box
										setInputText(prompt);
									} else {
										// Submit the follow-up prompt directly
										submitMessage(message?.id, prompt);
									}
								}}
							/>
						</div>
					{/if}
				{/if}
			</div>
		</div>
	</div>
{/key}

<style>
	.buttons::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.buttons {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}
</style>
